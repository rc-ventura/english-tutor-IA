import React, { useRef, useEffect } from "react";
import { ChatMessage } from "../types";
import { UserIcon, BrainCircuitIcon, CopyIcon } from "./icons/Icons";
import ReactMarkdown from "react-markdown";

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
}

interface ChatMessageBubbleProps {
  message: ChatMessage;
  practiceMode: "hybrid" | "immersive";
  isLastMessage: boolean;
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
        // Placeholder for user or assistant while processing
        const placeholder = isUser
          ? "⏳ Processando sua fala..."
          : "⏳ Gerando resposta...";
        return <div style={{ color: "#aaa" }}>{placeholder}</div>;
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

      // Mantém o tratamento padrão para mensagens de texto
      const text =
        typeof message.content === "string"
          ? message.content
          : message.text_for_llm || "";
      return (
        <div className="max-w-3xl whitespace-normal break-words chat-markdown">
          <ReactMarkdown skipHtml>
            {text.replace(/\n{3,}/g, "\n\n")}
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

const Chatbot: React.FC<ChatbotProps> = ({
  messages,
  isLoading,
  practiceMode,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 pr-6">
      <div className="max-w-4xl mx-auto">
        {messages.map((message, index) => (
          <ChatMessageBubble
            key={index}
            message={message}
            practiceMode={practiceMode}
            isLastMessage={index === messages.length - 1}
          />
        ))}
        {isLoading && (
          <div className="flex justify-start items-center gap-3 my-4">
            <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
              <BrainCircuitIcon className="w-6 h-6 text-white" />
            </div>
            <div className="px-4 py-3 rounded-2xl bg-gray-700 text-gray-200">
              <div className="flex items-center space-x-2">
                <div className="dot-flashing"></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chatbot;
