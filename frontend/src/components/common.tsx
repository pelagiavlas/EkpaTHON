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

export const LEVELS: Record<number, { name: string; description: string }> = {
  1: { name: "Πλήρης βοήθεια", description: "Εύκολο κείμενο με εικόνες και ήχο. Ερωτήσεις με 2 επιλογές." },
  2: { name: "Καθοδηγούμενη βοήθεια", description: "Εύκολο κείμενο. Ερωτήσεις με 3 επιλογές. Υποδείξεις όταν τις ζητάς." },
  3: { name: "Λιγότερη βοήθεια", description: "Εύκολο κείμενο με λιγότερες εικόνες. Γράφεις την απάντηση με δικά σου λόγια." },
  4: { name: "Αυτονομία", description: "Ξεκινάς από το πρωτότυπο. Διαλέγεις εσύ τι χρειάζεσαι. Βοήθεια μόνο όταν τη ζητήσεις." },
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
        <strong>Επίπεδο {level} από 4:</strong> {LEVELS[level]?.name}
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

export function Loading({ text = "Περίμενε λίγο, φορτώνει..." }: { text?: string }) {
  return (
    <p className="loading" role="status">
      {text}
    </p>
  );
}
