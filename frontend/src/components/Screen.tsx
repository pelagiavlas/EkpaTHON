import { useEffect, useRef, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, ChartColumn, Settings as SettingsIcon, Square, Sun, Volume2 } from "lucide-react";
import { useSpeech, type SpeechPart } from "../speech";

interface ScreenProps {
  title: string;
  /** Where "Πίσω" goes. Every screen except the home screen has one, always in the same place. */
  back?: string | (() => void);
  /** What "Άκου" reads. Defaults to the title. */
  listen?: SpeechPart[];
  /** Read the screen aloud when it opens (only if the student wants that). */
  autoRead?: boolean;
  /** Supporter view: no student menu. */
  hideNav?: boolean;
  children: ReactNode;
}

export function Screen({ title, back, listen, autoRead = false, hideNav = false, children }: ScreenProps) {
  const heading = useRef<HTMLHeadingElement>(null);
  const navigate = useNavigate();
  const speech = useSpeech();
  const parts = listen ?? [{ text: title }];

  useEffect(() => {
    document.title = `${title} · Study Buddy`;
    heading.current?.focus();
  }, [title]);

  const autoKey = autoRead ? parts.map((p) => p.text).join("|") : "";
  useEffect(() => {
    if (autoKey && speech.enabled) speech.speak(parts);
    // Only when the content to read changes.
  }, [autoKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          {back ? (
            <button type="button" className="btn btn-quiet" onClick={() => (typeof back === "string" ? navigate(back) : back())}>
              <ArrowLeft aria-hidden="true" />
              <span>Πίσω</span>
            </button>
          ) : (
            <span className="topbar-spacer" />
          )}
          {speech.enabled && (
            <button
              type="button"
              className="btn btn-quiet"
              aria-pressed={speech.speaking}
              onClick={() => (speech.speaking ? speech.stop() : speech.speak(parts))}
            >
              {speech.speaking ? <Square aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
              <span>{speech.speaking ? "Σταμάτα" : "Άκου"}</span>
            </button>
          )}
        </div>
      </header>
      <main id="main" className="main">
        <h1 ref={heading} tabIndex={-1}>
          {title}
        </h1>
        {children}
      </main>
      {!hideNav && (
        <nav className="bottomnav" aria-label="Κύριο μενού">
          <NavLink to="/" end>
            <Sun aria-hidden="true" />
            <span>Σήμερα</span>
          </NavLink>
          <NavLink to="/courses">
            <BookOpen aria-hidden="true" />
            <span>Μαθήματα</span>
          </NavLink>
          <NavLink to="/progress">
            <ChartColumn aria-hidden="true" />
            <span>Πρόοδος</span>
          </NavLink>
          <NavLink to="/settings">
            <SettingsIcon aria-hidden="true" />
            <span>Ρυθμίσεις</span>
          </NavLink>
        </nav>
      )}
    </>
  );
}
