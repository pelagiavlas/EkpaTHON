import { Link, useNavigate, useParams } from "react-router-dom";
import { BookOpen, ChevronRight } from "lucide-react";
import { Screen } from "../components/Screen";
import { LevelSteps, Loading, Notice } from "../components/common";
import type { Chapter } from "../types";
import { useLoad } from "../useLoad";

export function sectionLabel(s: { number: string | null; title: string }) {
  return s.number ? `${s.number} ${s.title}` : s.title;
}

export function ChapterScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: chapter, error } = useLoad<Chapter>(`/documents/${id}`);

  return (
    <Screen
      title={chapter?.title ?? "Κεφάλαιο"}
      back={chapter ? `/courses/${chapter.course_id}` : "/"}
      listen={chapter ? [{ text: `${chapter.title}. Έχει ${chapter.sections.length} ενότητες.` }] : undefined}
    >
      {error && <Notice tone="error" live>{error}</Notice>}
      {!chapter && !error && <Loading />}
      {chapter && (
        <>
          <p>Το κεφάλαιο έχει {chapter.sections.length} μικρές ενότητες. Κάθε ενότητα έχει τον δικό της τρόπο μελέτης.</p>
          <ol className="cards">
            {chapter.sections.map((s, i) => (
              <li key={s.id}>
                <Link className="card card-link" to={`/sections/${s.id}`}>
                  <span className="card-number" aria-hidden="true">{i + 1}</span>
                  <span className="card-body">
                    <span className="card-title">{sectionLabel(s)}</span>
                    <LevelSteps level={s.level} compact />
                    {s.has_proposal && <span className="badge">Έχεις πρόταση</span>}
                  </span>
                  <ChevronRight aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ol>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${chapter.sections[0].id}`)}>
              <BookOpen aria-hidden="true" />
              Ξεκίνα από την αρχή
            </button>
          </div>
        </>
      )}
    </Screen>
  );
}
