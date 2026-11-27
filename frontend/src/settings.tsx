import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Settings } from "./types";

const STORAGE_KEY = "studybuddy-settings";

function media(query: string): boolean {
  return typeof window !== "undefined" && window.matchMedia?.(query).matches === true;
}

// First values come from the device: less motion and more contrast if the system asks for them.
export function deviceDefaults(): Settings {
  return {
    fontScale: 1,
    lineSpacing: 1.6,
    highContrast: media("(prefers-contrast: more)") || media("(forced-colors: active)"),
    reducedMotion: media("(prefers-reduced-motion: reduce)"),
    readAloud: true,
    autoRead: true,
    voiceRate: 0.9,
    onboarded: false,
  };
}

function readCache(): Settings | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...deviceDefaults(), ...JSON.parse(raw) } : null;
  } catch {
    return null;
  }
}

function writeCache(settings: Settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    /* private mode: settings still live on the server */
  }
}

export function applySettings(s: Settings) {
  const root = document.documentElement;
  root.style.setProperty("--font-scale", String(s.fontScale));
  root.style.setProperty("--line-height", String(s.lineSpacing));
  root.classList.toggle("high-contrast", s.highContrast);
  root.classList.toggle("reduce-motion", s.reducedMotion);
}

interface SettingsContextValue {
  settings: Settings;
  loaded: boolean;
  update: (changes: Partial<Settings>) => Promise<void>;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => readCache() ?? deviceDefaults());
  const [loaded, setLoaded] = useState(false);

  useEffect(() => applySettings(settings), [settings]);

  useEffect(() => {
    api
      .get<Settings>("/settings")
      .then((server) => {
        // A fresh profile on the server gets the device-based defaults.
        const merged = server.onboarded ? server : { ...server, highContrast: settings.highContrast, reducedMotion: settings.reducedMotion };
        setSettings(merged);
        writeCache(merged);
      })
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const current = useRef(settings);
  current.current = settings;

  const update = useCallback(async (changes: Partial<Settings>) => {
    const next = { ...current.current, ...changes };
    current.current = next;
    setSettings(next);
    writeCache(next);
    await api.put<Settings>("/settings", next).catch(() => undefined);
  }, []);

  return <SettingsContext.Provider value={{ settings, loaded, update }}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings outside SettingsProvider");
  return value;
}
