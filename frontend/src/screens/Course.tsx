import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronRight, FileText, Trash2, Upload, X } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { LEVELS, LevelSteps, Loading, Notice } from "../components/common";
import type { Chapter, Course } from "../types";
import { useLoad } from "../useLoad";

export function CourseScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const course = useLoad<Course>(`/courses/${id}`);
  const chapters = useLoad<Chapter[]>(`/courses/${id}/documents`);
  const c = course.data;

  return (
    <Screen title={c?.name ?? "Μάθημα"} back="/" listen={c ? [{ text: `${c.name}. ${c.chapters} κεφάλαια.` }] : undefined}>
      {course.error && <Notice tone="error" live>{course.error}</Notice>}
      {!c && !course.error && <Loading />}
      {c && (
        <>
          <p>Κάθε ενότητα έχει τον δικό της τρόπο μελέτης. Όλες ξεκινούν «Με πολλή υποστήριξη».</p>
          <section aria-labelledby="chapters-title">
            <h2 id="chapters-title">Κεφάλαια</h2>
            {chapters.data?.length === 0 && <p>Δεν έχεις ανεβάσει ακόμα κεφάλαιο. Ανέβασε το PDF του μαθήματος.</p>}
            <ul className="cards">
              {chapters.data?.map((ch) => (
                <li key={ch.id}>
                  <Link className="card card-link" to={`/chapters/${ch.id}`}>
                    <FileText aria-hidden="true" className="course-icon" />
                    <span className="card-body">
                      <span className="card-title">{ch.title}</span>
                      <span>{ch.sections.length} ενότητες</span>
                      {ch.sections.some((s) => s.has_proposal) && <span className="badge">Έχεις πρόταση</span>}
                    </span>
                    <ChevronRight aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => navigate(`/courses/${c.id}/upload`)}>
              <Upload aria-hidden="true" />
              Ανέβασε PDF
            </button>
            <Link className="text-link danger-link" to={`/courses/${c.id}/delete`}>
              <Trash2 aria-hidden="true" />
              Σβήσε το μάθημα
            </Link>
          </div>
        </>
      )}
    </Screen>
  );
}

export function LevelChoice({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <fieldset className="field">
      <legend>Διάλεξε τρόπο μελέτης</legend>
      <div className="radio-cards">
        {[1, 2, 3, 4].map((n) => (
          <label key={n} className={`radio-card ${value === n ? "is-on" : ""}`}>
            <input type="radio" name="level" value={n} checked={value === n} onChange={() => onChange(n)} />
            <span>
              <LevelSteps level={n} compact />
              <span className="level-desc">{LEVELS[n].description}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function DeleteCourse() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: course } = useLoad<Course>(`/courses/${id}`);
  const [error, setError] = useState<string | null>(null);

  const remove = async () => {
    try {
      await api.del(`/courses/${id}`);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorText(err));
    }
  };

  return (
    <Screen title="Σβήσιμο μαθήματος" back={`/courses/${id}`}>
      <Notice tone="calm">
        <p>Θέλεις σίγουρα να σβήσεις το μάθημα «{course?.name}»;</p>
        <p>Θα σβηστούν τα PDF, οι απαντήσεις και η πρόοδος του μαθήματος. Αυτό δεν γυρίζει πίσω.</p>
      </Notice>
      {error && <Notice tone="error" live>{error}</Notice>}
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={() => navigate(`/courses/${id}`)}>
          <X aria-hidden="true" />
          Όχι, κράτα το
        </button>
        <button type="button" className="btn btn-danger" onClick={remove}>
          <Trash2 aria-hidden="true" />
          Ναι, σβήσ' το
        </button>
      </div>
    </Screen>
  );
}
