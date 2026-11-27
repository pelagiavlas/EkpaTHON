import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, CircleHelp, FileText, Info, Sparkles } from "lucide-react";
import { api } from "../api";
import { Screen } from "../components/Screen";
import { EasyBlocks, blockSpeech, paginate, visibleBlocks } from "../components/Blocks";
import { Loading, Notice } from "../components/common";
import { sectionLabel } from "./Chapter";
import { useSettings } from "../settings";
import type { Study } from "../types";
import { useLoad } from "../useLoad";

export function StudyScreen() {
  const { id } = useParams();
  return <StudySection key={id} id={id!} />;
}

function StudySection({ id }: { id: string }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const { data, error } = useLoad<Study>(`/sections/${id}/study`);
  const [mode, setMode] = useState<"easy" | "original" | null>(null);
  const [page, setPage] = useState(0);
  const pageHeading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  // Level 4 starts from the original; every other level from the Easy-to-Read text.
  const shown = mode ?? (data && data.level >= 4 ? "original" : "easy");
  const blocks = useMemo(() => (data ? visibleBlocks(data.easy.blocks, data.level) : []), [data]);
  const pages = useMemo(() => paginate(blocks), [blocks]);
  const pageBlocks = pages[page] ?? [];
  const offset = pages.slice(0, page).reduce((n, p) => n + p.length, 0);
  const lastPage = shown === "original" || page >= pages.length - 1;

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    pageHeading.current?.focus();
  }, [page, shown]);

  const switchMode = (next: "easy" | "original") => {
    setMode(next);
    api.post(`/sections/${id}/views`, { mode: next }).catch(() => undefined);
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
      autoRead={!!data && settings.autoRead && data.level <= 2 && shown === "easy"}
    >
      {error && <Notice tone="error" live>{error}</Notice>}
      {!data && !error && <Loading />}
      {data && (
        <>
          <p className="step-count">
            Ενότητα {data.position} από {data.total} · {data.document_title}
          </p>

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
                Μέρος {page + 1} από {pages.length}
              </h2>
              <EasyBlocks blocks={pageBlocks} glossary={data.easy.glossary} offset={offset} />
            </section>
          ) : (
            <section aria-labelledby="page-title" className="original">
              <h2 id="page-title" ref={pageHeading} tabIndex={-1} className="page-title">
                Το πρωτότυπο κείμενο
              </h2>
              {data.original.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </section>
          )}

          {data.easy.glossary.length > 0 && (
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
                <CircleHelp aria-hidden="true" />
                Πάμε στις ερωτήσεις
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => setPage(page + 1)}>
                <ChevronRight aria-hidden="true" />
                Συνέχεια
              </button>
            )}
            {shown === "easy" && page > 0 && (
              <button type="button" className="btn" onClick={() => setPage(page - 1)}>
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
