import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, EnglishLevel } from "../types";
import Chatbot from "./Chatbot";
import { MicIcon, StopCircleIcon } from "./icons/Icons";
import * as api from "../services/api";

interface SpeakingTabProps {
  englishLevel: EnglishLevel;
}

const SpeakingTab: React.FC<SpeakingTabProps> = ({ englishLevel }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm Sophia, your AI English tutor. Let's practice speaking. Press the microphone button and start talking.",
    },
  ]);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const audioPlayerRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const audioEl = audioPlayerRef.current;
    return () => {
      if (audioEl) {
        audioEl.pause();
        audioEl.src = "";
      }
    };
  }, []);

  const handleStopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsLoading(true);
    }
  };

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setIsRecording(true);
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });
        const userPlaceholder: ChatMessage = {
          role: "user",
          content: "[Your speech is being processed...]",
        };
        setMessages((prev) => [...prev, userPlaceholder]);

        try {
          const { messages: newMessages, audioUrl } =
            await api.handleTranscriptionAndResponse(audioBlob, englishLevel);
          setMessages(newMessages);

          if (audioUrl && audioPlayerRef.current) {
          }

          setMessages(newMessages);
        } catch (error) {
          console.error("Error handling transcription and response:", error);
          const errorMsg: ChatMessage = {
            role: "assistant",
            content: "Sorry, I couldn't process your audio.",
          };
          setMessages((prev) => [...prev, errorMsg]);
        } finally {
          setIsLoading(false);
          stream.getTracks().forEach((track) => track.stop());
        }
      };
      recorder.start();
    } catch (err) {
      console.error("Failed to get microphone:", err);
      alert(
        "Could not access the microphone. Please check your browser permissions."
      );
    }
  };

  const handleToggleRecording = () => {
    if (isRecording) {
      handleStopRecording();
    } else {
      handleStartRecording();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto pr-4">
        <Chatbot messages={messages} isLoading={isLoading} />
      </div>
      <div className="mt-6">
        <div className="flex flex-col items-center justify-center">
          <button
            onClick={handleToggleRecording}
            className={`flex items-center justify-center w-20 h-20 rounded-full transition-all duration-300 ease-in-out focus:outline-none focus:ring-4 focus:ring-opacity-50
                    ${
                      isRecording
                        ? "bg-red-600 hover:bg-red-700 focus:ring-red-400"
                        : "bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-400"
                    }`}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
          >
            {isRecording ? (
              <StopCircleIcon className="w-10 h-10 text-white" />
            ) : (
              <MicIcon className="w-10 h-10 text-white" />
            )}
          </button>
          <p className="mt-3 text-sm text-gray-400">
            {isRecording
              ? "Recording... Click to stop."
              : isLoading
              ? "Processing..."
              : "Press the button to speak"}
          </p>
        </div>
      </div>
      <audio ref={audioPlayerRef} className="hidden" />
    </div>
  );
};

export default SpeakingTab;
