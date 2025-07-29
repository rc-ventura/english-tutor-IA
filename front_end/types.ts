import React from "react";
import { ENGLISH_LEVELS, WRITING_TYPES } from "./constants";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string | React.ReactNode;
  audioUrl?: string;
};

export type EnglishLevel = (typeof ENGLISH_LEVELS)[number];

export type WritingType = (typeof WRITING_TYPES)[number];

// --- Progress Dashboard Types ---

export interface SkillProgress {
  grammar: number;
  vocabulary: number;
  pronunciation: number;
}

export type BadgeName =
  | "First Steps"
  | "Getting Warmer"
  | "Rising Star"
  | "Master"
  | "Wordsmith"
  | "Grammar Guru";

export interface Badge {
  name: BadgeName;
  description: string;
  unlocked: boolean;
  iconName: BadgeName;
}

export interface ProgressData {
  xp: number;
  level: number;
  xpForCurrentLevel: number;
  xpForNextLevel: number;
  tasksCompleted: number;
  skills: SkillProgress;
  badges: Badge[];
}
