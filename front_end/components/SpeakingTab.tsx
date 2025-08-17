import React, { useState, useRef, useEffect } from "react";
import { ChatMessage, EnglishLevel } from "../types";
import Chatbot from "./Chatbot";
import {
  MicIcon,
  StopCircleIcon,
  HeadphonesIcon,
  MessageSquareTextIcon,
} from "./icons/Icons";
import * as api from "../services/api";

interface SpeakingTabProps {
  englishLevel: EnglishLevel;
}

const SpeakingTab: React.FC<SpeakingTabProps> = ({ englishLevel }) => {
  const [practiceMode, setPracticeMode] = useState<"hybrid" | "immersive">(
    "hybrid"
  );
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
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioPlayedRef = useRef<boolean>(false);
  const awaitingAssistantRef = useRef<boolean>(false);
  const [botSpeaking, setBotSpeaking] = useState<boolean>(false);
  const streamingJobRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // Escolhe o construtor disponível e tipa para satisfazer o TS
    const AudioContextCtor = (window.AudioContext ??
      (window as any).webkitAudioContext) as {
      new (): AudioContext;
    };
    audioContextRef.current = new AudioContextCtor();

    return () => {
      audioContextRef.current?.close();
      if (streamingJobRef.current) streamingJobRef.current();
    };
  }, []);

  // Unlocks the audio context on the first user interaction
  const unlockAudioContext = () => {
    if (
      audioContextRef.current &&
      audioContextRef.current.state === "suspended"
    ) {
      audioContextRef.current.resume();
    }
  };

  // Plays audio from a URL using the Web Audio API
  const playAudio = async (url: string) => {
    if (!audioContextRef.current) return;
    console.log("🔊 Attempting to play audio from URL:", url);
    try {
      console.log("🔊 Fetching audio from URL...");
      const response = await fetch(url);
      console.log(
        "🔊 Fetch response status:",
        response.status,
        response.statusText
      );

      if (!response.ok) {
        console.error(
          "🔊 Failed to fetch audio:",
          response.status,
          response.statusText
        );
        return;
      }

      const arrayBuffer = await response.arrayBuffer();
      console.log(
        "🔊 Audio data received, size:",
        arrayBuffer.byteLength,
        "bytes"
      );
      const audioBuffer = await audioContextRef.current.decodeAudioData(
        arrayBuffer
      );
      console.log(
        "🔊 Audio decoded successfully. Duration:",
        audioBuffer.duration.toFixed(2),
        "s"
      );
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      // FIX: Add a small delay to prevent audio quality issues on autoplay
      const playTimeout = setTimeout(() => {
        console.log("🔊 Starting audio playback after short delay...");
        setBotSpeaking(true);
        source.start(0);
      }, 150); // 150ms delay is enough for the browser to settle.

      source.onended = () => {
        console.log("🔊 Audio playback finished");
        setBotSpeaking(false);
      };
    } catch (error) {
      console.error("Error playing audio with Web Audio API:", error);
    }
  };

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
    unlockAudioContext(); // Unlock audio on user gesture
    audioPlayedRef.current = false; // Reset for the new interaction
    console.info(
      `[UX] 🎙️ handleStartRecording: start (mode=${practiceMode}, level=${englishLevel})`
    );

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.debug("[UX] 🎤 getUserMedia acquired");
      setIsRecording(true);
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        console.info("[UX] ⏹️ recorder.onstop");
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });
        console.debug(
          `[UX] 💾 audioBlob size=${audioBlob.size}B, chunks=${audioChunksRef.current.length}`
        );
        const userPlaceholder: ChatMessage = { role: "user", content: null };
        const botPlaceholder: ChatMessage = {
          role: "assistant",
          content: null,
        };
        // Show both bubbles immediately with loading placeholders; onData will replace them with real content
        setMessages((prev) => [...prev, userPlaceholder, botPlaceholder]);
        awaitingAssistantRef.current = true;

        const handleError = (error: Error) => {
          console.error("Streaming Error:", error);
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Sorry, an error occurred." },
          ]);
          setIsLoading(false);
        };

        // Start the streaming job
        console.info(
          `[UX] 🚀 start streaming (mode=${practiceMode}, level=${englishLevel})`
        );
        streamingJobRef.current = api.handleTranscriptionAndResponse(
          audioBlob,
          englishLevel,
          practiceMode,
          (data) => {
            // onData callback
            const { messages: serverMessages, audioUrl } = data;
            console.debug(
              `[UX] 🟢 onData: messages=${
                serverMessages.length
              }, audioUrl=${Boolean(audioUrl)}`
            );
            if (audioUrl && !audioPlayedRef.current) {
              console.info("[UX] 🔊 playAudio invoked");
              playAudio(audioUrl);
              audioPlayedRef.current = true;
            }

            // Keep assistant placeholder visible across the user transcription update and until assistant text arrives
            let merged = serverMessages as ChatMessage[];
            const last = merged[merged.length - 1];
            const lastIsAssistantPending =
              !!last &&
              last.role === "assistant" &&
              (last.content == null || (typeof last.content !== "string" && !(last as any).text_for_llm));
            const hasAssistantText = merged.some(
              (m) =>
                m.role === "assistant" &&
                (typeof m.content === "string" || (m as any).text_for_llm)
            );
            const needsAssistantPlaceholder =
              awaitingAssistantRef.current || !!audioUrl || isLoading || botSpeaking;
            if (needsAssistantPlaceholder && !lastIsAssistantPending) {
              merged = [...merged, { role: "assistant", content: null }];
            }
            // Stop awaiting only once assistant textual content appears
            awaitingAssistantRef.current = !hasAssistantText;

            setMessages(merged);
            setIsLoading(false);
            console.debug("[UX] ✅ onData applied to UI (merged)");
          },
          handleError // onError callback
        );
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
    console.debug(`[UX] ⏯️ handleToggleRecording (isRecording=${isRecording})`);
    if (isRecording) {
      handleStopRecording();
    } else {
      handleStartRecording();
    }
  };

  const handleModeChange = (newMode: "hybrid" | "immersive") => {
    setPracticeMode(newMode);

    if (newMode === "immersive") {
      // Verifica se a última mensagem é de áudio antes de tocar
      const lastMessage = messages[messages.length - 1];

      if (
        lastMessage.role === "assistant" &&
        lastMessage.content &&
        typeof lastMessage.content === "object" &&
        "file" in lastMessage.content &&
        (lastMessage.content.file as any)?.url
      ) {
        const audioUrl = (lastMessage.content as any).file.url;
        if (audioUrl && typeof audioUrl === "string") {
          playAudio(audioUrl);
        }
      }
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex justify-center mb-6">
        <fieldset
          className="bg-gray-800 p-1 rounded-full flex items-center space-x-1 border border-gray-700"
          disabled={isLoading || isRecording}
          aria-label="Practice Mode"
        >
          <button
            onClick={() => handleModeChange("hybrid")}
            className={`relative flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-full transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 focus-visible:ring-white disabled:opacity-50 ${
              practiceMode === "hybrid"
                ? "bg-indigo-600 text-white"
                : "text-gray-400 hover:bg-gray-700"
            }`}
            aria-pressed={practiceMode === "hybrid"}
          >
            <MessageSquareTextIcon className="w-5 h-5" />
            Hybrid
          </button>
          <button
            onClick={() => handleModeChange("immersive")}
            className={`relative flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-full transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900 focus-visible:ring-white disabled:opacity-50 ${
              practiceMode === "immersive"
                ? "bg-indigo-600 text-white"
                : "text-gray-400 hover:bg-gray-700"
            }`}
            aria-pressed={practiceMode === "immersive"}
          >
            <HeadphonesIcon className="w-5 h-5" />
            Immersive
          </button>
        </fieldset>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden pr-4">
        <Chatbot
          messages={messages}
          isLoading={isLoading}
          practiceMode={practiceMode}
          botIsSpeaking={botSpeaking}
        />
      </div>

      <div className="mt-6">
        <div className="flex flex-col items-center justify-center">
          <button
            onClick={handleToggleRecording}
            disabled={isLoading}
            className={`flex items-center justify-center w-20 h-20 rounded-full transition-all duration-300 ease-in-out focus:outline-none focus:ring-4 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-wait
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
