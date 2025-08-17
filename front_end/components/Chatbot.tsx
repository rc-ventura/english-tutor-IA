import React, { useRef, useEffect, useState } from "react";
import { ChatMessage } from "../types";
import { UserIcon, BrainCircuitIcon, CopyIcon } from "./icons/Icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// --- Local Type Definitions for Clarity ---
interface GradioFile {
  url?: string;
}

interface GradioMessageContent {
  file?: GradioFile;
}

// --- Component Props ---
interface ChatbotProps {
  messages: ChatMessage[];
  isLoading: boolean;
  practiceMode: "hybrid" | "immersive";
  botIsSpeaking?: boolean;
}

interface ChatMessageBubbleProps {
  message: ChatMessage;
  practiceMode: "hybrid" | "immersive";
  isLastMessage: boolean;
  botIsSpeaking?: boolean;
}

// --- Helper Functions ---
const isGradioAudioContent = (
  content: any
): content is GradioMessageContent => {
  return (
    typeof content === "object" &&
    content !== null &&
    "file" in content &&
    typeof content.file === "object" &&
    content.file !== null &&
    "url" in content.file
  );
};

// --- Main Components ---

const AudioPlayer: React.FC<{ src: string }> = ({ src }) => {
  // Removed the useEffect for autoplay. This component now only renders the controls.
  // The autoplay is handled by SpeakingTab.tsx using the Web Audio API.
  return (
    <audio controls src={src} className="w-full" style={{ minWidth: 200 }} />
  );
};

const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({
  message,
  practiceMode,
  isLastMessage,
  botIsSpeaking,
}) => {
  const isUser = message.role === "user";

  const handleCopy = () => {
    const textToCopy =
      typeof message.content === "string"
        ? message.content
        : message.text_for_llm;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
    }
  };

  // // Normalize assistant text to improve readability when the model returns a single long paragraph
  // function normalizeAssistantText(text: string): string {
  //   if (!text) return "";
  //   let t = text;
  //   // Insert blank lines before common section headers (EN/PT): Day(s) X or X–Y
  //   t = t.replace(
  //     /\s+(?=(?:Days?|Day|Dias?|Dia)\s\d+(?:[–-]\d+)?\s*:)/g,
  //     "\n\n"
  //   );
  //   // Ensure bullet items render as a list when the dash appears mid-paragraph
  //   t = t.replace(/\s-\s/g, "\n- ");
  //   // Collapse 3+ newlines to 2 for clean Markdown
  //   t = t.replace(/\n{3,}/g, "\n\n");
  //   return t.trim();
  // }

  const renderContent = () => {
    if (practiceMode === "immersive") {
      // --- Immersive Mode Rendering ---
      if (isGradioAudioContent(message.content) && message.content.file?.url) {
        return <AudioPlayer src={message.content.file.url} />;
      } else if (typeof message.content === "string") {
        return (
          <div
            className={message.content.includes("Error") ? "text-red-400" : ""}
          >
            {message.content}
          </div>
        );
      } else {
        // Inline modern placeholder inside the bubble
        return (
          <div className="flex items-center gap-2 text-gray-300">
            <div className="eq-bars" aria-hidden>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>
              {isUser
                ? "Transcrevendo sua fala..."
                : botIsSpeaking
                ? "Falando..."
                : "Gerando resposta de voz..."}
            </span>
          </div>
        );
      }
    } else {
      // --- Hybrid Mode Rendering ---
      // Trata mensagens de áudio primeiro
      if (isGradioAudioContent(message.content) && message.content.file?.url) {
        return (
          <div className="flex items-center gap-2 text-gray-400">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.536 8.464a5 5 0 010 7.072M12 6a7.975 7.975 0 014.242 1.757"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <span>Mensagem de áudio</span>
          </div>
        );
      }

      // Se ainda não há conteúdo de texto (pendente), mostrar placeholder moderno
      if (typeof message.content !== "string" && !message.text_for_llm) {
        return (
          <div className="flex items-center gap-2 text-gray-300">
            <div className="eq-bars" aria-hidden>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>{isUser ? "Enviando..." : botIsSpeaking ? "Falando..." : "Aguardando..."}</span>
          </div>
        );
      }

      // Mantém o tratamento padrão para mensagens de texto
      const text =
        typeof message.content === "string"
          ? message.content
          : message.text_for_llm || "";
      //const normalized = normalizeAssistantText(text);
      return (
        <div className="max-w-3xl whitespace-pre-wrap break-words leading-relaxed chat-markdown">
          <ReactMarkdown skipHtml remarkPlugins={[remarkGfm]}>
            {text}
          </ReactMarkdown>
        </div>
      );
    }
  };

  return (
    <div
      className={`flex items-start gap-3 my-4 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
          <BrainCircuitIcon className="w-6 h-6 text-white" />
        </div>
      )}
      <div
        className={`relative px-4 py-3 rounded-2xl max-w-[80%] md:max-w-[70%] lg:max-w-[60%] ${
          isUser
            ? "bg-indigo-500 text-white rounded-br-none"
            : "bg-gray-700 text-gray-200 rounded-bl-none"
        }`}
      >
        {renderContent()}
        {!isUser && practiceMode === "hybrid" && (
          <button
            onClick={handleCopy}
            className="absolute top-1 right-1 p-1 text-gray-400 hover:text-white transition-colors"
            aria-label="Copy message"
          >
            <CopyIcon className="w-4 h-4" />
          </button>
        )}
      </div>
      {isUser && (
        <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0">
          <UserIcon className="w-6 h-6 text-white" />
        </div>
      )}
    </div>
  );
};

// Compact typing bubble used for global loading state
const TypingBubble: React.FC<{
  variant?: "thinking" | "audio" | "transcribing";
}> = ({ variant = "thinking" }) => {
  const label =
    variant === "audio"
      ? "Gerando resposta de voz..."
      : variant === "transcribing"
      ? "Transcrevendo sua fala..."
      : "Gerando resposta...";
  return (
    <div className="flex justify-start items-center gap-3 my-4">
      <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
        <BrainCircuitIcon className="w-6 h-6 text-white" />
      </div>
      <div className="px-4 py-3 rounded-2xl bg-gray-700 text-gray-200">
        <div className="flex items-center gap-3">
          <div className="eq-bars" aria-hidden>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span className="text-sm text-gray-300">{label}</span>
        </div>
      </div>
    </div>
  );
};

const Chatbot: React.FC<ChatbotProps> = ({
  messages,
  isLoading,
  practiceMode,
  botIsSpeaking,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [nearBottom, setNearBottom] = useState(true);

  // Detect whether user is near the bottom to avoid fighting manual scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const distance = el.scrollHeight - (el.scrollTop + el.clientHeight);
      setNearBottom(distance < 64); // 64px threshold
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-scroll only if the user is already near the bottom
  useEffect(() => {
    if (nearBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isLoading, nearBottom]);

  return (
    <div
      ref={scrollRef}
      className="relative h-full overflow-y-auto p-4 pr-6 chat-scrollbar"
    >
      <div className="max-w-4xl mx-auto">
        {messages.map((message, index) => (
          <ChatMessageBubble
            key={index}
            message={message}
            practiceMode={practiceMode}
            isLastMessage={index === messages.length - 1}
            botIsSpeaking={botIsSpeaking}
          />
        ))}
        {(() => {
          const hasPendingAssistant = messages.some(
            (m) =>
              m.role === "assistant" &&
              (m.content == null ||
                (typeof m.content !== "string" && !(m as any).text_for_llm))
          );
          return isLoading && !hasPendingAssistant ? (
            <TypingBubble
              variant={practiceMode === "immersive" ? "audio" : "thinking"}
            />
          ) : null;
        })()}
        {/* Anchor at the bottom for smooth auto-scroll */}
        <div ref={bottomRef} />

        {/* Jump to latest button when user scrolled up */}
        {!nearBottom && (
          <button
            onClick={() =>
              bottomRef.current?.scrollIntoView({
                behavior: "smooth",
                block: "end",
              })
            }
            aria-label="Jump to latest"
            className="absolute bottom-4 right-4 px-3.5 py-2.5 rounded-full bg-emerald-500 text-white shadow-xl ring-2 ring-white/40 hover:bg-emerald-400 focus:outline-none focus-visible:ring-4 focus-visible:ring-emerald-300 transition"
          >
            Jump to latest
          </button>
        )}
      </div>
    </div>
  );
};

export default Chatbot;
