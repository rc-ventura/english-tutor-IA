import { Client } from '@gradio/client';
import type { EnglishLevel, WritingType, ChatMessage } from '../types';
import type {
    GradioBotResponsePayload,
    GradioFile,
    GradioProgressPayload,
    GradioTopicPayload,
    GradioEvaluationPayload,
    GradioAudioPlaybackPayload,
} from './gradio';

const GRADIO_URL = "http://127.0.0.1:7860/";

let clientInstance: Promise<Client> | null = null;
const getClient = (): Promise<Client> => {
    if (!clientInstance) {
        clientInstance = Client.connect(GRADIO_URL);
    }
    return clientInstance;
};

const getFileUrl = (file: GradioFile): string | null => {
    if (file?.url) return file.url;
    if (file?.path) return `${GRADIO_URL}file=${file.path}`;
    return null;
}

const formatMessages = (rawMessages: any[]): ChatMessage[] => {
    if (!Array.isArray(rawMessages)) return [];
    return rawMessages.map(m => ({
        role: m.role,
        content: m.content
    }));
}

export const handleTranscriptionAndResponse = async (
    audioBlob: Blob,
    level: EnglishLevel
): Promise<{ messages: ChatMessage[], audioUrl: string | null }> => {
    const client = await getClient();

    // In Gradio, event chains often rely on session state. We replicate this by calling endpoints sequentially.
    // 1. First, send audio for transcription. The backend updates its internal chat history.
    await client.predict('/handle_transcription', {
        audio_filepath: audioBlob,
        level: level,
    });

    // 2. Then, ask for the bot's response based on the now-updated history.
    const response = await client.predict('/handle_bot_response', {
        level: level,
    });

    const [rawMessages, audioFile] = (response.data as GradioBotResponsePayload);
    const messages = formatMessages(rawMessages);
    const audioUrl = getFileUrl(audioFile);

    return { messages, audioUrl };
};


export const generateRandomTopic = async (
    level: EnglishLevel,
    writingType: WritingType
): Promise<ChatMessage[]> => {
    const client = await getClient();
    const response = await client.predict('/generate_random_topic', {
        level: level,
        writing_type: writingType,
    });
    const rawMessages = (response.data as GradioTopicPayload)[0];
    return formatMessages(rawMessages);
};

export const processInput = async (
    essayText: string,
    writingType: WritingType,
    level: EnglishLevel
): Promise<ChatMessage[]> => {
    const client = await getClient();
    // Note the parameter name mapping from our app to the Gradio API's specific names
    const response = await client.predict('/process_input', {
        input_data: essayText,
        writing_type: writingType, // correto: writing_type
        level: level,              // correto: level
    });
    const rawMessages = (response.data as GradioEvaluationPayload)[0];
    return formatMessages(rawMessages);
};

export const playLastAudio = async (): Promise<string | null> => {
     const client = await getClient();
     // This endpoint relies on the session state managed by the Gradio backend to identify the correct audio.
     const response = await client.predict('/play_audio', {});
     const audioFile = (response.data as GradioAudioPlaybackPayload)[0];
     if (!audioFile) return null;
     return getFileUrl(audioFile);
};


export const getProgressHtml = async (): Promise<string> => {
    const client = await getClient();
    const response = await client.predict('/get_progress_html', {});
    return (response.data as GradioProgressPayload)[0] ?? '';
};

export const setApiKey = async(apiKey: string): Promise<void> => {
    const client = await getClient();
    await client.predict