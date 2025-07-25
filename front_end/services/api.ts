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

const getFileUrl = (file: GradioFile): string | null =>
  file?.url ? file.url : file?.path ? `${BASE_URL}/file=${file.path}` : null;

// SET API KEY
export const setApiKey = async (apiKey: string): Promise<string> => {
  const client = await getClient();
  const result = await client.predict("/set_api_key_ui", { api_key: apiKey });
  const data = result.data as [string];
  return data[0] ?? "Error: No status message received.";
};

// AUDIO FLOW
export const handleTranscriptionAndResponse = async (
  audioBlob: Blob,
  level: EnglishLevel
): Promise<{ messages: ChatMessage[]; audioUrl: string | null }> => {
  const client = await getClient();

  // 1. Transcrição usando handle_file
  await client.predict("/speaking_transcribe", {
    audio_filepath: await handle_file(audioBlob),
    level,
  });

  // 2. Resposta do bot
  const response = await client.predict("/speaking_bot_response", { level });
  const [rawMessages, audioFile] = response.data as GradioBotResponsePayload;

  return {
    messages: formatMessages(rawMessages),
    audioUrl: getFileUrl(audioFile),
  };
};

// GERAR TÓPICO ALEATÓRIO
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

// PROCESSAR REDAÇÃO
export const processInput = async (
  essayText: string,
  writingType: WritingType,
  level: EnglishLevel
): Promise<ChatMessage[]> => {
  const client = await getClient();
  const response = await client.predict("/evaluate_essay", {
    input_data: essayText,
    writing_type: writingType,
    level,
  });
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
