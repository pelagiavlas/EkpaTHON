// Shapes returned by the backend (backend/app/schemas.py).

export interface Settings {
  fontScale: number;
  lineSpacing: number;
  highContrast: boolean;
  reducedMotion: boolean;
  readAloud: boolean;
  autoRead: boolean;
  voiceRate: number;
  onboarded: boolean;
}

export interface Proposal {
  direction: "up" | "down";
  from_level: number;
  to_level: number;
  message: string;
}

export interface Course {
  id: number;
  name: string;
  icon: string;
  level: number;
  level_name: string;
  chapters: number;
  proposal: Proposal | null;
}

export interface SectionSummary {
  id: number;
  number: string | null;
  title: string;
}

export interface Chapter {
  id: number;
  course_id: number;
  title: string;
  filename: string;
  uploaded_at: string;
  start_level: number | null;
  suggested_level: number | null;
  sections: SectionSummary[];
}

export interface Upload {
  document: Chapter;
  suggestion: { level: number; level_name: string; reason: string };
  current_level: number;
}

export interface Block {
  type: "text" | "example" | "image" | "formula" | "key";
  text: string;
  title: string | null;
  image: string | null;
  alt: string | null;
  formula: string | null;
  symbols: { symbol: string; meaning: string }[];
  essential: boolean;
}

export interface GlossaryEntry {
  term: string;
  gloss: string;
}

export interface Study {
  id: number;
  number: string | null;
  title: string;
  document_id: number;
  document_title: string;
  course_id: number;
  course_name: string;
  level: number;
  position: number;
  total: number;
  prev_id: number | null;
  next_id: number | null;
  original: string[];
  easy: { blocks: Block[]; glossary: GlossaryEntry[]; source: string };
}

export interface Option {
  id: number;
  text: string;
  image: string | null;
}

export interface Question {
  id: number;
  prompt: string;
  image: string | null;
  image_alt: string | null;
  mode: "choice" | "open";
  options: Option[];
}

export interface Questions {
  section_id: number;
  course_id: number;
  level: number;
  questions: Question[];
  ask_strategy: boolean;
  last_strategy: { choice: string; label: string } | null;
}

export interface Hint {
  step: number;
  text: string;
  action: "open_section" | "replay_example" | null;
  section_id: number | null;
  choices: Option[];
  example: Block | null;
}

export interface AnswerResult {
  outcome: "correct" | "try_again" | "self_check" | "explained" | "not_yet";
  message: string;
  key_point: string | null;
  done: boolean;
  proposal: Proposal | null;
}

export interface WeekPoint {
  label: string;
  start: string;
  end: string;
  questions: number;
  hints_per_question: number | null;
}

export interface CourseProgress {
  id: number;
  name: string;
  icon: string;
  level: number;
  level_name: string;
  days: { day: string; questions: number; hints_per_question: number }[];
  weeks: WeekPoint[];
  level_history: { at: string; from_level: number; to_level: number }[];
  message: string;
}

export interface Progress {
  simulated: boolean;
  message: string;
  courses: CourseProgress[];
}

export interface Supporter {
  id: number;
  name: string;
  token: string;
  created_at: string;
  active: boolean;
}
