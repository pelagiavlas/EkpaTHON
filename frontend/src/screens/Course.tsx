import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { BookOpen, Check, ChevronRight, Circle, CircleCheck, FileText, Pencil, Trash2, Upload, X } from "lucide-react";
import { useClock } from "../demo";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { LEVELS, LevelSteps, Loading, Notice } from "../components/common";
import type { Chapter, Course, Plan } from "../types";
import { useLoad } from "../useLoad";

export function CourseScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const course = useLoad<Course>(`/courses/${id}`);
  const chapters = useLoad<Chapter[]>(`/courses/${id}/documents`);
  const c = course.data;

  return (
    <Screen title={c?.name ?? "Μάθημα"} back="/courses" listen={c ? [{ text: `${c.name}. ${c.chapters} κεφάλαια.` }] : undefined}>
      {course.error && <Notice tone="error" live>{course.error}</Notice>}
      {!c && !course.error && <Loading />}
      {c && (
        <>
          {c.from_eclass && <TeachingPlan courseId={c.id} />}
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
      navigate("/courses", { replace: true });
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

/** Where teaching is (from the student's answers, or the syllabus), what has been studied,
 *  and one suggested next step. The student can correct where teaching is. */
function TeachingPlan({ courseId }: { courseId: number }) {
  const navigate = useNavigate();
  const clock = useClock();
  const { data: plan, setData } = useLoad<Plan>(`/courses/${courseId}/plan?${clock.query}`);
  const [editing, setEditing] = useState(false);
  const [unit, setUnit] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!plan) return null;

  const save = async () => {
    if (unit === null) return;
    try {
      setData(await api.post<Plan>(`/courses/${courseId}/teaching?${clock.query}`, { unit_id: unit }));
      setEditing(false);
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  };

  return (
    <section className="panel" aria-labelledby="plan-title">
      <h2 id="plan-title">Πού είναι η διδασκαλία</h2>
      {plan.teaching ? (
        <p>
          <strong>Στο μάθημα:</strong> {plan.teaching.title} (εβδομάδα {plan.teaching.week}).{" "}
          {plan.teaching_from === "confirmed" ? "Από τις απαντήσεις σου." : "Από το πλάνο του μαθήματος."}
        </p>
      ) : (
        <p>Η διδασκαλία δεν έχει ξεκινήσει ακόμα.</p>
      )}
      {plan.with_material > 0 && <p><strong>Έχεις μελετήσει:</strong> {plan.studied} από {plan.with_material} ενότητες.</p>}
      {plan.next && (
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${plan.next!.section_id}`)}>
            <BookOpen aria-hidden="true" />
            {plan.next.text}
          </button>
        </div>
      )}
      <ul className="plan-units">
        {plan.units.map((u) => (
          <li key={u.unit_id}>
            {u.taught ? <CircleCheck aria-hidden="true" className="ok" /> : <Circle aria-hidden="true" />}
            <span className="plan-title">{u.title}</span>
            <span className="plan-status">
              {u.taught ? "Έγινε στο μάθημα" : `Εβδομάδα ${u.week}`}
              {u.studied && " · Το μελέτησες"}
            </span>
          </li>
        ))}
      </ul>
      {!editing ? (
        <button type="button" className="btn" onClick={() => { setUnit(plan.teaching?.unit_id ?? null); setEditing(true); }}>
          <Pencil aria-hidden="true" />
          Άλλαξε πού είναι η διδασκαλία
        </button>
      ) : (
        <>
          <fieldset className="field">
            <legend>Μέχρι ποια ενότητα έχει γίνει στο μάθημα;</legend>
            <div className="radio-cards">
              {plan.units.map((u) => (
                <label key={u.unit_id} className={`radio-card ${unit === u.unit_id ? "is-on" : ""}`}>
                  <input type="radio" name="teaching" checked={unit === u.unit_id} onChange={() => setUnit(u.unit_id)} />
                  <span>{u.title}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && <Notice tone="error" live>{error}</Notice>}
          <div className="actions actions-row">
            <button type="button" className="btn btn-primary" onClick={save} disabled={unit === null}>
              <Check aria-hidden="true" />
              Αποθήκευση
            </button>
            <button type="button" className="btn" onClick={() => setEditing(false)}>
              <X aria-hidden="true" />
              Άκυρο
            </button>
          </div>
        </>
      )}
    </section>
  );
}
