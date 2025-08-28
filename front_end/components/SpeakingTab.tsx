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
import type { Badge, BadgeTriple } from "./Chatbot";

// Local types and REST helper for Speaking Metrics (avoid coupling to api.ts for now)
interface SpeakingMetrics {
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

const API_BASE_URL: string =
  ((import.meta as any).env?.VITE_API_BASE_URL as string) ||
  ((import.meta as any).env?.VITE_GRADIO_BASE_URL as string)?.replace(
    /\/?gradio\/?$/,
    ""
  ) ||
  "";

const postSpeakingMetrics = async (payload: {
  userAudioBase64?: string;
  userAudioUrl?: string;
  transcript?: string;
  level?: string;
}): Promise<SpeakingMetrics> => {
  const res = await fetch(`${API_BASE_URL}/api/speaking/metrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as SpeakingMetrics;
};

interface SpeakingTabProps {
  englishLevel: EnglishLevel;
}

const SpeakingTab: React.FC<SpeakingTabProps> = ({ englishLevel }) => {
  const ENABLE_ESCALATION =
    (import.meta as any).env?.VITE_ENABLE_ESCALATION === "true";
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
  const [speakingMetrics, setSpeakingMetrics] =
    useState<SpeakingMetrics | null>(null);
  const [userBadgesByIndex, setUserBadgesByIndex] = useState<
    Record<number, BadgeTriple>
  >({});
  const [bannerVisible, setBannerVisible] = useState<boolean>(true);
  const bannerTimerRef = useRef<number | null>(null);
  const AUTO_HIDE_MS = 12000; // generous timeout (12s)

  const audioPlayerRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioPlayedRef = useRef<boolean>(false);
  const awaitingAssistantRef = useRef<boolean>(false);
  const [botSpeaking, setBotSpeaking] = useState<boolean>(false);
  const streamingJobRef = useRef<(() => void) | null>(null);
  // Stream watchdog to auto-cancel lingering jobs
  const streamWatchdogTimerRef = useRef<number | null>(null);
  const lastActivityRef = useRef<number>(0);
  const STEP_TIMEOUT_SEC: number = Number(
    ((import.meta as any).env?.VITE_SPEAKING_STEP_TIMEOUT_SEC as string) ?? 25
  );
  // Track chosen recording MIME type per session
  const recordingMimeRef = useRef<string>("");
  // Track last bot audio URL to include in escalation payload if assistant message isn't populated yet
  const lastAudioUrlRef = useRef<string | null>(null);
  // Track last user audio (as data URL) to recompute metrics when transcript arrives
  const lastUserAudioDataUrlRef = useRef<string | null>(null);
  const transcriptMetricsSentRef = useRef<boolean>(false);
  const lastUserMsgIndexRef = useRef<number | null>(null);

  // Escalation UI state
  const [escalatedIndices, setEscalatedIndices] = useState<number[]>([]);
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [pendingEscalationIdx, setPendingEscalationIdx] = useState<
    number | null
  >(null);
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
      // Cancel any in-flight streaming job
      if (streamingJobRef.current) streamingJobRef.current();
      // Clear watchdog timer
      if (streamWatchdogTimerRef.current) {
        window.clearTimeout(streamWatchdogTimerRef.current);
        streamWatchdogTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    return () => {
      if (bannerTimerRef.current) window.clearTimeout(bannerTimerRef.current);
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
      prev.includes(reason)
        ? prev.filter((r) => r !== reason)
        : [...prev, reason]
    );
  };

  const submitEscalation = async () => {
    if (pendingEscalationIdx == null) return;
    const idx = pendingEscalationIdx;
    const msg = messages[idx];
    const userLastText =
      typeof msg.content === "string"
        ? msg.content
        : (msg as any).text_for_llm || "";
    const practiceModeLabel =
      practiceMode === "hybrid" ? "Hybrid" : "Immersive";
    const assistantMsg = messages
      .slice(idx + 1)
      .find((m) => m.role === "assistant");
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

  // Pick a supported audio MIME type for MediaRecorder depending on the browser
  const pickRecordingMime = (): string => {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/aac",
      "audio/mpeg", // fallback
    ];
    const isSupported = (t: string) =>
      typeof MediaRecorder !== "undefined" &&
      typeof (MediaRecorder as any).isTypeSupported === "function" &&
      (MediaRecorder as any).isTypeSupported(t);
    for (const t of candidates) {
      try {
        if (isSupported(t)) return t;
      } catch {}
    }
    return ""; // let browser choose default
  };

  // Plays audio from a URL using the Web Audio API
  const playAudio = async (url: string) => {
    if (!audioContextRef.current) return;
    console.log("🔊 Attempting to play audio from URL:", url);
    // Guard: avoid re-playing the same URL
    if (lastAudioUrlRef.current === url) {
      console.info("🔊 Skipping playback: same URL as last played", url);
      return;
    }
    // keep latest audio URL for escalation fallback and replay guard
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
    lastAudioUrlRef.current = null; // allow new URL to play in this turn
    transcriptMetricsSentRef.current = false; // reset for a fresh metrics-with-transcript call
    setSpeakingMetrics(null); // clear previous banner
    // No need to clear userBadgesByIndex; keep history per turn
    console.info(
      `[UX] 🎙️ handleStartRecording: start (mode=${practiceMode}, level=${englishLevel})`
    );

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.debug("[UX] 🎤 getUserMedia acquired");
      setIsRecording(true);
      audioChunksRef.current = [];
      const chosen = pickRecordingMime();
      recordingMimeRef.current = chosen;
      console.debug("[UX] 🎛️ MediaRecorder mimeType:", chosen || "(browser default)");
      const opts = chosen ? { mimeType: chosen } : undefined;
      const recorder = new MediaRecorder(stream, opts as any);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.info("[UX] ⏹️ recorder.onstop");
        try {
          // Stop mic tracks to release resources
          stream.getTracks().forEach((t) => t.stop());
        } catch {}
        const inferredType =
          audioChunksRef.current[0]?.type || recordingMimeRef.current || "";
        const audioBlob = new Blob(audioChunksRef.current, {
          type: inferredType,
        });
        console.debug(
          `[UX] 💾 audioBlob size=${audioBlob.size}B, chunks=${audioChunksRef.current.length}`
        );
        if (!audioBlob.size) {
          console.warn("[UX] ⚠️ Empty recording blob; aborting upload and resetting UI.");
          setIsRecording(false);
          setIsLoading(false);
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "I couldn't hear anything. Please try again." },
          ]);
          return;
        }
        const userPlaceholder: ChatMessage = { role: "user", content: null };
        const botPlaceholder: ChatMessage = {
          role: "assistant",
          content: null,
        };
        // Show both bubbles immediately with loading placeholders; capture user index for badges
        let userIndexAssigned: number | null = null;
        setMessages((prev) => {
          const idx = prev.length; // user message will be appended at this index
          lastUserMsgIndexRef.current = idx;
          userIndexAssigned = idx;
          return [...prev, userPlaceholder, botPlaceholder];
        });
        awaitingAssistantRef.current = true;

        const handleError = (error: Error) => {
          console.error("Streaming Error:", error);
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "Sorry, an error occurred." },
          ]);
          setIsLoading(false);
          // On error, clear watchdog
          if (streamWatchdogTimerRef.current) {
            window.clearTimeout(streamWatchdogTimerRef.current);
            streamWatchdogTimerRef.current = null;
          }
        };

        const armWatchdog = () => {
          if (streamWatchdogTimerRef.current) {
            window.clearTimeout(streamWatchdogTimerRef.current);
          }
          streamWatchdogTimerRef.current = window.setTimeout(() => {
            console.warn(
              `[UX] ⏱️ Stream watchdog fired after ${STEP_TIMEOUT_SEC}s without activity; cancelling job.`
            );
            if (streamingJobRef.current) streamingJobRef.current();
            setIsLoading(false);
            awaitingAssistantRef.current = false;
          }, STEP_TIMEOUT_SEC * 1000);
        };

        // Start the streaming job
        console.info(
          `[UX] 🚀 start streaming (mode=${practiceMode}, level=${englishLevel})`
        );
        lastActivityRef.current = Date.now();
        armWatchdog();
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
            lastActivityRef.current = Date.now();
            armWatchdog();
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
              (last.content == null ||
                (typeof last.content !== "string" &&
                  !(last as any).text_for_llm));
            const hasAssistantText = merged.some(
              (m) =>
                m.role === "assistant" &&
                (typeof m.content === "string" || (m as any).text_for_llm)
            );
            const needsAssistantPlaceholder =
              awaitingAssistantRef.current ||
              !!audioUrl ||
              isLoading ||
              botSpeaking;
            if (needsAssistantPlaceholder && !lastIsAssistantPending) {
              merged = [...merged, { role: "assistant", content: null }];
            }
            // Stop awaiting only once assistant textual content appears
            awaitingAssistantRef.current = !hasAssistantText;

            // If transcription text is present, forward it to speaking metrics once
            try {
              if (
                !transcriptMetricsSentRef.current &&
                lastUserAudioDataUrlRef.current
              ) {
                const lastUser = [...serverMessages]
                  .reverse()
                  .find(
                    (m) =>
                      m.role === "user" &&
                      typeof m.content === "string" &&
                      (m.content as string).trim().length > 0
                  ) as ChatMessage | undefined;
                if (lastUser && typeof lastUser.content === "string") {
                  transcriptMetricsSentRef.current = true;
                  postSpeakingMetrics({
                    userAudioBase64: lastUserAudioDataUrlRef.current,
                    transcript: lastUser.content,
                    level: englishLevel,
                  })
                    .then((m) => {
                      showBanner(m);
                      const badges = buildBadgesFromMetrics(m, englishLevel);
                      const idx = lastUserMsgIndexRef.current;
                      if (typeof idx === "number") {
                        setUserBadgesByIndex((prev) => ({
                          ...prev,
                          [idx]: badges,
                        }));
                      }
                    })
                    .catch((e) =>
                      console.warn(
                        "/api/speaking/metrics (with transcript) failed",
                        e
                      )
                    );
                }
              }
            } catch (e) {
              console.warn("metrics-with-transcript block failed:", e);
            }

            setMessages(merged);
            setIsLoading(false);
            console.debug("[UX] ✅ onData applied to UI (merged)");
          },
          handleError, // onError callback
          () => {
            // onComplete: normal end of stream
            if (streamWatchdogTimerRef.current) {
              window.clearTimeout(streamWatchdogTimerRef.current);
              streamWatchdogTimerRef.current = null;
            }
          }
        );
        // Post initial speaking metrics (without transcript) and attach badges to this user turn
        try {
          const dataUrl = await blobToDataURL(audioBlob);
          lastUserAudioDataUrlRef.current = dataUrl;
          postSpeakingMetrics({ userAudioBase64: dataUrl, level: englishLevel })
            .then((m) => {
              showBanner(m);
              const badges = buildBadgesFromMetrics(m, englishLevel);
              const idx = userIndexAssigned ?? lastUserMsgIndexRef.current;
              if (typeof idx === "number") {
                setUserBadgesByIndex((prev) => ({ ...prev, [idx]: badges }));
              }
            })
            .catch((e) =>
              console.warn("/api/speaking/metrics (no transcript) failed", e)
            );
        } catch (e) {
          console.warn("blobToDataURL failed:", e);
        }
      };
      // Use a small timeslice to get periodic data and avoid zero-sized recordings on quick stops
      recorder.start(250);
    } catch (err) {
      console.error("Failed to get microphone:", err);
      alert(
        "Could not access the microphone. Please check your browser permissions."
      );
    }
  };

  const blobToDataURL = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
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
          if (lastAudioUrlRef.current === audioUrl) {
            console.debug("[UX] 🔁 Skipping replay on mode toggle (same URL)");
          } else {
            playAudio(audioUrl);
          }
        }
      }
    }
  };

  // Helper: show banner now and auto-hide after timeout
  function showBanner(m: SpeakingMetrics) {
    setSpeakingMetrics(m);
    setBannerVisible(true);
    if (bannerTimerRef.current) window.clearTimeout(bannerTimerRef.current);
    bannerTimerRef.current = window.setTimeout(() => {
      setBannerVisible(false);
    }, AUTO_HIDE_MS);
  }

  // ---------------- Badge + Banner helpers ----------------
  function levelWpmRange(level: EnglishLevel | string | null | undefined): {
    min: number;
    max: number;
  } {
    const L = String(level ?? "B1").toUpperCase();
    const map: Record<string, { min: number; max: number }> = {
      A1: { min: 80, max: 140 },
      A2: { min: 100, max: 160 },
      B1: { min: 110, max: 180 },
      B2: { min: 120, max: 200 },
      C1: { min: 130, max: 210 },
      C2: { min: 140, max: 220 },
    };
    return map[L] ?? map.B1;
  }

  function buildBadgesFromMetrics(
    m: SpeakingMetrics,
    level: EnglishLevel | string
  ): BadgeTriple {
    // Speed badge
    const { min, max } = levelWpmRange(level);
    const tol = 15;
    let speed: Badge;
    if (typeof m.wpm !== "number" || !isFinite(m.wpm)) {
      speed = {
        label: "—",
        tone: "warn",
        tooltip: "No transcript yet to compute WPM",
      };
    } else if (m.wpm < min - tol) {
      speed = {
        label: "Slow",
        tone: "warn",
        tooltip: `WPM ${m.wpm.toFixed(0)} (below ${min})`,
      };
    } else if (m.wpm > max + tol) {
      speed = {
        label: "Fast",
        tone: "warn",
        tooltip: `WPM ${m.wpm.toFixed(0)} (above ${max})`,
      };
    } else {
      speed = {
        label: "Good",
        tone: "good",
        tooltip: `WPM ${m.wpm.toFixed(0)} in target range (${min}-${max})`,
      };
    }

    // Clarity badge (pauses + clipping)
    let clarity: Badge;
    if (m.clipping_ratio > 0.02) {
      clarity = {
        label: "Clipping",
        tone: "bad",
        tooltip: `Clipping ${(m.clipping_ratio * 100).toFixed(2)}%`,
      };
    } else if (m.pause_ratio > 0.6) {
      clarity = {
        label: "Pauses",
        tone: "warn",
        tooltip: `Pause ${Math.round(m.pause_ratio * 100)}% (high)`,
      };
    } else {
      clarity = {
        label: "Clear",
        tone: "good",
        tooltip: `Speech ${Math.round(m.speech_ratio * 100)}%`,
      };
    }

    // Volume badge (rough heuristics on RMS dBFS)
    const rms = m.rms_dbfs;
    let volume: Badge;
    if (rms <= -40) {
      volume = {
        label: "Very Low",
        tone: "bad",
        tooltip: `RMS ${rms.toFixed(1)} dBFS`,
      };
    } else if (rms <= -28) {
      volume = {
        label: "Low",
        tone: "warn",
        tooltip: `RMS ${rms.toFixed(1)} dBFS`,
      };
    } else if (rms >= -6) {
      volume = {
        label: "Too Loud",
        tone: "bad",
        tooltip: `RMS ${rms.toFixed(1)} dBFS`,
      };
    } else if (rms >= -10) {
      volume = {
        label: "Loud",
        tone: "warn",
        tooltip: `RMS ${rms.toFixed(1)} dBFS`,
      };
    } else {
      volume = {
        label: "Good",
        tone: "good",
        tooltip: `RMS ${rms.toFixed(1)} dBFS`,
      };
    }

    return { speed, clarity, volume };
  }

  const Pill: React.FC<{ badge: Badge; name: string }> = ({ badge, name }) => (
    <span
      title={badge.tooltip || name}
      className={`px-2 py-1 rounded-full text-xs border shadow-sm ${
        badge.tone === "good"
          ? "bg-emerald-500/15 text-emerald-200 border-emerald-400/30"
          : badge.tone === "warn"
          ? "bg-amber-500/15 text-amber-200 border-amber-400/30"
          : "bg-rose-500/15 text-rose-200 border-rose-400/30"
      }`}
    >
      {name}: {badge.label}
    </span>
  );

  const SpeakingStickyBanner: React.FC<{
    metrics: SpeakingMetrics;
    level: EnglishLevel;
    onClose?: () => void;
  }> = ({ metrics, level, onClose }) => {
    const badges = buildBadgesFromMetrics(metrics, level);
    const friendly = (() => {
      const tips: string[] = [];
      if (badges.speed.tone !== "good") {
        tips.push(
          badges.speed.label === "Slow"
            ? "Try speaking a bit faster."
            : badges.speed.label === "Fast"
            ? "Try slowing down a little."
            : "Waiting for transcript to adjust speed."
        );
      }
      if (badges.clarity.tone !== "good") {
        tips.push(
          badges.clarity.label === "Clipping"
            ? "Reduce mic gain or move slightly away."
            : "Reduce long pauses for clearer speech."
        );
      }
      if (badges.volume.tone !== "good") {
        tips.push(
          badges.volume.label.includes("Low")
            ? "Increase input volume or move closer to the mic."
            : "Lower input volume to avoid distortion."
        );
      }
      return tips.length ? tips.join(" ") : "Great pace, clarity, and volume!";
    })();

    const styleBase = metrics.suggested_escalation
      ? "border-amber-400 bg-amber-500/10 text-amber-200"
      : "border-gray-700 bg-gray-800 text-gray-200";

    return (
      <div className={`rounded-lg border px-3 py-2 ${styleBase}`}>
        <div className="flex flex-wrap items-center gap-2">
          <Pill name="Speed" badge={badges.speed} />
          <Pill name="Clarity" badge={badges.clarity} />
          <Pill name="Volume" badge={badges.volume} />
          <button
            type="button"
            aria-label="Close speaking tips"
            onClick={onClose}
            className="ml-auto px-2 py-0.5 text-xs rounded-md bg-gray-700/60 hover:bg-gray-600 transition"
          >
            Close
          </button>
        </div>
        <div className="mt-1 text-xs text-gray-300">{friendly}</div>
      </div>
    );
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
          userBadgesByIndex={userBadgesByIndex}
          stickyHeader={
            bannerVisible && speakingMetrics ? (
              <SpeakingStickyBanner
                metrics={speakingMetrics}
                level={englishLevel}
                onClose={() => setBannerVisible(false)}
              />
            ) : null
          }
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
                disabled={
                  pendingEscalationIdx == null || escReasons.length === 0
                }
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
