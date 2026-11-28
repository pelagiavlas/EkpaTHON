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

export interface Milestone {
  key: string;
  text: string;
  created_at: string;
}

export interface Proposal {
  reason: string;
  from_level: number;
  to_level: number;
  message: string;
}

export interface Support {
  section_id: number;
  level: number;
  level_name: string;
  proposal: Proposal | null;
  new_milestones: Milestone[];
}

export interface Course {
  id: number;
  name: string;
  icon: string;
  chapters: number;
  proposals: number;
  from_eclass: boolean;
  teaching: string | null;
  studied: number;
  with_material: number;
  next_section_id: number | null;
  next_text: string | null;
}

export interface SectionSummary {
  id: number;
  number: string | null;
  title: string;
  level: number;
  level_name: string;
  has_proposal: boolean;
}

export interface Chapter {
  id: number;
  course_id: number;
  title: string;
  filename: string;
  uploaded_at: string;
  sections: SectionSummary[];
  concepts_known: number;
  concepts_total: number;
}

/** How well a concept is known, in words only (the probability stays on the server). */
export interface Concept {
  concept: string;
  label_key: "learning" | "almost" | "known";
  label: string;
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
  support: Support;
  position: number;
  total: number;
  prev_id: number | null;
  next_id: number | null;
  original: string[];
  easy: { blocks: Block[]; glossary: GlossaryEntry[]; source: string };
  demo: boolean;
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
  exam: boolean;
  questions: Question[];
  ask_strategy: boolean;
  last_strategy: { choice: string; label: string } | null;
}

export interface Hint {
  kind: "explain" | "search";
  step: number;
  text: string;
  action: "open_section" | "replay_example" | "open_original" | "highlight_paragraph" | "pick_sentence" | null;
  section_id: number | null;
  paragraph: number | null;
  sentences: string[];
  choices: Option[];
  example: Block | null;
  fell_back: boolean;
}

export interface PickResult {
  correct: boolean;
  message: string;
  fallback_hint: Hint | null;
  new_milestones: Milestone[];
}

export interface AnswerResult {
  outcome: "correct" | "try_again" | "self_check" | "explained" | "not_yet";
  message: string;
  key_point: string | null;
  done: boolean;
  proposal: Proposal | null;
  new_milestones: Milestone[];
}

export interface Note {
  id: number;
  kind: string;
  text: string;
  created_at: string;
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
  chapters: { title: string; sections: { id: number; label: string; level: number; level_name: string }[] }[];
  days: { day: string; questions: number; hints_per_question: number }[];
  weeks: WeekPoint[];
  level_history: { at: string; section: string; from_level: number; to_level: number }[];
  message: string;
  concepts: Concept[];
}

export interface Progress {
  simulated: boolean;
  message: string;
  courses: CourseProgress[];
  milestones: Milestone[];
}

export interface Supporter {
  id: number;
  name: string;
  token: string;
  created_at: string;
  active: boolean;
}

// --- eClass and "Σήμερα" ---

export interface NextClass {
  course_id: number;
  course_name: string;
  day: string;
  weekday: string;
  is_today: boolean;
  start: string;
  end: string;
  room: string;
  phase: "before" | "during" | "later";
}

export interface UnitChoice {
  unit_id: number;
  title: string;
}

export interface Today {
  now: string;
  demo: boolean;
  simulated_eclass: boolean;
  next_class: NextClass | null;
  before: { course_id: number; course_name: string; unit_id: number; unit_title: string; section_id: number | null; minutes: number | null } | null;
  after: { course_id: number; course_name: string; class_date: string; when: string; predicted: UnitChoice | null; units: UnitChoice[] } | null;
  new_material: { document_id: number; course_name: string; title: string; added_on: string }[];
}

export interface ConfirmResult {
  status: "done" | "unknown";
  unit_title: string | null;
  section_id: number | null;
  has_questions: boolean;
}

export interface Plan {
  teaching: { unit_id: number; title: string; week: number } | null;
  teaching_from: "confirmed" | "plan";
  week: number;
  units: { unit_id: number; title: string; week: number; taught: boolean; section_id: number | null; studied: boolean }[];
  studied: number;
  with_material: number;
  next: { section_id: number; text: string } | null;
  simulated_eclass: boolean;
}
