
/**
 * This file contains TypeScript type definitions for the data structures
 * received from the Gradio backend API. These types ensure that we can
 * safely handle the API responses in our application.
 */

// Represents a file object returned by Gradio. It can contain a server path or a direct URL.
export interface GradioFile {
  path?: string;
  url?: string;
  // Gradio may include other metadata, but we only need path and url.
}

// Represents a single chat message object as defined by the Gradio Chatbot component.
export interface GradioChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// Payload for the /handle_bot_response endpoint.
// It returns the updated chat history and the audio file for the bot's response.
export type GradioBotResponsePayload = [GradioChatMessage[], GradioFile];

// Payload for the /generate_random_topic endpoint.
// It returns a new chat history containing the generated topic.
export type GradioTopicPayload = [GradioChatMessage[]];

// Payload for the /process_input (evaluation) endpoint.
// It returns a new chat history containing the essay feedback.
export type GradioEvaluationPayload = [GradioChatMessage[]];

// Payload for the /play_audio endpoint.
// It returns the audio file corresponding to the last generated feedback.
export type GradioAudioPlaybackPayload = [GradioFile | null];

// Payload for the /get_progress_html endpoint.
// It returns the user's progress dashboard as an HTML string.
export type GradioProgressPayload = [string | null];

// Payload for the /set_api_key_ui endpoint.
// It returns a status message string.
export type GradioApiKeyStatusPayload = [string | null];
