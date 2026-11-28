import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Accessibility, Check, ChevronRight, Contrast, Footprints, Type, UserRound, Volume2, type LucideIcon,
} from "lucide-react";
import { Screen } from "../components/Screen";
import { Notice } from "../components/common";
import { useSettings } from "../settings";
import { useSpeech } from "../speech";
import type { Settings } from "../types";

const MENU: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/settings/text", label: "Γράμματα και διάστιχο", icon: Type },
  { to: "/settings/colors", label: "Χρώματα και αντίθεση", icon: Contrast },
  { to: "/settings/sound", label: "Ανάγνωση φωναχτά", icon: Volume2 },
  { to: "/settings/motion", label: "Κίνηση", icon: Footprints },
  { to: "/settings/supporter", label: "Υποστηρικτής", icon: UserRound },
  { to: "/accessibility", label: "Δήλωση προσβασιμότητας", icon: Accessibility },
];

export function SettingsHome() {
  return (
    <Screen title="Ρυθμίσεις" back="/">
      <p>Διάλεξε τι θέλεις να αλλάξεις. Οι αλλαγές γίνονται αμέσως.</p>
      <ul className="cards">
        {MENU.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <Link className="card card-link" to={to}>
              <Icon aria-hidden="true" className="course-icon" />
              <span className="card-body">
                <span className="card-title">{label}</span>
              </span>
              <ChevronRight aria-hidden="true" />
            </Link>
          </li>
        ))}
      </ul>
    </Screen>
  );
}

/** A group of options where one is chosen (native radios: keyboard and screen readers work as expected). */
function OptionGroup<T extends string | number | boolean>({ legend, name, value, options, onChange }: {
  legend: string;
  name: string;
  value: T;
  options: { value: T; label: string; preview?: ReactNode }[];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="field">
      <legend>{legend}</legend>
      <div className="radio-cards">
        {options.map((o) => (
          <label key={String(o.value)} className={`radio-card ${o.value === value ? "is-on" : ""}`}>
            <input type="radio" name={name} checked={o.value === value} onChange={() => onChange(o.value)} />
            <span>
              {o.label}
              {o.preview}
            </span>
            {o.value === value && <Check aria-hidden="true" className="tick" />}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function useSaved() {
  const { settings, update } = useSettings();
  const [saved, setSaved] = useState(false);
  const change = async (changes: Partial<Settings>) => {
    setSaved(false);
    await update(changes);
    setSaved(true);
  };
  const status = (
    <p className="saved" role="status">
      {saved && (
        <>
          <Check aria-hidden="true" /> Αποθηκεύτηκε.
        </>
      )}
    </p>
  );
  return { settings, change, status };
}

const onOff = [
  { value: true, label: "Ναι" },
  { value: false, label: "Όχι" },
];

export function SettingsText() {
  const { settings, change, status } = useSaved();
  return (
    <Screen title="Γράμματα και διάστιχο" back="/settings">
      <OptionGroup legend="Μέγεθος γραμμάτων" name="font" value={settings.fontScale} onChange={(v) => change({ fontScale: v })}
        options={[
          { value: 1, label: "Κανονικά" },
          { value: 1.25, label: "Μεγάλα" },
          { value: 1.5, label: "Πολύ μεγάλα" },
          { value: 1.75, label: "Τεράστια" },
        ]} />
      <OptionGroup legend="Χώρος ανάμεσα στις γραμμές" name="spacing" value={settings.lineSpacing} onChange={(v) => change({ lineSpacing: v })}
        options={[
          { value: 1.6, label: "Κανονικός" },
          { value: 2, label: "Περισσότερος" },
          { value: 2.4, label: "Πολύς" },
        ]} />
      <p className="preview">Δείγμα: Ρωτάμε λίγους ανθρώπους. Αυτοί λέγονται δείγμα. Από αυτούς μαθαίνουμε κάτι για όλους.</p>
      {status}
    </Screen>
  );
}

export function SettingsColors() {
  const { settings, change, status } = useSaved();
  return (
    <Screen title="Χρώματα και αντίθεση" back="/settings">
      <OptionGroup legend="Έντονη αντίθεση: μαύρο φόντο, άσπρα και κίτρινα γράμματα" name="contrast" value={settings.highContrast}
        onChange={(v) => change({ highContrast: v })} options={onOff} />
      {status}
    </Screen>
  );
}

export function SettingsMotion() {
  const { settings, change, status } = useSaved();
  return (
    <Screen title="Κίνηση" back="/settings">
      <OptionGroup legend="Λιγότερη κίνηση στην οθόνη" name="motion" value={settings.reducedMotion}
        onChange={(v) => change({ reducedMotion: v })} options={onOff} />
      <p>Η εφαρμογή δεν έχει κινούμενα σχέδια. Με αυτή τη ρύθμιση σταματούν και οι μικρές μεταβάσεις.</p>
      {status}
    </Screen>
  );
}

export function SettingsSound() {
  const { settings, change, status } = useSaved();
  const speech = useSpeech();
  return (
    <Screen title="Ανάγνωση φωναχτά" back="/settings">
      {!speech.supported && (
        <Notice tone="calm"><p>Αυτός ο browser δεν μπορεί να διαβάσει φωναχτά. Δοκίμασε Chrome, Edge ή Safari.</p></Notice>
      )}
      {speech.supported && !speech.hasGreek && (
        <Notice tone="calm">
          <p>Δεν βρήκαμε ελληνική φωνή σε αυτή τη συσκευή. Μπορείς να προσθέσεις ελληνική φωνή από τις ρυθμίσεις της συσκευής.</p>
        </Notice>
      )}
      <OptionGroup legend="Να εμφανίζεται το κουμπί «Άκου»;" name="read" value={settings.readAloud}
        onChange={(v) => change({ readAloud: v })} options={onOff} />
      <OptionGroup legend="Να διαβάζει μόνο του κάθε νέα οθόνη;" name="auto" value={settings.autoRead}
        onChange={(v) => change({ autoRead: v })} options={onOff} />
      <OptionGroup legend="Ταχύτητα φωνής" name="rate" value={settings.voiceRate} onChange={(v) => change({ voiceRate: v })}
        options={[
          { value: 0.7, label: "Αργά" },
          { value: 0.9, label: "Κανονικά" },
          { value: 1.1, label: "Γρήγορα" },
        ]} />
      <div className="actions">
        <button type="button" className="btn" disabled={!speech.supported}
          onClick={() => speech.speak("Έτσι ακούγεται η φωνή. Ρωτάμε λίγους ανθρώπους. Αυτοί λέγονται δείγμα.")}>
          <Volume2 aria-hidden="true" />
          Δοκίμασε τη φωνή
        </button>
      </div>
      {status}
    </Screen>
  );
}
