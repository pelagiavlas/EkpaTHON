import type { ReactNode } from "react";
import {
  Book, Brain, Calculator, ChartColumn, Code, FlaskConical, Globe, Info, Scale, type LucideIcon,
} from "lucide-react";

export const COURSE_ICONS: Record<string, { icon: LucideIcon; label: string }> = {
  chart: { icon: ChartColumn, label: "Γράφημα" },
  book: { icon: Book, label: "Βιβλίο" },
  flask: { icon: FlaskConical, label: "Επιστήμη" },
  calculator: { icon: Calculator, label: "Αριθμοί" },
  brain: { icon: Brain, label: "Ψυχολογία" },
  globe: { icon: Globe, label: "Κόσμος" },
  scale: { icon: Scale, label: "Δίκαιο" },
  code: { icon: Code, label: "Υπολογιστές" },
};

export function CourseIcon({ name }: { name: string }) {
  const Icon = (COURSE_ICONS[name] ?? COURSE_ICONS.book).icon;
  return <Icon aria-hidden="true" className="course-icon" />;
}

// What each level changes. Only learning support: never letters, spacing, colours, voice or motion.
export const LEVELS: Record<number, { name: string; description: string }> = {
  1: {
    name: "Με πολλή υποστήριξη",
    description: "Εύκολο κείμενο σε μικρά κομμάτια, με εικόνα και παράδειγμα. Οι δύσκολες λέξεις εξηγούνται μέσα στο κείμενο. Ερωτήσεις με 2 επιλογές.",
  },
  2: {
    name: "Με λιγότερη υποστήριξη",
    description: "Εύκολο κείμενο σε μεγαλύτερα κομμάτια. Εικόνες μόνο στα δύσκολα. Πατάς μια λέξη για να δεις τι σημαίνει. Ερωτήσεις με 3 επιλογές.",
  },
  3: {
    name: "Από το πρωτότυπο",
    description: "Πρώτα το πρωτότυπο κείμενο. Το Εύκολο κείμενο είναι ένα πάτημα μακριά. Γράφεις την απάντηση. Οι υποδείξεις σού δείχνουν πού να ψάξεις.",
  },
  4: {
    name: "Αυτόνομα",
    description: "Το πρωτότυπο κείμενο, χωρίς προσθήκες. Γράφεις τα βασικά σημεία ή μια δική σου ερώτηση. Βοήθεια μόνο όταν τη ζητήσεις.",
  },
};

/** Support level shown with text AND a staircase picture (never colour alone). */
export function LevelSteps({ level, compact = false }: { level: number; compact?: boolean }) {
  return (
    <div className="level">
      <svg className="level-steps" viewBox="0 0 64 40" aria-hidden="true">
        {[1, 2, 3, 4].map((n) => (
          <rect
            key={n}
            x={(n - 1) * 16 + 1}
            y={40 - n * 10}
            width={14}
            height={n * 10}
            rx={2}
            className={n <= level ? "step-on" : "step-off"}
          />
        ))}
      </svg>
      <span>
        <strong>Τρόπος μελέτης:</strong> {LEVELS[level]?.name}
        {!compact && <span className="level-desc">{LEVELS[level]?.description}</span>}
      </span>
    </div>
  );
}

export function Pictogram({ name, alt, className }: { name: string; alt: string; className?: string }) {
  return <img className={`picto ${className ?? ""}`} src={`/pictos/${name}.svg`} alt={alt} width={400} height={240} />;
}

type Tone = "info" | "success" | "calm" | "error";

export function Notice({ tone = "info", icon: Icon = Info, children, live = false }: {
  tone?: Tone;
  icon?: LucideIcon;
  children: ReactNode;
  live?: boolean;
}) {
  return (
    <div className={`notice notice-${tone}`} role={live ? (tone === "error" ? "alert" : "status") : undefined}>
      <Icon aria-hidden="true" className="notice-icon" />
      <div>{children}</div>
    </div>
  );
}

export function Loading({ text = "Φορτώνει..." }: { text?: string }) {
  return (
    <p className="loading" role="status">
      {text}
    </p>
  );
}
