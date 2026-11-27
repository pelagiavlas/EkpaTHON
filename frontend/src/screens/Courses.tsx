import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, Plus, Save } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { COURSE_ICONS, CourseIcon, LevelSteps, Loading, Notice } from "../components/common";
import { useSettings } from "../settings";
import type { Course } from "../types";
import { useLoad } from "../useLoad";

export function Courses() {
  const { data: courses, error } = useLoad<Course[]>("/courses");
  const { settings } = useSettings();
  const navigate = useNavigate();

  const listen = [
    { text: "Τα μαθήματά μου." },
    ...(courses ?? []).map((c) => ({ text: `${c.name}. Επίπεδο ${c.level} από 4: ${c.level_name}.` })),
  ];

  return (
    <Screen title="Τα μαθήματά μου" listen={listen} autoRead={settings.autoRead && !!courses}>
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
                  <LevelSteps level={c.level} compact />
                  {c.proposal && <span className="badge">Έχεις μια πρόταση</span>}
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
    <Screen title="Νέο μάθημα" back="/">
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
