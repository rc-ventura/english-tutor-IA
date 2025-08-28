# Watchdog Functionality Testing Guide

## Implementation Overview

The stream watchdog functionality was implemented in `SpeakingTab.tsx` to prevent hanging UI states when streaming is inactive. It works by:

1. **Arming a timer** when streaming starts (after recording)
2. **Resetting the timer** on each `onData` event (new message chunk)
3. **Clearing the timer** on normal completion (`onComplete`)
4. **Canceling the stream** if no activity is detected within `VITE_SPEAKING_STEP_TIMEOUT_SEC` (default: 25 seconds)

## Configuration

- Default timeout: 25 seconds
- Can be modified via `VITE_SPEAKING_STEP_TIMEOUT_SEC` environment variable
- Defined in `.env` or `.env.example`

## Watchdog Functionality

```typescript
// In SpeakingTab.tsx
const streamWatchdogTimerRef = useRef<number | null>(null);
const STEP_TIMEOUT_SEC: number = Number(
  ((import.meta as any).env?.VITE_SPEAKING_STEP_TIMEOUT_SEC as string) ?? 25
);

// Function to arm the watchdog timer
const armWatchdog = useCallback((job: CancelablePromise) => {
  // Clear any existing watchdog
  if (streamWatchdogTimerRef.current !== null) {
    clearTimeout(streamWatchdogTimerRef.current);
  }

  // Set new watchdog
  streamWatchdogTimerRef.current = setTimeout(() => {
    console.warn(`[UX] ⏱️ Watchdog fired after ${STEP_TIMEOUT_SEC}s of inactivity`);
    job.cancel();
    setIsLoading(false);
    streamWatchdogTimerRef.current = null;
  }, STEP_TIMEOUT_SEC * 1000) as unknown as number;

  console.debug(`[UX] 🕐 Watchdog armed: ${STEP_TIMEOUT_SEC}s`);
}, [STEP_TIMEOUT_SEC]);

// In the API call handler
const job = handleTranscriptionAndResponse(
  audioBlob,
  englishLevel,
  "hybrid",
  (data) => {
    // Reset watchdog on each data chunk
    if (streamWatchdogTimerRef.current !== null) {
      clearTimeout(streamWatchdogTimerRef.current);
      armWatchdog(job);
    }

    // Process data...
  },
  (error) => {
    // Handle error...
  },
  () => {
    // Clear watchdog on normal completion
    if (streamWatchdogTimerRef.current !== null) {
      clearTimeout(streamWatchdogTimerRef.current);
      streamWatchdogTimerRef.current = null;
    }
  }
);

// Arm watchdog initially
armWatchdog(job);
```

## Manual Testing

### Test 1: Normal Stream Behavior
1. Start recording with the mic button
2. Speak a sentence and stop recording
3. Observe the console logs:
   - `[UX] 🕐 Watchdog armed: 25s` (when streaming begins)
   - `[UX] 🕐 Watchdog armed: 25s` (each reset on data chunk)
4. Verify the assistant responds normally and the loading indicator stops

### Test 2: Stream Timeout
1. Start recording with the mic button
2. Say a phrase and stop recording
3. Simulate a server hang by:
   - Using network throttling in DevTools (Network tab → Throttling → Slow 3G)
   - Or temporarily disconnect from the internet after streaming begins
4. Wait for ~25 seconds
5. Observe the console logs:
   - `[UX] ⏱️ Watchdog fired after 25s of inactivity`
6. Verify the loading indicator disappears and the UI becomes interactive again

### Test 3: Stream Cancellation
1. In Chrome DevTools, go to Network tab
2. Start recording and speak a sentence
3. Stop recording and wait for the stream to start
4. In DevTools, find the `/speaking_transcribe` request
5. Right-click and select "Cancel request" to simulate an aborted request
6. Verify the watchdog behaves correctly:
   - Either the request cancellation is caught normally
   - Or the watchdog fires after 25 seconds

## Expected Behavior

1. The UI should never remain in a "loading" state for more than 25 seconds without activity
2. Each stream data event should reset the timeout
3. Normal completion should clear the watchdog timer
4. Watchdog firing should clear loading states and make the UI interactive again

## Test Coverage

The implementation ensures:
- No hanging UI when streams are interrupted
- Automatic recovery from network/server issues
- Defense against incomplete/interrupted audio streams
- Properly timed fallback when no server response is received
