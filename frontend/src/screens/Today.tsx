import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen, CalendarClock, Check, CircleCheck, CircleHelp, Clock, FilePlus2, Info, ListChecks, Sun, X, type LucideIcon,
} from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { Loading, Notice } from "../components/common";
import { useClock, type Moment } from "../demo";
import { useSettings } from "../settings";
import type { ConfirmResult, Today } from "../types";
import { useLoad } from "../useLoad";

const dateFmt = new Intl.DateTimeFormat("el-GR", { weekday: "long", day: "numeric", month: "long" });

/** "Σήμερα": the first screen. Cards always in the same order; a card without content is simply not shown.
 *  Everything is an offer ("Θες να...;"), never "πρέπει", and nothing marks what did not happen. */
export function TodayScreen() {
  const clock = useClock();
  const { settings } = useSettings();
  const { data, error, reload } = useLoad<Today>(`/today?${clock.query}`);

  const listen = data ? speechFor(data) : undefined;

  return (
    <Screen title="Σήμερα" listen={listen} autoRead={settings.autoRead && !!data}>
      {error && <Notice tone="error" live>{error}</Notice>}
      {!data && !error && <Loading />}
      {data && (
        <>
          <p className="step-count">{capitalize(dateFmt.format(new Date(data.now)))}</p>
          {data.simulated_eclass && (
            <Notice icon={Info}>
              <p><strong>Προσομοιωμένα δεδομένα eClass.</strong> Τα μαθήματα, το πρόγραμμα και τα έγγραφα είναι για την παρουσίαση.</p>
            </Notice>
          )}
          {data.demo && <DemoClock value={clock.moment} onChange={clock.setMoment} />}

          <NextClassCard data={data} />
          <BeforeCard data={data} />
          <AfterCard data={data} query={clock.query} onSaved={reload} />
          <NewMaterialCard data={data} />

          {!data.next_class && !data.before && !data.after && data.new_material.length === 0 && (
            <p className="lead">Για σήμερα δεν υπάρχει κάτι καινούργιο. Μπορείς να συνεχίσεις από τα μαθήματά σου όποτε θέλεις.</p>
          )}
        </>
      )}
    </Screen>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function speechFor(d: Today) {
  const parts = [{ text: `Σήμερα. ${dateFmt.format(new Date(d.now))}.` }];
  const c = d.next_class;
  if (c) parts.push({ text: `Επόμενο μάθημα: ${c.course_name}, ${c.is_today ? "σήμερα" : c.weekday}, ${c.start} μέχρι ${c.end}, ${c.room}.` });
  if (d.before) parts.push({ text: `Σήμερα προβλέπεται η ενότητα ${d.before.unit_title}.` });
  if (d.after) parts.push({ text: `${d.after.when} κάνατε την ενότητα ${d.after.predicted?.title ?? ""};` });
  if (d.new_material.length) parts.push({ text: `Νέο υλικό: ${d.new_material.map((m) => m.title).join(", ")}.` });
  return parts;
}

function Card({ id, icon: Icon, title, children }: { id: string; icon: LucideIcon; title: string; children: ReactNode }) {
  return (
    <section className="today-card" aria-labelledby={id}>
      <h2 id={id} className="with-icon">
        <Icon aria-hidden="true" />
        {title}
      </h2>
      {children}
    </section>
  );
}

function DemoClock({ value, onChange }: { value: Moment; onChange: (m: Moment) => void }) {
  return (
    <div className="panel preview-panel">
      <p className="with-icon"><Clock aria-hidden="true" /><strong>Ώρα για την παρουσίαση</strong></p>
      <div className="toggle" role="group" aria-label="Ώρα για την παρουσίαση">
        <button type="button" className="btn btn-toggle" aria-pressed={value === "before"} onClick={() => onChange("before")}>
          Πριν το μάθημα (09:30)
        </button>
        <button type="button" className="btn btn-toggle" aria-pressed={value === "after"} onClick={() => onChange("after")}>
          Μετά το μάθημα (13:00)
        </button>
      </div>
    </div>
  );
}

function NextClassCard({ data }: { data: Today }) {
  const navigate = useNavigate();
  const c = data.next_class;
  if (!c) return null;
  const when = c.phase === "during" ? `Τώρα, μέχρι τις ${c.end}` : `${c.is_today ? "Σήμερα" : c.weekday}, ${c.start}–${c.end}`;
  return (
    <Card id="card-next" icon={CalendarClock} title="Επόμενο μάθημα">
      <p className="card-big">{c.course_name}</p>
      <p>{when}</p>
      <p>{c.room}</p>
      <div className="actions">
        <button type="button" className="btn" onClick={() => navigate(`/courses/${c.course_id}`)}>
          <BookOpen aria-hidden="true" />
          Δες το μάθημα
        </button>
      </div>
    </Card>
  );
}

function BeforeCard({ data }: { data: Today }) {
  const navigate = useNavigate();
  const b = data.before;
  if (!b) return null;
  return (
    <Card id="card-before" icon={Sun} title="Πριν το μάθημα">
      <p>Σήμερα προβλέπεται η ενότητα <strong>{b.unit_title}</strong>.</p>
      {b.section_id ? (
        <>
          <p>Θες μια σύντομη ματιά, σε Εύκολο κείμενο; Περίπου {b.minutes} {b.minutes === 1 ? "λεπτό" : "λεπτά"}.</p>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${b.section_id}`)}>
              <BookOpen aria-hidden="true" />
              Ναι, δείξε μου
            </button>
          </div>
        </>
      ) : (
        <p>Το υλικό αυτής της ενότητας δεν έχει ανέβει ακόμα στο eClass.</p>
      )}
    </Card>
  );
}

function AfterCard({ data, query, onSaved }: { data: Today; query: string; onSaved: () => void }) {
  const navigate = useNavigate();
  const a = data.after;
  const [choosing, setChoosing] = useState(false);
  const [unit, setUnit] = useState<number | null>(null);
  const [result, setResult] = useState<ConfirmResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!a && !result) return null;

  const send = async (status: "done" | "unknown", unitId?: number) => {
    if (!a) return;
    try {
      setResult(await api.post<ConfirmResult>(`/classes/confirm?${query}`, {
        course_id: a.course_id, class_date: a.class_date, unit_id: unitId ?? null, status,
      }));
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  };

  if (result) {
    return (
      <Card id="card-after" icon={ListChecks} title="Μετά το μάθημα">
        {result.status === "done" ? (
          <>
            <Notice tone="success" icon={CircleCheck} live><p>Αποθηκεύτηκε: {result.unit_title}.</p></Notice>
            {result.section_id && result.has_questions && (
              <>
                <p>Θες 2 ερωτήσεις για να δεις τι κράτησες;</p>
                <div className="actions actions-row">
                  <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${result.section_id}/questions?limit=2`)}>
                    <CircleHelp aria-hidden="true" />
                    Ναι, 2 ερωτήσεις
                  </button>
                  <button type="button" className="btn" onClick={() => { setResult(null); onSaved(); }}>
                    <X aria-hidden="true" />
                    Όχι τώρα
                  </button>
                </div>
              </>
            )}
          </>
        ) : (
          <Notice icon={Info} live><p>Εντάξει. Θα το δεις ξανά άλλη μέρα.</p></Notice>
        )}
      </Card>
    );
  }
  if (!a) return null;

  const question = a.predicted
    ? <>{a.when} κάνατε την ενότητα <strong>{a.predicted.title}</strong> στο μάθημα «{a.course_name}»;</>
    : <>Ποια ενότητα κάνατε {a.when.toLowerCase()} στο μάθημα «{a.course_name}»;</>;

  return (
    <Card id="card-after" icon={ListChecks} title="Μετά το μάθημα">
      <p>{question}</p>
      {error && <Notice tone="error" live>{error}</Notice>}
      {!choosing && a.predicted ? (
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => send("done", a.predicted!.unit_id)}>
            <Check aria-hidden="true" />
            Ναι
          </button>
          <button type="button" className="btn" onClick={() => setChoosing(true)}>
            Όχι, κάναμε άλλη
          </button>
          <button type="button" className="btn" onClick={() => send("unknown")}>
            Δεν ξέρω
          </button>
        </div>
      ) : (
        <>
          <fieldset className="field">
            <legend>Ποια ενότητα κάνατε;</legend>
            <div className="radio-cards">
              {a.units.map((u) => (
                <label key={u.unit_id} className={`radio-card ${unit === u.unit_id ? "is-on" : ""}`}>
                  <input type="radio" name="unit" checked={unit === u.unit_id} onChange={() => setUnit(u.unit_id)} />
                  <span>{u.title}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="actions">
            <button type="button" className="btn btn-primary" disabled={unit === null} onClick={() => unit !== null && send("done", unit)}>
              <Check aria-hidden="true" />
              Αποθήκευση
            </button>
            <button type="button" className="btn" onClick={() => send("unknown")}>
              Δεν ξέρω
            </button>
          </div>
        </>
      )}
    </Card>
  );
}

function NewMaterialCard({ data }: { data: Today }) {
  const navigate = useNavigate();
  if (!data.new_material.length) return null;
  return (
    <Card id="card-new" icon={FilePlus2} title="Νέο υλικό">
      <p>Ο διδάσκων πρόσθεσε στο eClass:</p>
      <ul className="cards">
        {data.new_material.map((m) => (
          <li key={m.document_id}>
            <button type="button" className="card card-link card-button" onClick={() => navigate(`/chapters/${m.document_id}`)}>
              <FilePlus2 aria-hidden="true" className="course-icon" />
              <span className="card-body">
                <span className="card-title">{m.title}</span>
                <span>{m.course_name}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p>Είναι ήδη χωρισμένο σε μικρές ενότητες. Θες να ρίξεις μια ματιά;</p>
    </Card>
  );
}
