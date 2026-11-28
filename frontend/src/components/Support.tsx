import { useEffect, useState } from "react";
import { Check, CircleCheck, Flag, MapPin, Sparkles, X } from "lucide-react";
import { api, errorText } from "../api";
import { LEVELS, Notice } from "./common";
import type { Milestone, Support } from "../types";

/** "Θες λιγότερη/περισσότερη βοήθεια;" for one section. Nothing changes until the student says yes. */
export function SectionProposal({ support, onDone }: { support: Support; onDone: (s: Support) => void }) {
  const [error, setError] = useState<string | null>(null);
  const proposal = support.proposal;
  if (!proposal) return null;
  const decide = async (yes: boolean) => {
    try {
      const updated = yes
        ? await api.post<Support>(`/sections/${support.section_id}/level`, { level: proposal.to_level, reason: "proposal" })
        : await api.post<Support>(`/sections/${support.section_id}/proposal/decline`);
      onDone(updated);
    } catch (err) {
      setError(errorText(err));
    }
  };
  return (
    <section className="proposal" aria-labelledby={`proposal-${support.section_id}`}>
      <h2 id={`proposal-${support.section_id}`}>
        <Sparkles aria-hidden="true" />
        Μια πρόταση για αυτή την ενότητα
      </h2>
      <p>{proposal.message}</p>
      <p>
        <strong>Τι θα αλλάξει («{LEVELS[proposal.to_level].name}»):</strong>{" "}
        {LEVELS[proposal.to_level].description}
      </p>
      <p>Τα γράμματα, τα χρώματα και ο ήχος μένουν όπως τα έχεις. Μπορείς να το αλλάξεις ξανά όποτε θέλεις.</p>
      {error && <Notice tone="error" live>{error}</Notice>}
      <div className="actions actions-row">
        <button type="button" className="btn btn-primary" onClick={() => decide(true)}>
          <Check aria-hidden="true" />
          Ναι, ας δοκιμάσω
        </button>
        <button type="button" className="btn" onClick={() => decide(false)}>
          <X aria-hidden="true" />
          Όχι τώρα
        </button>
      </div>
    </section>
  );
}

/** Calm "first time" messages. No animation, no sound effect, shown once. */
export function MilestoneNotes({ items }: { items: Milestone[] }) {
  useEffect(() => {
    items.forEach((m) => api.post(`/milestones/${m.key}/seen`).catch(() => undefined));
  }, [items]);
  if (!items.length) return null;
  return (
    <>
      {items.map((m) => (
        <Notice key={m.key} tone="success" icon={Flag} live>
          <p>{m.text}</p>
        </Notice>
      ))}
    </>
  );
}

export interface SentencePick {
  paragraph: number;
  sentences: string[];
  tried: number[];
  found: number | null;
  onPick: (index: number) => void;
}

/** The ORIGINAL text, paragraphs numbered (hints say "2η παράγραφο").
 *  `highlight`: the paragraph a hint points to, marked with a frame AND the word "Εδώ".
 *  `pick`: the sentences of that paragraph become buttons (keyboard and screen reader friendly). */
export function OriginalText({ paragraphs, highlight, pick, idPrefix = "orig" }: {
  paragraphs: string[];
  highlight?: number | null;
  pick?: SentencePick | null;
  idPrefix?: string;
}) {
  return (
    <ol className="original-paras">
      {paragraphs.map((p, i) => {
        const here = highlight === i;
        const picking = pick && pick.paragraph === i;
        return (
          <li key={i} id={`${idPrefix}-p${i}`} className={here ? "para-here" : undefined}>
            {here && (
              <p className="here-label">
                <MapPin aria-hidden="true" /> Εδώ
              </p>
            )}
            {picking ? (
              <div role="group" aria-label="Πάτησε την πρόταση που ψάχνεις" className="sentence-group">
                {pick.sentences.map((s, j) => {
                  const tried = pick.tried.includes(j);
                  const found = pick.found === j;
                  return (
                    <button
                      key={j}
                      type="button"
                      className={`sentence-btn ${tried ? "is-tried" : ""} ${found ? "is-found" : ""}`}
                      aria-disabled={tried || pick.found !== null}
                      onClick={() => !tried && pick.found === null && pick.onPick(j)}
                    >
                      {found && <CircleCheck aria-hidden="true" />}
                      <span>{s}</span>
                      {tried && <span className="sentence-note">Όχι αυτή</span>}
                      {found && <span className="sentence-note">Τη βρήκες</span>}
                    </button>
                  );
                })}
              </div>
            ) : (
              <p>{p}</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
