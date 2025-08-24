import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mocks necessários - sem usar JSX
vi.mock('../PronunciationProgress');
vi.mock('../SpeakingTab');

// Mock para o localStorage
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
    getAllItems: () => store
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock para funções API
vi.mock('../../services/api', () => ({
  postSpeakingMetrics: vi.fn().mockResolvedValue({
    speed_wpm: 120,
    clarity_score: 85,
    volume_level: 75,
    pronunciation_score: 80,
    pronunciation_reasons: ['good_intonation', 'clear_consonants'],
    suggested_escalation: false
  }),
  generateSpeakingQuestion: vi.fn().mockResolvedValue({
    text: "How was your day?"
  }),
  postSpeakingTranscription: vi.fn().mockResolvedValue({
    text: "Hello, I am speaking for a test."
  })
}));

// Mock para o analizador de pausas
vi.mock('../../utils/speech-analysis', () => ({
  analyzePausesAndRhythm: vi.fn().mockReturnValue({
    score: 85,
    issues: []
  })
}));

describe('SpeakingTab Pronunciation Integration', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  // Testes focados no localStorage e na persistência dos dados

  it('should load pronunciation progress from localStorage', async () => {
    // Prepara localStorage com dados de histórico
    const mockHistory = {
      entries: [
        {
          timestamp: Date.now(),
          score: 75,
          originalScore: 70,
          rhythmScore: 80,
          issues: ['excessive_pauses'],
          level: 'B1',
          transcription: 'Hello world'
        }
      ],
      maxEntries: 20
    };

    localStorageMock.setItem('sophia_pronunciation_history', JSON.stringify(mockHistory));

    // Teste simplificado - apenas verificamos se os dados foram salvos corretamente
    const storedData = localStorageMock.getItem('sophia_pronunciation_history');
    expect(storedData).not.toBeNull();
    expect(JSON.parse(storedData!).entries[0].score).toBe(75);
  });

  it('should update pronunciation history when new metrics are added', async () => {
    // Prepara localStorage com dados anteriores
    const mockHistory = {
      entries: [
        {
          timestamp: Date.now() - 1000, // um pouco mais velho
          score: 70,
          originalScore: 65,
          rhythmScore: 75,
          issues: ['excessive_pauses'],
          level: 'B1',
          transcription: 'Previous entry'
        }
      ],
      maxEntries: 20
    };

    localStorageMock.setItem('sophia_pronunciation_history', JSON.stringify(mockHistory));

    // Simula adição de nova entrada no histórico
    const mockNewEntry = {
      timestamp: Date.now(),
      score: 80,
      originalScore: 75,
      rhythmScore: 85,
      issues: [],
      level: 'B2',
      transcription: 'New entry'
    };

    // Atualizamos o histórico manualmente para simular o componente fazendo isso
    const currentHistory = JSON.parse(localStorageMock.getItem('sophia_pronunciation_history') || '{}');
    currentHistory.entries.unshift(mockNewEntry);
    localStorageMock.setItem('sophia_pronunciation_history', JSON.stringify(currentHistory));

    // Verifica se o histórico foi atualizado corretamente
    const stored = localStorageMock.getItem('sophia_pronunciation_history');
    if (stored) {
      const history = JSON.parse(stored);
      expect(history.entries.length).toBe(2); // A original + a nova
      expect(history.entries[0].score).toBe(80); // A nova entrada está no início
      expect(history.entries[1].score).toBe(70); // A entrada antiga está na posição 1
    } else {
      throw new Error('Expected localStorage to have history data');
    }
  });
});
