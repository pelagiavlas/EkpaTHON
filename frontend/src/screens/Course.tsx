import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, ChevronRight, FileText, Sparkles, Trash2, Upload, X } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { LEVELS, LevelSteps, Loading, Notice } from "../components/common";
import type { Chapter, Course } from "../types";
import { useLoad } from "../useLoad";

/** "Θες λιγότερη/περισσότερη βοήθεια;": the app proposes, the student decides. */
export function ProposalCard({ course, onDone }: { course: Course; onDone: (c: Course) => void }) {
  const [error, setError] = useState<string | null>(null);
  const proposal = course.proposal!;
  const decide = async (yes: boolean) => {
    try {
      const updated = yes
        ? await api.post<Course>(`/courses/${course.id}/level`, { level: proposal.to_level, reason: "proposal" })
        : await api.post<Course>(`/courses/${course.id}/proposal/decline`);
      onDone(updated);
    } catch (err) {
      setError(errorText(err));
    }
  };
  return (
    <section className="proposal" aria-labelledby="proposal-title">
      <h2 id="proposal-title">
        <Sparkles aria-hidden="true" />
        Μια πρόταση για σένα
      </h2>
      <p>{proposal.message}</p>
      <p>
        Από το επίπεδο {proposal.from_level} πας στο επίπεδο {proposal.to_level}: {LEVELS[proposal.to_level].name}.
        Μπορείς να το αλλάξεις ξανά όποτε θέλεις.
      </p>
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

export function CourseScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const course = useLoad<Course>(`/courses/${id}`);
  const chapters = useLoad<Chapter[]>(`/courses/${id}/documents`);
  const c = course.data;

  return (
    <Screen
      title={c?.name ?? "Μάθημα"}
      back="/"
      listen={c ? [{ text: `${c.name}. Επίπεδο ${c.level} από 4: ${c.level_name}. ${LEVELS[c.level].description}` }] : undefined}
    >
      {course.error && <Notice tone="error" live>{course.error}</Notice>}
      {!c && !course.error && <Loading />}
      {c && (
        <>
          {c.proposal && <ProposalCard course={c} onDone={course.setData} />}
          <section aria-labelledby="level-title" className="panel">
            <h2 id="level-title">Επίπεδο βοήθειας</h2>
            <LevelSteps level={c.level} />
            <Link className="text-link" to={`/courses/${c.id}/level`}>
              Άλλαξε επίπεδο
            </Link>
          </section>
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

export function LevelChoice({ value, onChange, suggested }: { value: number; onChange: (n: number) => void; suggested?: number }) {
  return (
    <fieldset className="field">
      <legend>Διάλεξε επίπεδο βοήθειας</legend>
      <div className="radio-cards">
        {[1, 2, 3, 4].map((n) => (
          <label key={n} className={`radio-card ${value === n ? "is-on" : ""}`}>
            <input type="radio" name="level" value={n} checked={value === n} onChange={() => onChange(n)} />
            <span>
              <LevelSteps level={n} compact />
              <span className="level-desc">{LEVELS[n].description}</span>
              {suggested === n && <span className="badge">Η πρότασή μας</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function ChangeLevel() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: course } = useLoad<Course>(`/courses/${id}`);
  const [level, setLevel] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chosen = level ?? course?.level ?? 1;

  const save = async () => {
    try {
      await api.post(`/courses/${id}/level`, { level: chosen, reason: "manual" });
      navigate(`/courses/${id}`);
    } catch (err) {
      setError(errorText(err));
    }
  };

  return (
    <Screen title="Άλλαξε επίπεδο βοήθειας" back={`/courses/${id}`}>
      <p>Το επίπεδο αλλάζει μόνο για το μάθημα «{course?.name}». Μπορείς να το αλλάξεις όποτε θέλεις.</p>
      {course && <LevelChoice value={chosen} onChange={setLevel} />}
      {error && <Notice tone="error" live>{error}</Notice>}
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={save} disabled={!course}>
          <Check aria-hidden="true" />
          Αποθήκευση
        </button>
      </div>
    </Screen>
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
