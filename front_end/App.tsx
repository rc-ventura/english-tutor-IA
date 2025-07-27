import React, { useState } from "react";
import Sidebar from "./components/Sidebar";
import SpeakingTab from "./components/SpeakingTab";
import WritingTab from "./components/WritingTab";
import ProgressTab from "./components/ProgressTab";
import { EnglishLevel } from "./types";
import { ENGLISH_LEVELS } from "./constants";
import { BrainCircuitIcon } from "./components/icons/Icons";
import Login from "./components/Login";

export type ActiveTab = "speaking" | "writing" | "progress";

const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("speaking");
  const [apiKey, setApiKey] = useState<string>("");
  const [englishLevel, setEnglishLevel] = useState<EnglishLevel>("B1");
  const [isClientReady, setIsClientReady] = useState<boolean>(false);

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case "speaking":
        return <SpeakingTab englishLevel={englishLevel} />;
      case "writing":
        return <WritingTab englishLevel={englishLevel} />;
      case "progress":
        return <ProgressTab />;
      default:
        return <SpeakingTab englishLevel={englishLevel} />;
    }
  };

  if (!isLoggedIn) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

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
        isClientReady={isClientReady}
        setIsClientReady={setIsClientReady}
      />
      <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
        <div className="relative h-full">
          <div
            className={`transition-filter duration-300 h-full ${
              !isClientReady ? "blur-md pointer-events-none" : ""
            }`}
          >
            {renderActiveTab()}
          </div>
          {!isClientReady && (
            <div className="absolute inset-0 bg-gray-900/70 backdrop-blur-sm flex flex-col items-center justify-center z-10 rounded-lg">
              <div className="text-center p-8 bg-gray-800 rounded-2xl shadow-2xl border border-gray-700">
                <BrainCircuitIcon className="w-16 h-16 text-indigo-400 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-white mb-2">
                  Welcome to Sophia AI
                </h2>
                <p className="text-gray-300 max-w-sm">
                  To begin your interactive English learning session, please
                  save a valid API key in the Settings panel on the left.
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
