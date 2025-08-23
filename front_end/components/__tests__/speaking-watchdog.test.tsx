import { render } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as api from '../../services/api';
// NOTE: Import component after importing the module we will spy on
import SpeakingTab, { __TEST_ONLY__ } from '../SpeakingTab';

// Spy for cancel function returned by the streaming API
const cancelMock = vi.fn();

describe('SpeakingTab stream watchdog', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    cancelMock.mockClear();
    vi.spyOn(api, 'handleTranscriptionAndResponse').mockImplementation(
      (_blob: Blob, _level: any, _mode: any, _onData: any, _onError: any, _onComplete?: () => void) => {
        // Do not call onData or onComplete -> simulates a hanging stream
        return cancelMock;
      }
    );
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('cancels a hanging streaming job on timeout', () => {
    // 1) Render the component
    render(<SpeakingTab englishLevel={'B1' as any} />);

    // 2) Configurar o cancelMock como o streamingJobRef.current
    __TEST_ONLY__.streamingJobRef.current = cancelMock;

    // 3) Capturar avisos do console
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    // 4) Chamar resetWatchdog para iniciar o timer
    if (__TEST_ONLY__.resetWatchdog) {
      __TEST_ONLY__.resetWatchdog();
    } else {
      throw new Error('resetWatchdog function not available');
    }

    // 5) Avançar o tempo para disparar o timeout
    vi.advanceTimersByTime(30 * 1000 + 100); // Adicionar 100ms extra para garantir

    // 6) Verificar se o cancelMock foi chamado
    expect(cancelMock).toHaveBeenCalledTimes(1);

    warnSpy.mockRestore();
  });
});
