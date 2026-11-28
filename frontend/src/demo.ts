// Presentation mode. ?demo=1 in the URL turns it on for this browser tab, ?demo=0 turns it off.
// The backend can also turn it on for everyone with DEMO_MODE=true.
// Outside demo mode the level preview and the clock buttons are not rendered at all.
// In demo mode the app clock is set so that there is always a class at 11:00, and the
// presenter can choose "before" (09:30) or "after" (13:00) the class.

import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const KEY = "studybuddy-demo";
const MOMENT_KEY = "studybuddy-demo-moment";
export type Moment = "before" | "after";

function read(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    /* storage blocked: the URL flag still works on this page */
  }
}

export function useDemoMode(serverDemo = false): boolean {
  const { search } = useLocation();
  // Read the URL on the very first render too, so the first request already uses the demo clock.
  const [tabDemo, setTabDemo] = useState(() => {
    const fromUrl = new URLSearchParams(search).get("demo");
    return fromUrl !== null ? fromUrl === "1" : read(KEY) === "1";
  });

  useEffect(() => {
    const value = new URLSearchParams(search).get("demo");
    if (value === null) return;
    write(KEY, value === "1" ? "1" : null);
    setTabDemo(value === "1");
  }, [search]);

  return serverDemo || tabDemo;
}

/** Query string for API calls that depend on the app clock (Σήμερα, courses, plan). */
export function useClock() {
  const tabDemo = useDemoMode();
  const [moment, setMomentState] = useState<Moment>(() => (read(MOMENT_KEY) === "after" ? "after" : "before"));
  const setMoment = useCallback((m: Moment) => {
    write(MOMENT_KEY, m);
    setMomentState(m);
  }, []);
  const query = `moment=${moment}${tabDemo ? "&demo=true" : ""}`;
  return { tabDemo, moment, setMoment, query };
}

/** Remember ?demo=1 even on pages without a preview, so it lasts for the whole tab. */
export function DemoFlagListener() {
  useDemoMode();
  return null;
}
