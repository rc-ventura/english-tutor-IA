import React, { useState } from 'react';
import { EnglishLevel } from '../types';
import { ActiveTab } from '../App';
import { BrainCircuitIcon, SettingsIcon, MessageSquareIcon, PencilIcon, BarChartIcon, ChevronLeftIcon, ChevronRightIcon, SaveIcon, TrashIcon, ChevronDownIcon } from './icons/Icons';
import * as api from '../services/api';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  englishLevel: EnglishLevel;
  setEnglishLevel: (level: EnglishLevel) => void;
  englishLevels: readonly EnglishLevel[];
}

const NavButton: React.FC<{
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  isCollapsed: boolean;
  onClick: () => void;
}> = ({ icon, label, isActive, isCollapsed, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center w-full px-3 py-3 text-sm font-medium rounded-lg transition-colors duration-200 ${
      isActive
        ? 'bg-indigo-600 text-white'
        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
    }`}
  >
    {icon}
    {!isCollapsed && <span className="ml-3">{label}</span>}
  </button>
);

const SettingsAccordion: React.FC<{ title: string; children: React.ReactNode; id: string }> = ({ title, children, id }) => {
    const [isOpen, setIsOpen] = useState(false);
    const contentId = `accordion-content-${id}`;
    const headerId = `accordion-header-${id}`;

    return (
        <div className="border-b border-gray-700 last:border-b-0">
            <h4 id={headerId} className="text-base font-medium">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex justify-between items-center w-full px-3 py-3 text-sm font-medium text-left text-gray-300 hover:bg-gray-700/50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                    aria-expanded={isOpen}
                    aria-controls={contentId}
                >
                    <span>{title}</span>
                    <ChevronDownIcon className={`w-5 h-5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                </button>
            </h4>
            {isOpen && (
                <div id={contentId} role="region" aria-labelledby={headerId} className="px-3 pb-4 space-y-2">
                    {children}
                </div>
            )}
        </div>
    );
};


const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  apiKey,
  setApiKey,
  englishLevel,
  setEnglishLevel,
  englishLevels,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [tempApiKey, setTempApiKey] = useState(apiKey);

  const handleSaveKey = async () => {
    try {
      await api.setApiKey(tempApiKey);
      setApiKey(tempApiKey);
      alert('API key saved successfully!'); // Simple feedback
    } catch (error) {
      console.error('Failed to save API key:', error);
      alert('Failed to save API key.');
    }
  };

  const handleClearKey = () => {
    setTempApiKey('');
    setApiKey('');
  };

  return (
    <div className={`flex flex-col bg-gray-800 text-white transition-all duration-300 ease-in-out ${isCollapsed ? 'w-20' : 'w-64'}`}>
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!isCollapsed && <div className="flex items-center">
            <BrainCircuitIcon className="w-8 h-8 text-indigo-400" />
            <span className="ml-2 text-xl font-bold">Sophia AI</span>
        </div>}
        <button onClick={() => setIsCollapsed(!isCollapsed)} className="p-1 rounded-full hover:bg-gray-700">
            {isCollapsed ? <ChevronRightIcon className="w-6 h-6" /> : <ChevronLeftIcon className="w-6 h-6" />}
        </button>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        <NavButton icon={<MessageSquareIcon className="w-6 h-6" />} label="Speaking" isActive={activeTab === 'speaking'} isCollapsed={isCollapsed} onClick={() => setActiveTab('speaking')} />
        <NavButton icon={<PencilIcon className="w-6 h-6" />} label="Writing" isActive={activeTab === 'writing'} isCollapsed={isCollapsed} onClick={() => setActiveTab('writing')} />
        <NavButton icon={<BarChartIcon className="w-6 h-6" />} label="Progress" isActive={activeTab === 'progress'} isCollapsed={isCollapsed} onClick={() => setActiveTab('progress')} />
      </nav>

      <div className="p-4 border-t border-gray-700">
        <div className={`${isCollapsed ? 'hidden' : 'block'}`}>
            <h3 className="flex items-center mb-2 text-sm font-semibold text-gray-400 uppercase">
                <SettingsIcon className="w-5 h-5 mr-2" />
                Settings
            </h3>
            <div className="rounded-lg border border-gray-700 overflow-hidden">
                <SettingsAccordion title="API Key" id="api-key-accordion">
                    <div className="flex items-center">
                        <input
                            id="api-key"
                            type="password"
                            placeholder="sk-..."
                            aria-label="API Key Input"
                            value={tempApiKey}
                            onChange={(e) => setTempApiKey(e.target.value)}
                            className="w-full px-3 py-2 text-sm bg-gray-700 border border-gray-600 rounded-l-md focus:ring-indigo-500 focus:border-indigo-500"
                        />
                        <button onClick={handleSaveKey} className="p-2 bg-indigo-600 hover:bg-indigo-700 rounded-r-md" aria-label="Save API Key"><SaveIcon className="w-5 h-5"/></button>
                        <button onClick={handleClearKey} className="p-2 ml-1 bg-gray-600 hover:bg-gray-500 rounded-md" aria-label="Clear API Key"><TrashIcon className="w-5 h-5"/></button>
                    </div>
                </SettingsAccordion>
                <SettingsAccordion title="English Level" id="english-level-accordion">
                    <select
                        id="level-select"
                        value={englishLevel}
                        aria-label="English Level Selection"
                        onChange={(e) => setEnglishLevel(e.target.value as EnglishLevel)}
                        className="w-full px-3 py-2 text-sm bg-gray-700 border border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                    >
                        {englishLevels.map(level => (
                            <option key={level} value={level}>{level}</option>
                        ))}
                    </select>
                </SettingsAccordion>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;