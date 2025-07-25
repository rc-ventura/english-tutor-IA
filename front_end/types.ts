import React from "react";
import { ENGLISH_LEVELS, WRITING_TYPES } from "./constants";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string | React.ReactNode;
  audioUrl?: string;
};

export type EnglishLevel = (typeof ENGLISH_LEVELS)[number];

export type WritingType = (typeof WRITING_TYPES)[number];
