import { Fragment, useState } from "react";
import { Lightbulb, Pin } from "lucide-react";
import type { Block, GlossaryEntry } from "../types";
import { Pictogram } from "./common";
import { useSpeech, type SpeechPart } from "../speech";

const TERM = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;

function glossMap(glossary: GlossaryEntry[]) {
  return new Map(glossary.map((g) => [g.term.toLowerCase(), g.gloss]));
}

/** "inline": the explanation is always next to the term (level 1).
 *  "tap": the term is a button, the explanation opens when pressed (level 2 and up). */
export type TermMode = "inline" | "tap";

function TapTerm({ shown, gloss }: { shown: string; gloss: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="term">
      <button type="button" className="term-btn" aria-expanded={open} onClick={() => setOpen(!open)}>
        <dfn>{shown}</dfn>
        <span className="sr-only">, δες τι σημαίνει</span>
      </button>
      {open && <span className="gloss"> ({gloss})</span>}
    </span>
  );
}

/** Text with academic terms kept, and a simple explanation for them. */
export function TermText({ text, glossary, mode = "inline" }: { text: string; glossary: GlossaryEntry[]; mode?: TermMode }) {
  const glosses = glossMap(glossary);
  const out = [];
  let last = 0;
  for (const match of text.matchAll(TERM)) {
    const [whole, shown, key] = match;
    out.push(text.slice(last, match.index));
    const gloss = glosses.get((key ?? shown).toLowerCase());
    out.push(
      gloss && mode === "tap" ? (
        <TapTerm key={match.index} shown={shown} gloss={gloss} />
      ) : (
        <span className="term" key={match.index}>
          <dfn>{shown}</dfn>
          {gloss && <span className="gloss"> ({gloss})</span>}
        </span>
      ),
    );
    last = (match.index ?? 0) + whole.length;
  }
  out.push(text.slice(last));
  return <>{out.map((part, i) => (typeof part === "string" ? <Fragment key={`t${i}`}>{part}</Fragment> : part))}</>;
}

/** Spoken version: each term is followed by "δηλαδή ..." the first time. */
export function speakable(text: string, glossary: GlossaryEntry[], said: Set<string>): string {
  const glosses = glossMap(glossary);
  return text.replace(TERM, (_, shown: string, key?: string) => {
    const term = (key ?? shown).toLowerCase();
    const gloss = glosses.get(term);
    if (!gloss || said.has(term)) return shown;
    said.add(term);
    return `${shown}, δηλαδή ${gloss},`;
  });
}

/** Level 1: a picture for every idea. Level 2 and up: pictures only for the hard ideas. */
export function visibleBlocks(blocks: Block[], level: number): Block[] {
  if (level <= 1) return blocks;
  return blocks
    .filter((b) => b.type !== "image" || b.essential)
    .map((b) => (b.type === "example" && !b.essential ? { ...b, image: null } : b));
}

export function blockSpeech(blocks: Block[], glossary: GlossaryEntry[], idPrefix = "b", offset = 0): SpeechPart[] {
  const said = new Set<string>();
  return blocks.map((b, i) => {
    const id = `${idPrefix}-${offset + i}`;
    switch (b.type) {
      case "example":
        return { id, text: `${b.title ?? "Παράδειγμα"}. ${speakable(b.text, glossary, said)}` };
      case "image":
        return { id, text: `Εικόνα: ${b.alt}` };
      case "formula":
        return { id, text: `Ο τύπος. ${b.symbols.map((s) => `${s.symbol}: ${s.meaning}.`).join(" ")}` };
      case "key":
        return { id, text: speakable(b.text, glossary, said) };
      default:
        return { id, text: speakable(b.text, glossary, said) };
    }
  });
}

export function EasyBlocks({ blocks, glossary, idPrefix = "b", offset = 0, termMode = "inline" }: {
  blocks: Block[];
  glossary: GlossaryEntry[];
  idPrefix?: string;
  offset?: number; // index of the first block in the whole section, so ids stay unique across pages
  termMode?: TermMode;
}) {
  const { currentId } = useSpeech();
  return (
    <div className="blocks">
      {blocks.map((b, i) => {
        const id = `${idPrefix}-${offset + i}`;
        const r = (base: string) => (id === currentId ? `${base} reading` : base);
        switch (b.type) {
          case "example":
            return (
              <figure key={id} id={id} className={r("block example")}>
                <figcaption className="example-title">
                  <Lightbulb aria-hidden="true" />
                  {b.title ?? "Παράδειγμα"}
                </figcaption>
                <p>
                  <TermText text={b.text} glossary={glossary} mode={termMode} />
                </p>
                {b.image && <Pictogram name={b.image} alt={b.alt ?? ""} />}
              </figure>
            );
          case "image":
            return (
              <figure key={id} id={id} className={r("block")}>
                <Pictogram name={b.image ?? ""} alt={b.alt ?? ""} />
              </figure>
            );
          case "formula":
            return (
              <div key={id} id={id} className={r("block formula")}>
                <p className="formula-text" lang="en">
                  {b.formula}
                </p>
                {b.symbols.length > 0 && (
                  <>
                    <p className="formula-help">Τι σημαίνει κάθε σύμβολο:</p>
                    <dl className="symbols">
                      {b.symbols.map((s) => (
                        <div key={s.symbol}>
                          <dt lang="en">{s.symbol}</dt>
                          <dd>{s.meaning}</dd>
                        </div>
                      ))}
                    </dl>
                  </>
                )}
              </div>
            );
          case "key":
            return (
              <p key={id} id={id} className={r("block key")}>
                <Pin aria-hidden="true" />
                <strong>
                  <TermText text={b.text} glossary={glossary} mode={termMode} />
                </strong>
              </p>
            );
          default:
            return (
              <p key={id} id={id} className={r("block")}>
                <TermText text={b.text} glossary={glossary} mode={termMode} />
              </p>
            );
        }
      })}
    </div>
  );
}

/** Pages: a picture or example closes a page at level 1; at most `maxTexts` paragraphs per page
 *  (level 1: 3, small parts; level 2 and up: 6, bigger parts). */
export function paginate(blocks: Block[], maxTexts = 3, visualEndsPage = true): Block[][] {
  const pages: Block[][] = [];
  let page: Block[] = [];
  let texts = 0;
  for (const [i, b] of blocks.entries()) {
    page.push(b);
    if (b.type === "text") texts += 1;
    const next = blocks[i + 1];
    const endsVisual = visualEndsPage && (b.type === "example" || b.type === "image" || b.type === "formula") && next?.type !== "image";
    if (endsVisual || texts >= maxTexts) {
      pages.push(page);
      page = [];
      texts = 0;
    }
  }
  if (page.length) {
    // A lonely "Το σημαντικό" goes with the page before it.
    if (page.length === 1 && page[0].type === "key" && pages.length) pages[pages.length - 1].push(page[0]);
    else pages.push(page);
  }
  return pages;
}
