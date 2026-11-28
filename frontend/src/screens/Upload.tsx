import { useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, FileText, Upload } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { Notice } from "../components/common";
import type { Chapter } from "../types";

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
      // Straight to the sections: no "where do you want to start" question.
      const chapter = await api.upload<Chapter>(`/courses/${id}/documents`, form);
      navigate(`/chapters/${chapter.id}`, { replace: true });
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
            Το PDF διαβάζεται και χωρίζεται σε μικρές ενότητες...
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
