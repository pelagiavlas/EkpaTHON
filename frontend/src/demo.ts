// Presentation mode. ?demo=1 in the URL turns it on for this browser tab, ?demo=0 turns it off.
// The backend can also turn it on for everyone with DEMO_MODE=true.
// Outside demo mode the level preview is not rendered at all (not even hidden).

import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const KEY = "studybuddy-demo";

function readFlag(): boolean {
  try {
    return sessionStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function useDemoMode(serverDemo = false): boolean {
  const { search } = useLocation();
  const [tabDemo, setTabDemo] = useState(readFlag);

  useEffect(() => {
    const value = new URLSearchParams(search).get("demo");
    if (value === null) return;
    try {
      if (value === "1") sessionStorage.setItem(KEY, "1");
      else sessionStorage.removeItem(KEY);
    } catch {
      /* storage blocked: the URL flag still works on this page */
    }
    setTabDemo(value === "1");
  }, [search]);

  return serverDemo || tabDemo;
}

/** Remember ?demo=1 even on pages without a preview, so it lasts for the whole tab. */
export function DemoFlagListener() {
  useDemoMode();
  return null;
}
