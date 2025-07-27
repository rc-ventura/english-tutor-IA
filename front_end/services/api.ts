import { Client, handle_file } from "@gradio/client";
import type { EnglishLevel, WritingType, ChatMessage } from "../types";
import type {
  GradioBotResponsePayload,
  GradioFile,
  GradioProgressPayload,
  GradioTopicPayload,
  GradioEvaluationPayload,
  GradioAudioPlaybackPayload,
} from "./gradio";

const BASE_URL = "http://localhost:7901";

// Conecta ao cliente Gradio usando o endpoint correto
const clientPromise = Client.connect(BASE_URL, {
  protocol: "http",
  host: "localhost:7901",
}).catch((error) => {
  console.error("Falha ao conectar ao Gradio API:", error);
  return Promise.reject(error);
});

const getClient = () => clientPromise;

const formatMessages = (rawMessages: any[]): ChatMessage[] =>
  Array.isArray(rawMessages)
    ? rawMessages.map((m) => ({ role: m.role, content: m.content }))
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
    return `${BASE_URL}/file=${file}`;
  }

  // If backend sends structured object
  return file.url ?? (file.path ? `${BASE_URL}/file=${file.path}` : null);
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
  onData: (data: { messages: ChatMessage[]; audioUrl: string | null }) => void,
  onError: (error: Error) => void
) => {
  let job;

  const process = async () => {
    try {
      const client = await getClient();

      // Step 1: Await the transcription using predict(), as it's a single event.
      await client.predict("/speaking_transcribe", {
        audio_filepath: await handle_file(audioBlob),
        level,
      });

      // Step 2: Once transcription is done, submit the job to stream the bot's response.
      job = client.submit("/speaking_bot_response", { level });

      (async () => {
        try {
          for await (const msg of job) {
            if (msg.type === "data") {
              console.log("🟣 Gradio streaming raw msg.data:", msg.data);
              const [rawMessages, audioFile] = msg.data as [any[], any];
              onData({
                messages: formatMessages(rawMessages),
                audioUrl: getFileUrl(audioFile),
              });
            } else if (msg.type === "status" && msg.stage === "error") {
              console.error("Streaming job failed:", msg);
              onError(new Error(msg.message ?? "Streaming error"));
            }
          }
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
  let job;
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
  let job;
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
