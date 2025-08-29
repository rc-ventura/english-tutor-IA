# SpeakingTab Integration Testing Guide

## Overview

This document provides comprehensive testing procedures for validating the full integration of the SpeakingTab component in both immersive and hybrid teaching modes. These tests go beyond unit testing to ensure all components work together properly in real-world scenarios.

## Prerequisites

1. Development environment running (`npm run dev` in frontend directory)
2. Backend server running (`python main.py` in project root)
3. Working microphone
4. Network connectivity for API calls
5. Chrome DevTools or similar for monitoring network activity and console logs

## Test Matrix

| Test ID | Mode      | Level | Network | Audio | Description                                    |
|---------|-----------|-------|---------|-------|------------------------------------------------|
| I-1     | Immersive | A2    | Normal  | Yes   | Basic conversation flow                        |
| I-2     | Immersive | B1    | Flaky   | Yes   | Handling network instability                   |
| I-3     | Immersive | C1    | Normal  | No    | Empty audio recording                          |
| H-1     | Hybrid    | A2    | Normal  | Yes   | Basic conversation flow                        |
| H-2     | Hybrid    | B1    | Flaky   | Yes   | Handling network instability                   |
| H-3     | Hybrid    | C1    | Normal  | No    | Empty audio recording                          |
| X-1     | Both      | B1    | Normal  | Yes   | Multiple conversation turns                    |
| X-2     | Both      | B1    | Offline | Yes   | Complete offline handling                      |
| X-3     | Both      | B1    | Normal  | Yes   | Audio playback issues                          |

## Watchdog Verification

During tests that involve streaming responses, verify the following console messages appear:

1. **Watchdog Reset**: `[UX] 🔄 Stream watchdog reset (received chunk)`
   - Should appear each time a new chunk is received
   - Confirms the watchdog timer is being properly reset

2. **Watchdog Fired** (only if timeout occurs): `[UX] ⏱️ Stream watchdog fired after 25s without activity; cancelling job.`
   - Should appear if no chunks are received for ~25 seconds
   - Confirms the watchdog timer triggers correctly on timeout

## Test Case Details

### I-1: Immersive Mode - Basic Conversation Flow

**Setup:**
1. Navigate to Speaking tab
2. Select "Immersive" mode
3. Select "A2" level
4. Open browser console (F12 > Console tab)

**Steps:**
1. Click microphone button and speak a simple phrase (e.g., "Hello, how are you?")
2. Stop recording after 3-5 seconds
3. Observe the entire flow (recording → transcription → response → audio playback)
4. Monitor console for watchdog messages

**Expected Results:**
- User's speech transcription appears in a chat bubble
- Loading indicator shows during transcription/generation
- Assistant's audio plays automatically
- Assistant's text appears in chat bubble
- Audio indicator shows during playback
- No error messages in console
- Watchdog reset messages appear as chunks are received:
  - `[UX] 🔄 Stream watchdog reset (received chunk)` (multiple times)

**Verification Points:**
- Speech recognition accuracy
- Response relevance to input
- Audio quality and pronunciation
- Timing between steps
- Watchdog reset messages in console

### I-2/H-2: Network Instability Tests

**Setup:**
1. Navigate to Speaking tab
2. Select either "Immersive" or "Hybrid" mode
3. Open Chrome DevTools > Network tab
4. Open Console tab in DevTools
5. Enable "Slow 3G" throttling

**Steps:**
1. Record audio message
2. Observe behavior during processing
3. Watch for watchdog messages in console
4. Watch for watchdog activation (if delay exceeds 25s)

**Expected Results:**
- System handles slowness gracefully
- Reset messages may appear less frequently: `[UX] 🔄 Stream watchdog reset (received chunk)`
- If timeout occurs, watchdog cancels the job (after ~25s)
- Watchdog fired message appears: `[UX] ⏱️ Stream watchdog fired after 25s without activity; cancelling job.`
- UI returns to interactive state
- Appropriate error message or recovery

**Verification Points:**
- Error handling
- UI responsiveness during network issues
- Recovery after network restoration
- Watchdog messages appear at appropriate times

### I-3/H-3: Empty Audio Recording

**Setup:**
1. Navigate to Speaking tab
2. Select either mode
3. Select any level

**Steps:**
1. Click microphone button
2. Wait 1 second without speaking
3. Stop recording

**Expected Results:**
- System detects empty/invalid audio
- Appropriate error message shown to user
- No hanging UI states
- Console log indicates empty recording detection

**Verification Points:**
- Error message clarity
- UI recovery
- No crash or freeze

### X-1: Multiple Conversation Turns

**Setup:**
1. Navigate to Speaking tab
2. Select either mode
3. Select "B1" level

**Steps:**
1. Complete a normal conversation turn
2. After receiving response, initiate a second recording
3. Continue for at least 3 conversation turns
4. Check conversation history preservation

**Expected Results:**
- Full conversation history maintained
- Each turn works correctly
- Audio context remains properly initialized
- No degradation in performance over multiple turns

**Verification Points:**
- Message ordering
- Context preservation
- Memory usage (no leaks)

### X-2: Complete Offline Handling

**Setup:**
1. Navigate to Speaking tab
2. Open DevTools > Network tab
3. Select "Offline" option

**Steps:**
1. Record audio message
2. Observe error handling

**Expected Results:**
- Clean error messaging
- No hanging UI states
- Watchdog activates if needed
- Console shows connection errors
- UI remains interactive

**Verification Points:**
- Error message clarity
- UI recovery
- Resource cleanup

### X-3: Audio Playback Issues

**Setup:**
1. Navigate to Speaking tab
2. Mute system audio or use headphones disconnected

**Steps:**
1. Complete normal conversation flow
2. Observe handling when audio cannot play

**Expected Results:**
- System attempts to play audio
- UI doesn't hang if audio fails
- Text still displays even if audio fails
- Console shows audio playback issues

**Verification Points:**
- Error handling
- Text fallback when audio fails
- UI responsiveness

## Metrics Tracking

During testing, monitor these metrics:

1. **Response time:** Time from end of recording to first response chunk
2. **Audio processing time:** Duration of audio transcription
3. **Watchdog events:** Count of arming, resets, and timeout events
4. **Error rate:** Percentage of interactions with errors

## Error Scenarios Documentation

For each error encountered, document:

1. Exact error message and stack trace
2. Steps to reproduce
3. Console output (including all watchdog messages)
4. Network request details
5. Expected vs. actual behavior
6. Screenshots if applicable

## Environment Variables To Test

Test with different values for:

1. `VITE_SPEAKING_STEP_TIMEOUT_SEC` (default: 25s)
2. `STREAM_TIMEOUT_MS` (default: 25000ms)

## Notes

- Integration tests should be performed across different devices/browsers if possible
- Pay special attention to mobile device behavior
- Audio quality should be tested in different environments (quiet/noisy)
- Test both short responses and extended conversations
