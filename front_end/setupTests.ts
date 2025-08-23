// Vitest setup file
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Ensure a short watchdog timeout during tests
// @ts-ignore
;(import.meta as any).env = { ...(import.meta as any).env, VITE_SPEAKING_STEP_TIMEOUT_SEC: '1' };

// Mock Gradio client to avoid network calls at module import time
vi.mock('@gradio/client', () => {
  const predict = vi.fn(async (_endpoint: string, _payload: any) => ({ data: [[], null] }));
  const submit = vi.fn((_endpoint: string, _payload: any) => {
    // minimal async iterable with cancel()
    const iterable: any = {
      async *[Symbol.asyncIterator]() {
        // yield nothing to end immediately
      },
      cancel: vi.fn(),
    };
    return iterable;
  });
  return {
    Client: {
      connect: vi.fn(async (_base?: string) => ({ predict, submit })),
    },
    handle_file: vi.fn(async (_b: Blob) => 'file'),
  };
});

// jsdom doesn't implement scrollIntoView
if (!(Element.prototype as any).scrollIntoView) {
  // @ts-ignore
  Element.prototype.scrollIntoView = vi.fn();
}

// Minimal AudioContext mock to satisfy SpeakingTab mount
class MockAudioBufferSourceNode {
  buffer: any = null;
  onended: (() => void) | null = null;
  connect() {}
  start() {
    // Immediately end
    if (typeof this.onended === 'function') this.onended();
  }
}

class MockAudioContext {
  state: 'suspended' | 'running' | 'closed' = 'running';
  resume = vi.fn(async () => {
    this.state = 'running';
  });
  close = vi.fn(async () => {
    this.state = 'closed';
  });
  decodeAudioData = vi.fn(async (_: ArrayBuffer) => ({ duration: 0 } as any));
  createBufferSource = vi.fn(() => new MockAudioBufferSourceNode());
  destination: any = {};
}

// @ts-ignore assign test mock
globalThis.AudioContext = (MockAudioContext as any);
// @ts-ignore WebKit alias
(globalThis as any).webkitAudioContext = MockAudioContext;

// navigator.mediaDevices.getUserMedia mock
if (!('mediaDevices' in navigator)) {
  // @ts-ignore add mediaDevices
  navigator.mediaDevices = {};
}
// @ts-ignore define gum
navigator.mediaDevices.getUserMedia = vi.fn(async () => ({ id: 'mock-stream' } as any));

// MediaRecorder mock
class MockMediaRecorder {
  stream: any;
  state: 'inactive' | 'recording' | 'paused' = 'inactive';
  ondataavailable: ((e: any) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor(stream: any) {
    this.stream = stream;
  }
  start() {
    this.state = 'recording';
    // Optionally emit a tiny chunk
    this.ondataavailable?.({ data: new Blob() });
  }
  stop() {
    this.state = 'inactive';
    this.onstop?.();
  }
}
// @ts-ignore assign global
globalThis.MediaRecorder = MockMediaRecorder as any;

// Always stub global fetch (tests can override as needed)
globalThis.fetch = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
  // Provide a generic OK response, with JSON matching SpeakingMetrics shape
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: async () => ({
      duration_sec: 2.1,
      speaking_time_sec: 1.6,
      speech_ratio: 0.76,
      pause_ratio: 0.24,
      rms_dbfs: -20,
      peak_dbfs: -3,
      clipping_ratio: 0.0,
      words: 5,
      wps: 2.5,
      wpm: 150,
      level: 'B1',
      suggested_escalation: false,
      reasons: [],
    }),
    text: async () => '',
    arrayBuffer: async () => new ArrayBuffer(0),
  } as any;
});
