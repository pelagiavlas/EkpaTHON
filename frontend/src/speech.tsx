// Read aloud with the Web Speech API, in Greek. One shared reader for the whole app,
// so "Άκου"/"Σταμάτα" always controls whatever is being read.
// Text is spoken sentence by sentence (long utterances get cut off in some browsers),
// and each piece says which element is being read, so it can be highlighted.

import {
  createContext, useCallback, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import { useSettings } from "./settings";

export interface SpeechPart {
  id?: string; // element to highlight while this part is read
  text: string;
}

const supported = typeof window !== "undefined" && "speechSynthesis" in window;

export function greekVoice(): SpeechSynthesisVoice | null {
  if (!supported) return null;
  return window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith("el")) ?? null;
}

// "[[δείγματος|δείγμα]]" -> "δείγματος"
export function plainText(text: string): string {
  return text.replace(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g, "$1");
}

function sentences(text: string): string[] {
  return plainText(text)
    .split(/(?<=[.;!:])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

interface SpeechValue {
  supported: boolean;
  enabled: boolean;
  speaking: boolean;
  currentId: string | undefined;
  hasGreek: boolean;
  speak: (parts: SpeechPart[] | string) => void;
  stop: () => void;
}

const SpeechContext = createContext<SpeechValue | null>(null);

export function SpeechProvider({ children }: { children: ReactNode }) {
  const { settings } = useSettings();
  const location = useLocation();
  const [speaking, setSpeaking] = useState(false);
  const [currentId, setCurrentId] = useState<string | undefined>();
  const [hasGreek, setHasGreek] = useState<boolean>(() => greekVoice() !== null);
  const runId = useRef(0);

  useEffect(() => {
    if (!supported) return;
    const check = () => setHasGreek(greekVoice() !== null);
    check();
    window.speechSynthesis.addEventListener("voiceschanged", check);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", check);
  }, []);

  const stop = useCallback(() => {
    runId.current += 1;
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
    setCurrentId(undefined);
  }, []);

  // A new screen never keeps talking about the old one. Layout effect: it runs before
  // the new screen's own effects, so the new screen can still start reading itself.
  useLayoutEffect(() => stop(), [location.pathname, stop]);

  const speak = useCallback(
    (parts: SpeechPart[] | string) => {
      if (!supported) return;
      stop();
      const run = runId.current;
      const queue = (typeof parts === "string" ? [{ text: parts }] : parts).flatMap((p) =>
        sentences(p.text).map((text) => ({ id: p.id, text })),
      );
      if (!queue.length) return;
      const voice = greekVoice();
      setSpeaking(true);
      const next = (i: number) => {
        if (run !== runId.current) return;
        if (i >= queue.length) {
          setSpeaking(false);
          setCurrentId(undefined);
          return;
        }
        const u = new SpeechSynthesisUtterance(queue[i].text);
        u.lang = "el-GR";
        if (voice) u.voice = voice;
        u.rate = settings.voiceRate;
        u.onend = () => next(i + 1);
        u.onerror = () => next(i + 1);
        setCurrentId(queue[i].id);
        window.speechSynthesis.speak(u);
      };
      next(0);
    },
    [settings.voiceRate, stop],
  );

  const value: SpeechValue = {
    supported,
    enabled: supported && settings.readAloud,
    speaking,
    currentId,
    hasGreek,
    speak,
    stop,
  };
  return <SpeechContext.Provider value={value}>{children}</SpeechContext.Provider>;
}

export function useSpeech(): SpeechValue {
  const value = useContext(SpeechContext);
  if (!value) throw new Error("useSpeech outside SpeechProvider");
  return value;
}
