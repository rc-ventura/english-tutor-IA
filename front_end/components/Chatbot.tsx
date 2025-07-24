
import React, { useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import { UserIcon, BrainCircuitIcon, CopyIcon } from './icons/Icons';

interface ChatbotProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

const ChatMessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
    const isUser = message.role === 'user';
    const handleCopy = () => {
        if(typeof message.content === 'string') {
            navigator.clipboard.writeText(message.content);
        }
    }
  return (
    <div className={`flex items-start gap-3 my-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
          <BrainCircuitIcon className="w-6 h-6 text-white" />
        </div>
      )}
      <div
        className={`relative max-w-lg px-4 py-3 rounded-xl shadow ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-none'
            : 'bg-gray-700 text-gray-200 rounded-bl-none'
        }`}
      >
        <div className="prose prose-sm prose-invert max-w-none prose-p:my-2">{message.content}</div>
         {!isUser && typeof message.content === 'string' && (
            <button onClick={handleCopy} className="absolute top-2 right-2 p-1 text-gray-400 hover:text-white transition-colors">
                <CopyIcon className="w-4 h-4"/>
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

const LoadingIndicator: React.FC = () => (
    <div className="flex items-start gap-3 my-4 justify-start">
        <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
          <BrainCircuitIcon className="w-6 h-6 text-white" />
        </div>
        <div className="bg-gray-700 text-gray-200 rounded-xl rounded-bl-none px-4 py-3 shadow">
            <div className="flex items-center justify-center space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0s'}}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
            </div>
        </div>
    </div>
)

const Chatbot: React.FC<ChatbotProps> = ({ messages, isLoading }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto">
      {messages.map((msg, index) => (
        <ChatMessageBubble key={index} message={msg} />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  );
};

export default Chatbot;
