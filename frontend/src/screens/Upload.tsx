import { useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Check, FileText, Upload } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { LEVELS, Notice } from "../components/common";
import { LevelChoice } from "./Course";
import { useSettings } from "../settings";
import type { Chapter, Course, Upload as UploadResult } from "../types";
import { useLoad } from "../useLoad";

export function UploadScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Πρώτα διάλεξε ένα αρχείο PDF.");
      return;
    }
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api.upload<UploadResult>(`/courses/${id}/documents`, form);
      navigate(`/chapters/${result.document.id}/start`, { state: result });
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  };

  return (
    <Screen
      title="Ανέβασε το PDF του μαθήματος"
      back={`/courses/${id}`}
      listen={[{ text: "Ανέβασε το PDF του μαθήματος. Διάλεξε το αρχείο από τη συσκευή σου. Το αρχείο μένει μόνο σε αυτή τη συσκευή." }]}
    >
      <p>Διάλεξε το αρχείο PDF από τη συσκευή σου, για παράδειγμα από το eClass.</p>
      <p>Το αρχείο μένει μόνο σε αυτή τη συσκευή.</p>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <input
            ref={input}
            id="pdf"
            className="file-input"
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setError(null);
            }}
            aria-describedby={error ? "pdf-error" : undefined}
          />
          <label htmlFor="pdf" className="btn btn-file">
            <FileText aria-hidden="true" />
            {file ? "Διάλεξε άλλο PDF" : "Διάλεξε PDF"}
          </label>
          {file && (
            <p className="chosen-file" role="status">
              <Check aria-hidden="true" /> Διάλεξες: <strong>{file.name}</strong>
            </p>
          )}
        </div>
        {error && (
          <div id="pdf-error">
            <Notice tone="error" live>{error}</Notice>
          </div>
        )}
        {busy && (
          <p className="loading" role="status">
            Διαβάζω το PDF και το χωρίζω σε μικρές ενότητες...
          </p>
        )}
        <div className="actions">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            <Upload aria-hidden="true" />
            Ανέβασε
          </button>
        </div>
      </form>
    </Screen>
  );
}

/** After the upload: "Προτείνουμε να ξεκινήσεις από το επίπεδο 2". The student decides. */
export function StartLevel() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { settings } = useSettings();
  const upload = useLocation().state as UploadResult | null;
  const chapter = useLoad<Chapter>(upload ? null : `/documents/${id}`);
  const doc = upload?.document ?? chapter.data;
  const course = useLoad<Course>(doc ? `/courses/${doc.course_id}` : null);
  const suggested = upload?.suggestion.level ?? doc?.suggested_level ?? course.data?.level ?? 1;
  const [choosing, setChoosing] = useState(false);
  const [level, setLevel] = useState(suggested);
  const [error, setError] = useState<string | null>(null);

  const start = async (chosen: number) => {
    try {
      await api.post(`/documents/${id}/start-level`, { level: chosen, reason: "new_chapter" });
      navigate(`/chapters/${id}`, { replace: true });
    } catch (err) {
      setError(errorText(err));
    }
  };

  const sentence = `Προτείνουμε να ξεκινήσεις από το επίπεδο ${suggested}: ${LEVELS[suggested].name}.`;
  const reason = upload?.suggestion.reason ?? "";

  return (
    <Screen
      title="Από πού θέλεις να ξεκινήσεις;"
      back={doc ? `/courses/${doc.course_id}` : "/"}
      autoRead={settings.autoRead && !!doc}
      listen={[{ text: `${doc?.title ?? ""}. ${sentence} ${LEVELS[suggested].description} ${reason}` }]}
    >
      {doc && <p className="lead">{doc.title}</p>}
      <Notice tone="success" icon={Check}>
        <p>Το PDF είναι έτοιμο. Το χωρίσαμε σε {doc?.sections.length ?? "..."} μικρές ενότητες.</p>
      </Notice>
      <p className="lead">{sentence}</p>
      <p>{LEVELS[suggested].description}</p>
      {reason && <p>{reason}</p>}
      {error && <Notice tone="error" live>{error}</Notice>}
      {!choosing ? (
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => start(suggested)}>
            <Check aria-hidden="true" />
            Ναι, από το επίπεδο {suggested}
          </button>
          <button type="button" className="btn" onClick={() => { setLevel(suggested); setChoosing(true); }}>
            Θέλω να διαλέξω άλλο
          </button>
        </div>
      ) : (
        <>
          <LevelChoice value={level} onChange={setLevel} suggested={suggested} />
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => start(level)}>
              <Check aria-hidden="true" />
              Ξεκίνα από το επίπεδο {level}
            </button>
          </div>
        </>
      )}
    </Screen>
  );
}
