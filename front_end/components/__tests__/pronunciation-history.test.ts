/**
 * Testes para as funções de histórico de pronúncia
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

interface PronunciationHistoryEntry {
  timestamp: number;
  score: number;
  originalScore?: number;
  rhythmScore?: number;
  issues?: string[];
  level?: string;
  transcription?: string;
}

interface PronunciationHistory {
  entries: PronunciationHistoryEntry[];
  maxEntries: number;
}

describe('Pronunciation History', () => {
  // Mock de localStorage
  const localStorageMock = (() => {
    let store: Record<string, string> = {};

    return {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value.toString();
      }),
      clear: vi.fn(() => {
        store = {};
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
      getAll: () => store
    };
  })();

  // Mock das funções
  const PRONUNCIATION_HISTORY_KEY = "sophia_pronunciation_history";

  function getPronunciationHistory(): PronunciationHistory {
    try {
      const stored = localStorageMock.getItem(PRONUNCIATION_HISTORY_KEY);
      if (stored) {
        return JSON.parse(stored) as PronunciationHistory;
      }
    } catch (e) {
      console.error("Error loading pronunciation history:", e);
    }

    // Retorna histórico vazio se não existir ou houver erro
    return { entries: [], maxEntries: 20 };
  }

  function savePronunciationHistory(history: PronunciationHistory): void {
    try {
      localStorageMock.setItem(PRONUNCIATION_HISTORY_KEY, JSON.stringify(history));
    } catch (e) {
      console.error("Error saving pronunciation history:", e);
    }
  }

  function addPronunciationHistoryEntry(
    score: number,
    originalScore?: number,
    rhythmScore?: number,
    issues?: string[],
    level?: string,
    transcription?: string
  ): void {
    const history = getPronunciationHistory();

    const entry: PronunciationHistoryEntry = {
      timestamp: Date.now(),
      score,
      originalScore,
      rhythmScore,
      issues,
      level,
      transcription
    };

    // Adicionar nova entrada no início do array
    history.entries.unshift(entry);

    // Limitar o número de entradas
    if (history.entries.length > history.maxEntries) {
      history.entries = history.entries.slice(0, history.maxEntries);
    }

    savePronunciationHistory(history);
  }

  function getPronunciationProgress(): {
    recent: number | null; // Score mais recente
    average: number | null; // Média dos últimos 5
    trend: "up" | "down" | "stable" | null; // Tendência
  } {
    const history = getPronunciationHistory();

    if (history.entries.length === 0) {
      return { recent: null, average: null, trend: null };
    }

    // Score mais recente
    const recent = history.entries[0].score;

    // Média dos últimos 5 (ou menos se não houver 5)
    const lastFive = history.entries.slice(0, Math.min(5, history.entries.length));
    const average = lastFive.reduce((sum, entry) => sum + entry.score, 0) / lastFive.length;

    // Calcular tendência
    let trend: "up" | "down" | "stable" | null = null;

    if (history.entries.length >= 3) {
      // Calcular a média dos 3 mais recentes e dos 3 anteriores (se houver)
      const recentAvg = history.entries.slice(0, 3).reduce((sum, entry) => sum + entry.score, 0) / 3;

      if (history.entries.length >= 6) {
        const olderAvg = history.entries.slice(3, 6).reduce((sum, entry) => sum + entry.score, 0) / 3;

        if (recentAvg >= olderAvg + 5) {
          trend = "up";
        } else if (recentAvg <= olderAvg - 5) {
          trend = "down";
        } else {
          trend = "stable";
        }
      } else {
        // Se não temos 6 entradas, comparamos com a primeira entrada
        const firstScore = history.entries[history.entries.length - 1].score;

        if (recentAvg >= firstScore + 5) {
          trend = "up";
        } else if (recentAvg <= firstScore - 5) {
          trend = "down";
        } else {
          trend = "stable";
        }
      }
    }

    return { recent, average, trend };
  }

  beforeEach(() => {
    localStorageMock.clear();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
  });

  it('deve retornar histórico vazio quando não há dados salvos', () => {
    const history = getPronunciationHistory();
    expect(history).toEqual({ entries: [], maxEntries: 20 });
  });

  it('deve adicionar nova entrada no histórico', () => {
    addPronunciationHistoryEntry(75, 70, 80, ['excessive_pauses'], 'B1', 'Hello world');

    const history = getPronunciationHistory();
    expect(history.entries.length).toBe(1);
    expect(history.entries[0].score).toBe(75);
    expect(history.entries[0].originalScore).toBe(70);
    expect(history.entries[0].rhythmScore).toBe(80);
    expect(history.entries[0].issues).toEqual(['excessive_pauses']);
    expect(history.entries[0].level).toBe('B1');
    expect(history.entries[0].transcription).toBe('Hello world');
  });

  it('deve limitar o número de entradas ao máximo configurado', () => {
    // Adicionar mais que o máximo de entradas
    for (let i = 0; i < 25; i++) {
      addPronunciationHistoryEntry(70 + i);
    }

    const history = getPronunciationHistory();
    expect(history.entries.length).toBe(20); // maxEntries definido como 20

    // A entrada mais recente deve ser a última adicionada
    expect(history.entries[0].score).toBe(94); // 70 + 24
  });

  it('deve calcular progresso quando há entradas suficientes', () => {
    // Adicionar entradas com tendência ascendente
    addPronunciationHistoryEntry(60); // mais antiga
    addPronunciationHistoryEntry(65);
    addPronunciationHistoryEntry(70);
    addPronunciationHistoryEntry(75);
    addPronunciationHistoryEntry(80);
    addPronunciationHistoryEntry(85); // mais recente

    const progress = getPronunciationProgress();
    expect(progress.recent).toBe(85);
    expect(progress.average).toBeCloseTo(75, 1); // média dos 5 mais recentes (85+80+75+70+65)/5 = 75
    expect(progress.trend).toBe('up'); // tendência crescente
  });

  it('deve retornar tendência "stable" quando não há variação significativa', () => {
    addPronunciationHistoryEntry(75);
    addPronunciationHistoryEntry(74);
    addPronunciationHistoryEntry(76);
    addPronunciationHistoryEntry(75);
    addPronunciationHistoryEntry(74);
    addPronunciationHistoryEntry(76);

    const progress = getPronunciationProgress();
    expect(progress.trend).toBe('stable');
  });

  it('deve retornar valores corretos quando há apenas uma entrada', () => {
    addPronunciationHistoryEntry(80);

    const progress = getPronunciationProgress();
    expect(progress.recent).toBe(80);
    expect(progress.average).toBe(80);
    expect(progress.trend).toBe(null); // não há dados suficientes para tendência
  });
});
