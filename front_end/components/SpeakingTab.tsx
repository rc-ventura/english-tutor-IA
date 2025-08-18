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
  const ENABLE_ESCALATION = (import.meta as any).env?.VITE_ENABLE_ESCALATION === "true";
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
  // Track last bot audio URL to include in escalation payload if assistant message isn't populated yet
  const lastAudioUrlRef = useRef<string | null>(null);

  // Escalation UI state
  const [escalatedIndices, setEscalatedIndices] = useState<number[]>([]);
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [pendingEscalationIdx, setPendingEscalationIdx] = useState<number | null>(
    null
  );
  const [escReasons, setEscReasons] = useState<string[]>([]);
  const [escNote, setEscNote] = useState("");

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

  // ---------- Escalation helpers ----------
  const handleEscalateRequest = (idx: number) => {
    if (!ENABLE_ESCALATION) return;
    setPendingEscalationIdx(idx);
    setShowEscalateModal(true);
  };

  const toggleReason = (reason: string) => {
    setEscReasons((prev) =>
      prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]
    );
  };

  const submitEscalation = async () => {
    if (pendingEscalationIdx == null) return;
    const idx = pendingEscalationIdx;
    const msg = messages[idx];
    const userLastText =
      typeof msg.content === "string" ? msg.content : (msg as any).text_for_llm || "";
    const practiceModeLabel = practiceMode === "hybrid" ? "Hybrid" : "Immersive";
    const assistantMsg = messages.slice(idx + 1).find((m) => m.role === "assistant");
    const assistantText = assistantMsg
      ? typeof assistantMsg.content === "string"
        ? assistantMsg.content
        : (assistantMsg as any).text_for_llm || null
      : null;
    let audioUrl: string | null = null;
    if (
      assistantMsg &&
      assistantMsg.content &&
      typeof assistantMsg.content === "object" &&
      "file" in (assistantMsg.content as any)
    ) {
      audioUrl = ((assistantMsg.content as any).file as any)?.url ?? null;
    }
    // Fallback to last played audio URL if assistant message hasn't populated file.url yet
    if (!audioUrl && lastAudioUrlRef.current) {
      audioUrl = lastAudioUrlRef.current;
    }

    try {
      await api.createEscalation({
        source: "speaking",
        practiceMode: practiceModeLabel,
        level: englishLevel,
        messageIndex: idx,
        reasons: escReasons,
        userNote: escNote || undefined,
        assistantText: assistantText || undefined,
        userLastText,
        historyPreview: messages,
        audioUrl,
      });
      setEscalatedIndices((prev) => Array.from(new Set([...prev, idx])));
    } catch (e) {
      console.error("Failed to create escalation", e);
      alert("Failed to create escalation");
    } finally {
      setShowEscalateModal(false);
      setPendingEscalationIdx(null);
      setEscReasons([]);
      setEscNote("");
    }
  };

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
    // keep latest audio URL for escalation fallback
    lastAudioUrlRef.current = url;
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
      setTimeout(() => {
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
          enableEscalation={ENABLE_ESCALATION}
          onEscalateRequest={handleEscalateRequest}
          escalatedIndices={escalatedIndices}
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

      {/* Escalation Modal */}
      {ENABLE_ESCALATION && showEscalateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-gray-800 text-gray-100 shadow-2xl border border-white/10">
            <div className="px-5 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold">Escalate conversation</h3>
              <p className="text-sm text-gray-400">
                Select reasons and add an optional note for human review.
              </p>
            </div>
            <div className="px-5 py-4 space-y-3">
              <div className="space-y-2">
                {[
                  "Pronunciation issue",
                  "Inappropriate content",
                  "Model error",
                  "Other",
                ].map((r) => (
                  <label key={r} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={escReasons.includes(r)}
                      onChange={() => toggleReason(r)}
                      className="accent-indigo-500"
                    />
                    <span>{r}</span>
                  </label>
                ))}
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">
                  Notes (optional)
                </label>
                <textarea
                  className="w-full rounded-md bg-gray-900/60 border border-white/10 p-2 text-gray-100"
                  rows={3}
                  value={escNote}
                  onChange={(e) => setEscNote(e.target.value)}
                  placeholder="Add any relevant context..."
                />
              </div>
            </div>
            <div className="px-5 py-4 border-t border-white/10 flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowEscalateModal(false);
                  setPendingEscalationIdx(null);
                }}
                className="px-3 py-2 rounded-md bg-gray-700 hover:bg-gray-600 transition"
              >
                Cancel
              </button>
              <button
                onClick={submitEscalation}
                className="px-3 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white transition"
                disabled={pendingEscalationIdx == null || escReasons.length === 0}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SpeakingTab;
