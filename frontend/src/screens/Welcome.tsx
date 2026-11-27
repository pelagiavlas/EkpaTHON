import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Contrast, Footprints, MoveHorizontal, Type, Volume2, X, type LucideIcon } from "lucide-react";
import { Screen } from "../components/Screen";
import { useSettings } from "../settings";
import type { Settings } from "../types";

// First use: we ask what HELPS, never about a diagnosis. Only the chosen settings are kept.

interface Choice {
  label: string;
  icon: LucideIcon;
  set: Partial<Settings>;
  selected: (s: Settings) => boolean;
}

interface Step {
  question: string;
  explain: string;
  icon: LucideIcon;
  preview?: ReactNode;
  choices: Choice[];
}

const yesNo = (key: "readAloud" | "highContrast" | "reducedMotion"): Choice[] => [
  { label: "Ναι", icon: Check, set: { [key]: true }, selected: (s) => s[key] },
  { label: "Όχι", icon: X, set: { [key]: false }, selected: (s) => !s[key] },
];

const SAMPLE = "Ρωτάμε λίγους ανθρώπους. Αυτοί λέγονται δείγμα.";

const STEPS: Step[] = [
  {
    question: "Σε βοηθά να ακούς το κείμενο;",
    explain: "Η εφαρμογή μπορεί να διαβάζει φωναχτά κάθε κείμενο και κάθε ερώτηση.",
    icon: Volume2,
    choices: yesNo("readAloud"),
  },
  {
    question: "Θέλεις μεγαλύτερα γράμματα;",
    explain: "Διάλεξε το μέγεθος που διαβάζεις πιο εύκολα.",
    icon: Type,
    preview: <p className="preview">{SAMPLE}</p>,
    choices: [
      { label: "Όπως είναι", icon: Type, set: { fontScale: 1 }, selected: (s) => s.fontScale === 1 },
      { label: "Μεγαλύτερα", icon: Type, set: { fontScale: 1.25 }, selected: (s) => s.fontScale === 1.25 },
      { label: "Πολύ μεγάλα", icon: Type, set: { fontScale: 1.5 }, selected: (s) => s.fontScale === 1.5 },
    ],
  },
  {
    question: "Θέλεις περισσότερο χώρο ανάμεσα στις γραμμές;",
    explain: "Με περισσότερο χώρο, οι γραμμές δεν μπερδεύονται.",
    icon: MoveHorizontal,
    preview: <p className="preview">{SAMPLE} {SAMPLE}</p>,
    choices: [
      { label: "Ναι", icon: Check, set: { lineSpacing: 2 }, selected: (s) => s.lineSpacing >= 1.9 },
      { label: "Όχι", icon: X, set: { lineSpacing: 1.6 }, selected: (s) => s.lineSpacing < 1.9 },
    ],
  },
  {
    question: "Θέλεις πιο έντονα χρώματα;",
    explain: "Μαύρο φόντο με άσπρα και κίτρινα γράμματα. Κάποιοι διαβάζουν έτσι πιο εύκολα.",
    icon: Contrast,
    choices: yesNo("highContrast"),
  },
  {
    question: "Σε ενοχλεί όταν κάτι κινείται στην οθόνη;",
    explain: "Αν ναι, τίποτα δεν θα κινείται.",
    icon: Footprints,
    choices: yesNo("reducedMotion"),
  },
];

export function Welcome() {
  const { settings, update } = useSettings();
  const navigate = useNavigate();
  const [step, setStep] = useState(-1);

  const finish = async () => {
    await update({ onboarded: true });
    navigate("/", { replace: true });
  };

  if (step === -1) {
    return (
      <Screen title="Καλώς ήρθες" hideNav listen={[{ text: "Καλώς ήρθες. Θα σε ρωτήσουμε 5 απλά πράγματα. Έτσι η εφαρμογή θα σε βοηθά όπως θέλεις εσύ. Μπορείς να τα αλλάξεις όποτε θέλεις, στις Ρυθμίσεις." }]}>
        <p className="lead">Θα σε ρωτήσουμε 5 απλά πράγματα.</p>
        <p>Έτσι η εφαρμογή θα σε βοηθά όπως θέλεις εσύ.</p>
        <p>Μπορείς να τα αλλάξεις όποτε θέλεις, στις Ρυθμίσεις.</p>
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => setStep(0)}>
            <Check aria-hidden="true" />
            Ξεκίνα
          </button>
        </div>
      </Screen>
    );
  }

  if (step === STEPS.length) {
    return (
      <Screen title="Έτοιμο" hideNav back={() => setStep(STEPS.length - 1)} autoRead={settings.autoRead}
        listen={[{ text: "Έτοιμο. Πάμε στα μαθήματά σου." }]}>
        <p className="lead">Πάμε στα μαθήματά σου.</p>
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={finish}>
            <Check aria-hidden="true" />
            Πάμε
          </button>
        </div>
      </Screen>
    );
  }

  const current = STEPS[step];
  const Icon = current.icon;
  return (
    <Screen
      title={current.question}
      hideNav
      back={() => setStep(step - 1)}
      autoRead={settings.readAloud && settings.autoRead}
      listen={[{ text: `${current.question} ${current.explain} Οι επιλογές είναι: ${current.choices.map((c) => c.label).join(", ")}.` }]}
    >
      <p className="step-count">Ερώτηση {step + 1} από {STEPS.length}</p>
      <Icon aria-hidden="true" className="hero-icon" />
      <p>{current.explain}</p>
      {current.preview}
      <div className="choices" role="group" aria-label={current.question}>
        {current.choices.map((c) => {
          const ChoiceIcon = c.icon;
          const on = c.selected(settings);
          return (
            <button key={c.label} type="button" className={`btn btn-choice ${on ? "is-on" : ""}`} aria-pressed={on}
              onClick={() => update(c.set)}>
              <ChoiceIcon aria-hidden="true" />
              {c.label}
              {on && <Check aria-hidden="true" className="tick" />}
            </button>
          );
        })}
      </div>
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={() => setStep(step + 1)}>
          Συνέχεια
        </button>
      </div>
    </Screen>
  );
}
