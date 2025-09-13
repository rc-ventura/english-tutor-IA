import React, { useState, useCallback, useEffect } from "react";
import * as api from "../services/api";
import { ProgressData, Badge as BadgeType, BadgeName } from "../types";
import {
  FirstStepsIcon,
  GettingWarmerIcon,
  RisingStarIcon,
  MasterIcon,
  WordsmithIcon,
  GrammarGuruIcon,
  LockIcon,
} from "./icons/Icons";

const badgeIcons: Record<BadgeName, React.FC<any>> = {
  "First Steps": FirstStepsIcon,
  "Getting Warmer": GettingWarmerIcon,
  "Rising Star": RisingStarIcon,
  Master: MasterIcon,
  Wordsmith: WordsmithIcon,
  "Grammar Guru": GrammarGuruIcon,
};

const Badge: React.FC<{ badge: BadgeType }> = ({ badge }) => {
  const Icon = badge.unlocked ? badgeIcons[badge.iconName] : LockIcon;
  const colorClass = badge.unlocked
    ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
    : "bg-gray-700/20 text-gray-500 border-gray-700/50";
  const iconColor = badge.unlocked ? "text-indigo-400" : "text-gray-500";

  return (
    <div
      title={badge.description}
      className={`flex flex-col items-center justify-center p-4 text-center border rounded-xl transition-all duration-300 ${colorClass} ${
        !badge.unlocked ? "grayscale" : "hover:bg-indigo-500/20"
      }`}
    >
      <div
        className={`w-16 h-16 flex items-center justify-center rounded-full bg-gray-800/50 mb-3 ${
          !badge.unlocked ? "opacity-60" : ""
        }`}
      >
        <Icon className={`w-8 h-8 ${iconColor}`} />
      </div>
      <h4 className="font-semibold text-sm text-gray-200">{badge.name}</h4>
      <p className="text-xs text-gray-400 mt-1">{badge.description}</p>
    </div>
  );
};

const SkillBar: React.FC<{ name: string; value: number; color: string }> = ({
  name,
  value,
  color,
}) => (
  <div>
    <div className="flex justify-between items-baseline mb-1">
      <span className="text-sm font-medium text-gray-300">{name}</span>
      <span className="text-sm font-semibold" style={{ color }}>
        {value}%
      </span>
    </div>
    <div className="w-full bg-gray-700 rounded-full h-2.5">
      <div
        className={`h-2.5 rounded-full transition-all duration-500`}
        style={{ width: `${value}%`, backgroundColor: color }}
      ></div>
    </div>
  </div>
);

const CircularProgressBar: React.FC<{ progress: number; level: number }> = ({
  progress,
  level,
}) => {
  const radius = 56;
  const stroke = 10;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg
        height={radius * 2}
        width={radius * 2}
        className="transform -rotate-90"
      >
        <circle
          stroke="currentColor"
          className="text-gray-700"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke="currentColor"
          className="text-indigo-400"
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={circumference + " " + circumference}
          style={{
            strokeDashoffset,
            transition: "stroke-dashoffset 0.5s ease-out",
          }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-xs text-gray-400">Level</span>
        <span className="text-4xl font-bold text-white">{level}</span>
      </div>
    </div>
  );
};

const ProgressTab: React.FC = () => {
  const [progressData, setProgressData] = useState<ProgressData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProgress = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getProgressData();
      setProgressData(data);
    } catch (err) {
      console.error("Failed to fetch progress:", err);
      setError("Could not load progress data. Please try refreshing.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-400"></div>
      </div>
    );
  }

  if (error || !progressData) {
    return (
      <div className="text-center py-10">
        <p className="text-red-400 mb-4">
          {error || "No progress data available."}
        </p>
        <button
          onClick={fetchProgress}
          className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const {
    level,
    xp,
    xpForCurrentLevel,
    xpForNextLevel,
    tasksCompleted,
    skills = { grammar: 0, vocabulary: 0, pronunciation: 0 },
    badges = [],
  } = progressData;

  const xpInLevel = xp - xpForCurrentLevel;
  const xpNeededForLevel = xpForNextLevel - xpForCurrentLevel;
  const levelProgress =
    xpNeededForLevel > 0 ? (xpInLevel / xpNeededForLevel) * 100 : 100;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-white">Progress Dashboard</h1>
        <button
          onClick={fetchProgress}
          disabled={isLoading}
          className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {/* Level & Stats */}
        <div className="md:col-span-1 lg:col-span-1 space-y-6">
          <div className="bg-gray-800 p-6 rounded-2xl text-center shadow-lg border border-gray-700">
            <CircularProgressBar progress={levelProgress} level={level} />
            <p className="font-bold text-xl text-white mt-4">
              {xp}{" "}
              <span className="text-base font-normal text-gray-400">XP</span>
            </p>
            <p className="text-sm text-gray-400">
              {xpNeededForLevel - xpInLevel} XP to next level
            </p>
          </div>
          <div className="bg-gray-800 p-6 rounded-2xl text-center shadow-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-300">
              Tasks Completed
            </h3>
            <p className="text-5xl font-bold text-white mt-2">
              {tasksCompleted}
            </p>
          </div>
        </div>

        {/* Skills & Badges */}
        <div className="md:col-span-2 lg:col-span-3 space-y-6">
          <div className="bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-300 mb-4">
              Skill Proficiency
            </h3>
            <div className="space-y-4">
              <SkillBar name="Grammar" value={skills.grammar} color="#818cf8" />
              <SkillBar
                name="Vocabulary"
                value={skills.vocabulary}
                color="#60a5fa"
              />
              <SkillBar
                name="Pronunciation"
                value={skills.pronunciation}
                color="#34d399"
              />
            </div>
          </div>
          <div className="bg-gray-800 p-6 rounded-2xl shadow-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-300 mb-4">
              Unlocked Badges
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {badges.map((badge) => (
                <Badge key={badge.name} badge={badge} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressTab;
