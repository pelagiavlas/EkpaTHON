import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, ChevronRight, Info, Plus, Save, Settings as SettingsIcon } from "lucide-react";
import { useClock } from "../demo";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { COURSE_ICONS, CourseIcon, Loading, Notice } from "../components/common";
import { useSettings } from "../settings";
import type { Course } from "../types";
import { useLoad } from "../useLoad";

/** One quiet tip on first use instead of a questionnaire. Closes with one tap. */
function FirstTip() {
  const { settings, loaded, update } = useSettings();
  if (!loaded || settings.onboarded) return null;
  return (
    <Notice icon={SettingsIcon}>
      <p>
        Μπορείς να αλλάξεις γράμματα, χρώματα και ήχο όποτε θέλεις, στις <Link to="/settings">Ρυθμίσεις</Link>.
      </p>
      <button type="button" className="btn" onClick={() => update({ onboarded: true })}>
        <Check aria-hidden="true" />
        Εντάξει
      </button>
    </Notice>
  );
}

export function Courses() {
  const clock = useClock();
  const { data: courses, error } = useLoad<Course[]>(`/courses?${clock.query}`);
  const { settings } = useSettings();
  const navigate = useNavigate();

  const listen = [{ text: "Τα μαθήματά μου." }, ...(courses ?? []).map((c) => ({ text: `${c.name}.` }))];

  return (
    <Screen title="Τα μαθήματά μου" back="/" listen={listen} autoRead={settings.autoRead && !!courses}>
      <FirstTip />
      {courses?.some((c) => c.from_eclass) && (
        <Notice icon={Info}><p><strong>Προσομοιωμένα δεδομένα eClass.</strong> Τα μαθήματα έρχονται από το eClass του ΕΚΠΑ.</p></Notice>
      )}
      {error && <Notice tone="error" live>{error}</Notice>}
      {!courses && !error && <Loading />}
      {courses?.length === 0 && <p className="lead">Δεν έχεις ακόμα μαθήματα. Πρόσθεσε το πρώτο σου μάθημα.</p>}
      {courses && courses.length > 0 && (
        <ul className="cards">
          {courses.map((c) => (
            <li key={c.id}>
              <Link className="card card-link" to={`/courses/${c.id}`}>
                <CourseIcon name={c.icon} />
                <span className="card-body">
                  <span className="card-title">{c.name}</span>
                  {c.teaching && <span><strong>Στο μάθημα:</strong> {c.teaching}</span>}
                  {c.with_material > 0
                    ? <span><strong>Έχεις μελετήσει:</strong> {c.studied} από {c.with_material} ενότητες</span>
                    : <span>{c.chapters === 1 ? "1 κεφάλαιο" : `${c.chapters} κεφάλαια`}</span>}
                  {c.next_text && <span className="next-step">{c.next_text}</span>}
                  {c.proposals > 0 && <span className="badge">Έχεις πρόταση</span>}
                </span>
                <ChevronRight aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={() => navigate("/courses/new")}>
          <Plus aria-hidden="true" />
          Νέο μάθημα
        </button>
      </div>
    </Screen>
  );
}

export function NewCourse() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [icon, setIcon] = useState("book");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Γράψε το όνομα του μαθήματος.");
      return;
    }
    setSaving(true);
    try {
      const course = await api.post<Course>("/courses", { name: name.trim(), icon });
      navigate(`/courses/${course.id}`, { replace: true });
    } catch (err) {
      setError(errorText(err));
      setSaving(false);
    }
  };

  return (
    <Screen title="Νέο μάθημα" back="/courses">
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="course-name">Πώς λέγεται το μάθημα;</label>
          <input
            id="course-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="off"
            aria-invalid={!!error}
            aria-describedby={error ? "course-error" : undefined}
          />
          {error && (
            <p id="course-error" className="field-error" role="alert">
              {error}
            </p>
          )}
        </div>
        <fieldset className="field">
          <legend>Διάλεξε μια εικόνα για το μάθημα</legend>
          <div className="icon-grid">
            {Object.entries(COURSE_ICONS).map(([key, { icon: Icon, label }]) => (
              <label key={key} className="icon-option">
                <input type="radio" name="icon" value={key} checked={icon === key} onChange={() => setIcon(key)} />
                <Icon aria-hidden="true" />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            <Save aria-hidden="true" />
            {saving ? "Αποθηκεύεται..." : "Αποθήκευση"}
          </button>
        </div>
      </form>
    </Screen>
  );
}
