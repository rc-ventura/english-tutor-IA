import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, EnglishLevel, WritingType } from '../types';
import { WRITING_TYPES } from '../constants';
import Chatbot from './Chatbot';
import { PlayIcon, SparklesIcon } from './icons/Icons';
import * as api from '../services/api';

interface WritingTabProps {
  englishLevel: EnglishLevel;
}

const WritingTab: React.FC<WritingTabProps> = ({ englishLevel }) => {
  const [writingType, setWritingType] = useState<WritingType>('Daily Journal');
  const [essayText, setEssayText] = useState<string>('');
  const [feedbackMessages, setFeedbackMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const audioPlayerRef = useRef<HTMLAudioElement>(null);
  const [hasEvaluated, setHasEvaluated] = useState<boolean>(false);


  useEffect(() => {
    const audioEl = audioPlayerRef.current;
    return () => {
      if (audioEl) {
        audioEl.pause();
        audioEl.src = '';
      }
    };
  }, []);

  // Streaming: mantém referência para cancelar caso o usuário clique várias vezes
  const topicJobRef = useRef<null | (() => void)>(null);

  const handleGenerateTopic = () => {
    setIsLoading(true);
    setFeedbackMessages([]);
    setHasEvaluated(false);
    // Cancela streaming anterior, se houver
    if (topicJobRef.current) topicJobRef.current();
    let lastMessages: ChatMessage[] = [];
    topicJobRef.current = api.generateRandomTopicStream(
      englishLevel,
      writingType,
      (messages) => {
        lastMessages = messages;
        setFeedbackMessages(messages);
      },
      (error) => {
        console.error("Failed to generate topic (stream):", error);
        setFeedbackMessages([{ role: 'assistant', content: 'Sorry, I could not generate a topic right now.' }]);
        setIsLoading(false);
      }
    );
    // Finaliza loading quando acabar o stream
    // Como não temos callback "done" do Gradio, faz um pequeno delay após última mensagem
    setTimeout(() => {
      setIsLoading(false);
    }, 800);
  };


  const handleEvaluate = () => {
    if (!essayText.trim()) return;
    setIsLoading(true);
    setHasEvaluated(false);

    let lastTimeout: NodeJS.Timeout | null = null;
    let lastMessages: ChatMessage[] = [];

    const cancel = api.processInputStream(
      essayText,
      writingType,
      englishLevel,
      feedbackMessages,
      (messages) => {
        lastMessages = messages;
        setFeedbackMessages(messages);
        // Reinicia o timeout a cada chunk recebido
        if (lastTimeout) clearTimeout(lastTimeout);
        lastTimeout = setTimeout(() => {
          setIsLoading(false);
          setHasEvaluated(true);
        }, 800); // considera stream finalizado após 800ms sem novos dados
      },
      (error) => {
        setIsLoading(false);
        setFeedbackMessages(prev => [...prev, { role: 'assistant', content: 'An error occurred during evaluation.' }]);
      }
    );
    // Opcional: retornar cancel para permitir interrupção futura
    return cancel;
  };


  const handlePlayAudio = async () => {
    try {
        const audioUrl = await api.playLastAudio();
        if (audioUrl && audioPlayerRef.current) {
            audioPlayerRef.current.src = audioUrl;
            audioPlayerRef.current.play().catch(e => console.error("Audio playback failed", e));
        } else {
            console.warn("No audio URL received from the backend.");
            alert("No feedback audio is available to play.");
        }
    } catch (error) {
        console.error("Failed to play audio:", error);
        alert("Could not play the audio feedback.");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
      <div className="flex flex-col h-full bg-gray-800 p-6 rounded-xl">
        <h2 className="text-xl font-bold mb-4">Writing Practice</h2>
        <div className="mb-4">
            <label className="text-sm font-medium text-gray-300">Writing Type</label>
            <div className="flex flex-wrap gap-2 mt-2">
                {WRITING_TYPES.map(type => (
                    <button key={type} onClick={() => setWritingType(type)} className={`px-3 py-1.5 text-sm rounded-full transition-colors ${writingType === type ? 'bg-indigo-600 text-white font-semibold' : 'bg-gray-700 hover:bg-gray-600 text-gray-200'}`}>
                        {type}
                    </button>
                ))}
            </div>
        </div>
        <div className="flex-1 flex flex-col">
            <label htmlFor="essay-input" className="text-sm font-medium text-gray-300 mb-2">Your Text</label>
            <textarea
                id="essay-input"
                value={essayText}
                onChange={(e) => setEssayText(e.target.value)}
                placeholder="Start writing here after generating a topic, or write about anything you want..."
                className="w-full flex-1 bg-gray-900 border border-gray-700 rounded-lg p-4 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            />
        </div>
         <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={handleGenerateTopic} disabled={isLoading} className="flex items-center justify-center px-4 py-2 bg-gray-600 text-white font-semibold rounded-lg hover:bg-gray-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            <SparklesIcon className="w-5 h-5 mr-2" />
            New Topic
          </button>
          <button onClick={handleEvaluate} disabled={isLoading || !essayText.trim()} className="flex items-center justify-center px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            Evaluate
          </button>
          <button onClick={handlePlayAudio} disabled={isLoading || !hasEvaluated} className="flex items-center justify-center px-4 py-2 bg-teal-500 text-white font-semibold rounded-lg hover:bg-teal-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
            <PlayIcon className="w-5 h-5 mr-2" />
            Play Feedback
          </button>
          <button onClick={() => setEssayText('')} disabled={isLoading} className="px-4 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50">
            Clear
          </button>
        </div>
      </div>
      <div className="flex flex-col h-full bg-gray-800 p-6 rounded-xl">
        <h2 className="text-xl font-bold mb-4">Feedback</h2>
        <div className="flex-1 overflow-y-auto">
            <Chatbot messages={feedbackMessages} isLoading={isLoading} />
        </div>
      </div>
      <audio ref={audioPlayerRef} className="hidden" />
    </div>
  );
};

export default WritingTab;