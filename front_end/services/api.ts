import { Client, handle_file } from "@gradio/client";
import type { EnglishLevel, WritingType, ChatMessage } from "../types";
import type {
  GradioFile,
  GradioProgressPayload,
  GradioTopicPayload,
  GradioEvaluationPayload,
  GradioAudioPlaybackPayload,
} from "./gradio";

// Distinguish Gradio base (mounted under /gradio) from REST API base (root)
const GRADIO_BASE_URL = import.meta.env.VITE_GRADIO_BASE_URL as string;
const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) ||
  GRADIO_BASE_URL?.replace(/\/?gradio\/?$/, "") ||
  "";

// Verbose streaming logs only in development or when explicitly enabled
const VERBOSE_GRADIO_LOGS = Boolean(
  (import.meta as any).env?.DEV ||
    (import.meta as any).env?.VITE_VERBOSE_GRADIO_LOGS === "true"
);

// Conecta ao cliente Gradio usando o endpoint correto (/gradio)
const clientPromise = Client.connect(GRADIO_BASE_URL).catch((error) => {
  console.error("Falha ao conectar ao Gradio API:", error);
  return Promise.reject(error);
});

const getClient = () => clientPromise;

const formatMessages = (rawMessages: any[]): ChatMessage[] =>
  Array.isArray(rawMessages)
    ? rawMessages.map((m) => ({
        role: m.role,
        content: m.content,
        text_for_llm: (m as any).text_for_llm,
      }))
    : [];

type FileLike = GradioFile | string | null | undefined;

const getFileUrl = (file: FileLike): string | null => {
  if (!file) return null;

  // If backend sends plain string path
  if (typeof file === "string") {
    // Already absolute URL?
    if (file.startsWith("http://") || file.startsWith("https://")) {
      return file;
    }
    return `${GRADIO_BASE_URL}/file=${file}`;
  }

  // If backend sends structured object
  return (
    file.url ?? (file.path ? `${GRADIO_BASE_URL}/file=${file.path}` : null)
  );
};

// SET API KEY
export const setApiKey = async (apiKey: string): Promise<string> => {
  const client = await getClient();
  const result = await client.predict("/set_api_key_ui", { api_key: apiKey });
  const data = result.data as [string];
  return data[0] ?? "Error: No status message received.";
};

// AUDIO FLOW
export const handleTranscriptionAndResponse = (
  audioBlob: Blob,
  level: EnglishLevel,
  practiceMode: "hybrid" | "immersive",
  onData: (data: { messages: ChatMessage[]; audioUrl: string | null }) => void,
  onError: (error: Error) => void,
  onComplete?: () => void
) => {
  let job: ReturnType<Client["submit"]>;

  const process = async () => {
    try {
      const client = await getClient();

      // Step 1: Await the transcription using predict(), as it's a single event.
      const tx = await client.predict("/speaking_transcribe", {
        audio_filepath: await handle_file(audioBlob),
        level,
        speaking_mode: practiceMode === "hybrid" ? "Hybrid" : "Immersive",
      });

      // After transcription completes, immediately reflect the user's message in the UI
      try {
        const [rawMessages] = tx.data as [any[], any[]];
        onData({ messages: formatMessages(rawMessages), audioUrl: null });
      } catch (e) {
        console.warn(
          "Unexpected /speaking_transcribe payload; skipping immediate UI update",
          e
        );
      }

      // Step 2: Once transcription is done, submit the job to stream the bot's response.
      job = client.submit("/speaking_bot_response", {
        level,
        speaking_mode: practiceMode === "hybrid" ? "Hybrid" : "Immersive",
      });

      (async () => {
        try {
          let latestRawMessages: any[] | null = null;
          let latestAudioFile: any = null;
          for await (const msg of job) {
            if (msg.type === "data") {
              if (VERBOSE_GRADIO_LOGS) {
                console.log(" Gradio streaming raw msg.data:", msg.data);
              }
              const [rawMessages, audioFile] = msg.data as [any[], any];
              latestRawMessages = rawMessages;
              latestAudioFile = audioFile;
              if (practiceMode === "immersive") {
                // During immersive streaming, update messages but suppress audio URL until the end
                onData({
                  messages: formatMessages(rawMessages),
                  audioUrl: null,
                });
              } else {
                // Hybrid: stream audio URL as usual
                onData({
                  messages: formatMessages(rawMessages),
                  audioUrl: getFileUrl(audioFile),
                });
              }
            } else if (msg.type === "status" && msg.stage === "error") {
              console.error("Streaming job failed:", msg);
              onError(new Error(msg.message ?? "Streaming error"));
            }
          }
          // After the stream ends, if immersive, emit the final audio URL once
          if (practiceMode === "immersive" && latestAudioFile) {
            onData({
              messages: formatMessages(latestRawMessages || []),
              audioUrl: getFileUrl(latestAudioFile),
            });
          }
          // Signal normal completion
          if (onComplete) onComplete();
        } catch (streamErr) {
          console.error("Streaming iterator error:", streamErr);
          onError(streamErr as Error);
        }
      })();
    } catch (error) {
      console.error("Error in transcription/response process:", error);
      onError(error as Error);
    }
  };

  process();

  // Return a function to allow the component to cancel the job
  return () => {
    if (job) {
      job.cancel();
    }
  };
};

// GERAR TÓPICO ALEATÓRIO (STREAMING)
export const generateRandomTopicStream = (
  level: EnglishLevel,
  writingType: WritingType,
  onData: (messages: ChatMessage[]) => void,
  onError: (error: Error) => void
) => {
  let job: ReturnType<Client["submit"]>;
  const process = async () => {
    try {
      const client = await getClient();
      job = client.submit("/generate_topic", {
        level,
        writing_type: writingType,
      });
      (async () => {
        try {
          for await (const msg of job) {
            if (msg.type === "data") {
              const [rawMessages] = msg.data as [any[]];
              onData(formatMessages(rawMessages));
            } else if (msg.type === "status" && msg.stage === "error") {
              onError(new Error(msg.message ?? "Streaming error"));
            }
          }
        } catch (streamErr) {
          onError(streamErr as Error);
        }
      })();
    } catch (error) {
      onError(error as Error);
    }
  };
  process();
  return () => {
    if (job) job.cancel();
  };
};

// GERAR TÓPICO ALEATÓRIO (FALLBACK NÃO-STREAMING)
export const generateRandomTopic = async (
  level: EnglishLevel,
  writingType: WritingType
): Promise<ChatMessage[]> => {
  const client = await getClient();
  const response = await client.predict("/generate_topic", {
    level,
    writing_type: writingType,
  });
  const rawMessages = (response.data as GradioTopicPayload)[0];
  return formatMessages(rawMessages);
};

// PROCESSAR REDAÇÃO (STREAMING)
export const processInputStream = (
  essayText: string,
  writingType: WritingType,
  level: EnglishLevel,
  history: ChatMessage[],
  onData: (messages: ChatMessage[]) => void,
  onError: (error: Error) => void
) => {
  let job: ReturnType<Client["submit"]>;
  const process = async () => {
    try {
      const client = await getClient();
      // Ordem: essay_input_text, history_writing, english_level, writing_type
      job = client.submit("/evaluate_essay", [
        essayText,
        history,
        level,
        writingType,
      ]);
      (async () => {
        try {
          for await (const msg of job) {
            if (msg.type === "data") {
              const [rawMessages] = msg.data as [any[]];
              onData(formatMessages(rawMessages));
            } else if (msg.type === "status" && msg.stage === "error") {
              onError(new Error(msg.message ?? "Streaming error"));
            }
          }
        } catch (streamErr) {
          onError(streamErr as Error);
        }
      })();
    } catch (error) {
      onError(error as Error);
    }
  };
  process();
  return () => {
    if (job) job.cancel();
  };
};

// PROCESSAR REDAÇÃO
export const processInput = async (
  essayText: string,
  writingType: WritingType,
  level: EnglishLevel,
  history: ChatMessage[]
): Promise<ChatMessage[]> => {
  const client = await getClient();
  // Ordem: essay_input_text, history_writing, english_level, writing_type
  const response = await client.predict("/evaluate_essay", [
    essayText,
    history,
    level,
    writingType,
  ]);
  const rawMessages = (response.data as GradioEvaluationPayload)[0];
  return formatMessages(rawMessages);
};

// REPRODUZIR ÁUDIO
export const playLastAudio = async (): Promise<string | null> => {
  const client = await getClient();
  const response = await client.predict("/play_audio", {});
  const audioFile = (response.data as GradioAudioPlaybackPayload)[0];
  return getFileUrl(audioFile);
};

// PROGRESSO
export const getProgressHtml = async (): Promise<string> => {
  const client = await getClient();
  const response = await client.predict("/get_progress_html", {});
  return (
    (response.data as GradioProgressPayload)[0] ??
    '<p class="text-gray-400">No progress data available.</p>'
  );
};

// ---------- Escalation API ----------
export interface Escalation {
  id: string;
  created_at: string;
  status: "queued" | "resolved";
  source?: "speaking" | "writing" | null;
  practice_mode?: "Hybrid" | "Immersive" | null;
  level?: string | null;
  message_index?: number | null;
  reasons?: string[] | null;
  user_note?: string | null;
  assistant_text?: string | null;
  user_last_text?: string | null;
  history_preview?: any[] | null;
  audio_relpath?: string | null;
  audio_url_at_submit?: string | null;
  user_id?: string | null;
  meta?: Record<string, any> | null;
  resolved_at?: string | null;
  resolution_note?: string | null;
}

export interface CreateEscalationPayload {
  source?: "speaking" | "writing";
  practiceMode?: "Hybrid" | "Immersive";
  level?: string;
  messageIndex?: number;
  reasons?: string[];
  userNote?: string;
  assistantText?: string;
  userLastText?: string;
  historyPreview?: ChatMessage[];
  audioUrl?: string | null;
  userId?: string;
  meta?: Record<string, any>;
}

const jsonFetch = async <T = any>(
  url: string,
  init?: RequestInit
): Promise<T> => {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return (await res.json()) as T;
};

export const createEscalation = async (
  payload: CreateEscalationPayload
): Promise<Escalation> => {
  return jsonFetch<Escalation>(`${API_BASE_URL}/api/escalations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const listEscalations = async (
  status?: "queued" | "resolved"
): Promise<Escalation[]> => {
  const url = status
    ? `${API_BASE_URL}/api/escalations?status=${encodeURIComponent(status)}`
    : `${API_BASE_URL}/api/escalations`;
  return jsonFetch<Escalation[]>(url);
};

export const resolveEscalation = async (
  escalationId: string,
  resolutionNote?: string
): Promise<Escalation> => {
  return jsonFetch<Escalation>(
    `${API_BASE_URL}/api/escalations/${encodeURIComponent(
      escalationId
    )}/resolve`,
    {
      method: "POST",
      body: JSON.stringify(
        resolutionNote ? { resolution_note: resolutionNote } : {}
      ),
    }
  );
};

export const getEscalation = async (
  escalationId: string
): Promise<Escalation> => {
  return jsonFetch<Escalation>(
    `${API_BASE_URL}/api/escalations/${encodeURIComponent(escalationId)}`
  );
};

export const getEscalationAudioUrl = (escalationId: string): string => {
  return `${API_BASE_URL}/api/escalations/${encodeURIComponent(
    escalationId
  )}/audio`;
};

// ---------- Speaking Metrics API ----------
export interface SpeakingMetricsPayload {
  userAudioBase64?: string; // data URL or raw base64
  userAudioUrl?: string; // absolute path or /file= URL
  transcript?: string;
  level?: string; // CEFR
}

export interface SpeakingMetrics {
  duration_sec: number;
  speaking_time_sec: number;
  speech_ratio: number;
  pause_ratio: number;
  rms_dbfs: number;
  peak_dbfs: number;
  clipping_ratio: number;
  words?: number | null;
  wps?: number | null;
  wpm?: number | null;
  level?: string | null;
  suggested_escalation: boolean;
  reasons: string[];
}

export const postSpeakingMetrics = async (
  payload: SpeakingMetricsPayload
): Promise<SpeakingMetrics> => {
  return jsonFetch<SpeakingMetrics>(`${API_BASE_URL}/api/speaking/metrics`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
};
