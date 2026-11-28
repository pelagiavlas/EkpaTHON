import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, ChevronLeft, ChevronRight, CircleHelp, Eye, FileText, Info, PenLine, Sparkles } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { EasyBlocks, blockSpeech, paginate, visibleBlocks } from "../components/Blocks";
import { LevelSteps, LEVELS, Loading, Notice } from "../components/common";
import { MilestoneNotes, OriginalText, SectionProposal } from "../components/Support";
import { LevelChoice } from "./Course";
import { sectionLabel } from "./Chapter";
import { useSettings } from "../settings";
import type { Milestone, Study, Support } from "../types";
import { useLoad } from "../useLoad";

/** How the LEARNING support looks at each level. Accessibility settings are not here on purpose:
 *  letters, spacing, colours, voice and motion come only from the student's settings. */
export function levelView(level: number) {
  return {
    startsWithOriginal: level >= 3,
    termMode: level <= 1 ? ("inline" as const) : ("tap" as const),
    pictureLevel: Math.min(level, 2), // level 1: every picture, level 2+: hard ideas only
    maxTexts: level <= 1 ? 3 : 6,
    visualEndsPage: level <= 1,
    glossary: level === 4 ? ("none" as const) : level === 3 ? ("closed" as const) : ("open" as const),
  };
}

export function StudyScreen() {
  const { id } = useParams();
  return <StudySection key={id} id={id!} />;
}

function StudySection({ id }: { id: string }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const { data, error } = useLoad<Study>(`/sections/${id}/study`);
  const [support, setSupport] = useState<Support | null>(null);
  const [preview, setPreview] = useState<number | null>(null);
  const [mode, setMode] = useState<"easy" | "original" | null>(null);
  const [page, setPage] = useState(0);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const visitId = useRef<number | null>(null);
  const visitStarted = useRef(false);
  const pageHeading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  useEffect(() => {
    if (data && !support) setSupport(data.support);
  }, [data, support]);

  useEffect(() => {
    if (visitStarted.current) return;
    visitStarted.current = true;
    api.post<{ visit_id: number }>(`/sections/${id}/visits`).then((v) => (visitId.current = v.visit_id)).catch(() => undefined);
  }, [id]);

  const realLevel = support?.level ?? 1;
  const level = preview ?? realLevel;
  const view = levelView(level);
  const shown = mode ?? (view.startsWithOriginal ? "original" : "easy");
  // At levels 3-4 the Easy-to-Read text, when opened, looks like level 2.
  const easyView = levelView(Math.min(level, 2));
  const blocks = useMemo(() => (data ? visibleBlocks(data.easy.blocks, easyView.pictureLevel) : []), [data, easyView.pictureLevel]);
  const pages = useMemo(() => paginate(blocks, easyView.maxTexts, easyView.visualEndsPage), [blocks, easyView.maxTexts, easyView.visualEndsPage]);
  const safePage = Math.min(page, Math.max(0, pages.length - 1));
  const pageBlocks = pages[safePage] ?? [];
  const offset = pages.slice(0, safePage).reduce((n, p) => n + p.length, 0);
  const lastPage = shown === "original" || safePage >= pages.length - 1;

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    pageHeading.current?.focus();
  }, [page, shown]);

  const switchMode = (next: "easy" | "original") => {
    setMode(next);
    setPage(0);
    // Opening the Easy-to-Read text at levels 3-4 is noted: used often, it brings a proposal (never a change).
    if (next === "easy" && realLevel >= 3 && preview === null && visitId.current) {
      api.post<Support>(`/visits/${visitId.current}/easy`).then(setSupport).catch(() => undefined);
    }
  };

  const listen = !data
    ? undefined
    : shown === "easy"
      ? [{ text: sectionLabel(data) }, ...blockSpeech(pageBlocks, data.easy.glossary, "b", offset)]
      : [{ text: sectionLabel(data) }, ...data.original.map((text) => ({ text }))];

  return (
    <Screen
      title={data ? sectionLabel(data) : "Ενότητα"}
      back={data ? `/chapters/${data.document_id}` : "/"}
      listen={listen}
      autoRead={!!data && settings.autoRead}
    >
      {error && <Notice tone="error" live>{error}</Notice>}
      {!data && !error && <Loading />}
      {data && support && (
        <>
          <p className="step-count">
            Ενότητα {data.position} από {data.total} · {data.document_title}
          </p>
          <div className="level-row">
            <LevelSteps level={realLevel} compact />
            <Link className="text-link" to={`/sections/${id}/level`}>Άλλαξε επίπεδο</Link>
          </div>

          {preview === null && (
            <SectionProposal
              support={support}
              onDone={(s) => {
                setSupport(s);
                setMode(null);
                setMilestones(s.new_milestones);
              }}
            />
          )}
          <MilestoneNotes items={milestones} />

          {data.demo && <LevelPreview value={preview} real={realLevel} onChange={(l) => { setPreview(l); setMode(null); setPage(0); }} />}

          {/* "Εύκολο κείμενο" is always here, at every level, in the same place. */}
          <div className="toggle" role="group" aria-label="Πώς θέλεις να δεις το κείμενο">
            <button type="button" className="btn btn-toggle" aria-pressed={shown === "easy"} onClick={() => switchMode("easy")}>
              <Sparkles aria-hidden="true" />
              Εύκολο κείμενο
            </button>
            <button type="button" className="btn btn-toggle" aria-pressed={shown === "original"} onClick={() => switchMode("original")}>
              <FileText aria-hidden="true" />
              Πρωτότυπο
            </button>
          </div>

          {shown === "easy" ? (
            <section aria-labelledby="page-title">
              {data.easy.source === "rules" && (
                <Notice icon={Info}>
                  <p>Αυτό το κείμενο απλοποιήθηκε αυτόματα. Αν κάτι δεν είναι καθαρό, δες το πρωτότυπο.</p>
                </Notice>
              )}
              <h2 id="page-title" ref={pageHeading} tabIndex={-1} className="page-title">
                Μέρος {safePage + 1} από {pages.length}
              </h2>
              <EasyBlocks blocks={pageBlocks} glossary={data.easy.glossary} offset={offset} termMode={easyView.termMode} />
            </section>
          ) : (
            <section aria-labelledby="page-title" className="original">
              <h2 id="page-title" ref={pageHeading} tabIndex={-1} className="page-title">
                Το πρωτότυπο κείμενο
              </h2>
              <OriginalText paragraphs={data.original} />
            </section>
          )}

          {data.easy.glossary.length > 0 && view.glossary !== "none" && (
            <details className="glossary">
              <summary>Λέξεις της ενότητας ({data.easy.glossary.length})</summary>
              <dl>
                {data.easy.glossary.map((g) => (
                  <div key={g.term}>
                    <dt>{g.term}</dt>
                    <dd>{g.gloss}</dd>
                  </div>
                ))}
              </dl>
            </details>
          )}

          <div className="actions">
            {lastPage ? (
              <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${id}/questions`)}>
                {realLevel >= 4 ? <PenLine aria-hidden="true" /> : <CircleHelp aria-hidden="true" />}
                {realLevel >= 4 ? "Τι κράτησες;" : "Πάμε στις ερωτήσεις"}
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => setPage(safePage + 1)}>
                <ChevronRight aria-hidden="true" />
                Συνέχεια
              </button>
            )}
            {shown === "easy" && safePage > 0 && (
              <button type="button" className="btn" onClick={() => setPage(safePage - 1)}>
                <ChevronLeft aria-hidden="true" />
                Προηγούμενο μέρος
              </button>
            )}
          </div>
        </>
      )}
    </Screen>
  );
}

/** Only with simulated (demo) data: see the same section as it looks at another level.
 *  Nothing is saved, the real level does not change. */
function LevelPreview({ value, real, onChange }: { value: number | null; real: number; onChange: (l: number | null) => void }) {
  return (
    <section className="panel preview-panel" aria-labelledby="preview-title">
      <h2 id="preview-title" className="with-icon">
        <Eye aria-hidden="true" />
        Προεπισκόπηση για την παρουσίαση
      </h2>
      <div className="toggle" role="group" aria-label="Δες την ενότητα σε επίπεδο">
        {[1, 2, 3, 4].map((l) => (
          <button key={l} type="button" className="btn btn-toggle" aria-pressed={(value ?? real) === l}
            onClick={() => onChange(l === real ? null : l)}>
            Επίπεδο {l}
          </button>
        ))}
      </div>
      {value !== null && (
        <Notice icon={Eye} live>
          <p>
            Έτσι φαίνεται η ενότητα στο επίπεδο {value}: {LEVELS[value].name}. Το πραγματικό επίπεδο ({real}) δεν αλλάζει.
          </p>
        </Notice>
      )}
    </section>
  );
}

export function ChangeLevel() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: support } = useLoad<Support>(`/sections/${id}/support`);
  const [level, setLevel] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chosen = level ?? support?.level ?? 1;

  const save = async () => {
    try {
      await api.post(`/sections/${id}/level`, { level: chosen, reason: "manual" });
      navigate(`/sections/${id}`);
    } catch (err) {
      setError(errorText(err));
    }
  };

  return (
    <Screen title="Άλλαξε επίπεδο βοήθειας" back={`/sections/${id}`}>
      <p>Το επίπεδο αλλάζει μόνο για αυτή την ενότητα. Τα γράμματα, τα χρώματα και ο ήχος μένουν όπως τα έχεις.</p>
      {support && <LevelChoice value={chosen} onChange={setLevel} />}
      {error && <Notice tone="error" live>{error}</Notice>}
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={save} disabled={!support}>
          <Check aria-hidden="true" />
          Αποθήκευση
        </button>
      </div>
    </Screen>
  );
}
