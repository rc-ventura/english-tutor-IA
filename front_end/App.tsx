
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import SpeakingTab from './components/SpeakingTab';
import WritingTab from './components/WritingTab';
import ProgressTab from './components/ProgressTab';
import { EnglishLevel, WritingType } from './types';
import { ENGLISH_LEVELS, WRITING_TYPES } from './constants';

export type ActiveTab = 'speaking' | 'writing' | 'progress';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('speaking');
  const [apiKey, setApiKey] = useState<string>('');
  const [englishLevel, setEnglishLevel] = useState<EnglishLevel>('B1');

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'speaking':
        return <SpeakingTab englishLevel={englishLevel} />;
      case 'writing':
        return <WritingTab englishLevel={englishLevel} />;
      case 'progress':
        return <ProgressTab />;
      default:
        return <SpeakingTab englishLevel={englishLevel} />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        apiKey={apiKey}
        setApiKey={setApiKey}
        englishLevel={englishLevel}
        setEnglishLevel={setEnglishLevel}
        englishLevels={ENGLISH_LEVELS}
      />
      <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
        {renderActiveTab()}
      </main>
    </div>
  );
};

export default App;
