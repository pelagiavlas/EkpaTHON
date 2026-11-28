import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronRight, CircleCheck, Pause, Play, Send, Square, Timer, Users } from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { Loading, Notice } from "../components/common";
import { MilestoneNotes } from "../components/Support";
import type { AnswerResult, Milestone, Questions } from "../types";
import { useLoad } from "../useLoad";

/** "Εξάσκηση σαν στις εξετάσεις" (level 4): no help, no timer unless the student turns one on.
 *  The timer can be paused or stopped and never ends the practice (WCAG 2.2.1). */
export function ExamScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const set = useLoad<Questions>(`/sections/${id}/questions?exam=true`);
  const [started, setStarted] = useState(false);
  const [useTimer, setUseTimer] = useState(false);
  const [minutes, setMinutes] = useState(10);
  const [index, setIndex] = useState(0);
  const [done, setDone] = useState(false);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const back = `/sections/${id}`;

  if (set.error) {
    return <Screen title="Εξάσκηση" back={back}><Notice tone="calm" live>{set.error}</Notice></Screen>;
  }
  if (!set.data) {
    return <Screen title="Εξάσκηση" back={back}><Loading /></Screen>;
  }
  const questions = set.data.questions;

  if (!started) {
    return (
      <Screen title="Εξάσκηση σαν στις εξετάσεις" back={back}>
        <p>Απαντάς σε {questions.length} ερωτήσεις με δικά σου λόγια, χωρίς βοήθεια. Μετά από κάθε απάντηση βλέπεις το βασικό σημείο.</p>
        <p>Η εξάσκηση δεν αλλάζει τον τρόπο μελέτης.</p>
        <fieldset className="field">
          <legend>Θέλεις χρονόμετρο;</legend>
          <div className="radio-cards">
            {[false, true].map((v) => (
              <label key={String(v)} className={`radio-card ${useTimer === v ? "is-on" : ""}`}>
                <input type="radio" name="timer" checked={useTimer === v} onChange={() => setUseTimer(v)} />
                <span>{v ? "Ναι, θέλω χρονόμετρο" : "Όχι, χωρίς χρονόμετρο"}</span>
              </label>
            ))}
          </div>
        </fieldset>
        {useTimer && (
          <div className="field">
            <label htmlFor="minutes">Πόσα λεπτά;</label>
            <select id="minutes" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
              {[5, 10, 15, 20, 30].map((m) => <option key={m} value={m}>{m} λεπτά</option>)}
            </select>
            <p>Όταν τελειώσει ο χρόνος, μπορείς να συνεχίσεις όσο θέλεις.</p>
          </div>
        )}
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => setStarted(true)}>
            <Play aria-hidden="true" />
            Ξεκίνα
          </button>
        </div>
      </Screen>
    );
  }

  if (done) {
    return (
      <Screen title="Τέλος εξάσκησης" back={back} listen={[{ text: `Τελείωσες την εξάσκηση. Απάντησες σε ${questions.length} ερωτήσεις.` }]}>
        <Notice tone="success" icon={CircleCheck}><p>Τελείωσες την εξάσκηση. Απάντησες σε {questions.length} ερωτήσεις.</p></Notice>
        <MilestoneNotes items={milestones} />
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => navigate(back)}>
            <ChevronRight aria-hidden="true" />
            Πίσω στην ενότητα
          </button>
        </div>
      </Screen>
    );
  }

  return (
    <Screen title={`Εξάσκηση: ερώτηση ${index + 1} από ${questions.length}`} back={back}
      listen={[{ text: questions[index].prompt }]}>
      {useTimer && <ExamTimer minutes={minutes} />}
      <ExamQuestion
        key={questions[index].id}
        questionId={questions[index].id}
        prompt={questions[index].prompt}
        last={index + 1 === questions.length}
        onMilestones={(m) => setMilestones((all) => [...all, ...m])}
        onNext={() => (index + 1 < questions.length ? setIndex(index + 1) : setDone(true))}
      />
    </Screen>
  );
}

function ExamQuestion({ questionId, prompt, last, onNext, onMilestones }: {
  questionId: number;
  prompt: string;
  last: boolean;
  onNext: () => void;
  onMilestones: (m: Milestone[]) => void;
}) {
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const feedback = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api.post<{ attempt_id: number }>(`/questions/${questionId}/attempts?exam=true`).then((r) => setAttemptId(r.attempt_id));
  }, [questionId]);

  useEffect(() => {
    if (result) feedback.current?.focus();
  }, [result]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!attemptId) return;
    if (!text.trim()) {
      setError("Γράψε την απάντησή σου.");
      return;
    }
    try {
      const r = await api.post<AnswerResult>(`/attempts/${attemptId}/answer`, { text });
      setResult(r);
      onMilestones(r.new_milestones);
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const selfCheck = async (close: boolean) => {
    const r = await api.post<AnswerResult>(`/attempts/${attemptId}/self-check`, { close });
    setResult(r);
    onMilestones(r.new_milestones);
  };

  return (
    <>
      <h2 className="question-prompt">{prompt}</h2>
      {!result?.done && result?.outcome !== "self_check" && (
        <form onSubmit={submit} noValidate className="field">
          <label htmlFor="exam-answer">Η απάντησή σου</label>
          <textarea id="exam-answer" rows={4} value={text} onChange={(e) => setText(e.target.value)}
            aria-describedby={error ? "exam-error" : undefined} />
          {error && <p id="exam-error" className="field-error" role="alert">{error}</p>}
          <button type="submit" className="btn btn-primary"><Send aria-hidden="true" />Στείλε την απάντηση</button>
        </form>
      )}
      {result && (
        <div ref={feedback} tabIndex={-1} className="feedback">
          <Notice tone={result.outcome === "correct" ? "success" : "calm"} icon={result.outcome === "correct" ? CircleCheck : Users}>
            <p className="feedback-message">{result.message}</p>
            {result.key_point && <p>{result.key_point}</p>}
          </Notice>
          {result.outcome === "self_check" ? (
            <div className="actions actions-row">
              <button type="button" className="btn btn-primary" onClick={() => selfCheck(true)}>Ναι, είναι κοντά</button>
              <button type="button" className="btn" onClick={() => selfCheck(false)}>Όχι ακόμα</button>
            </div>
          ) : (
            <div className="actions">
              <button type="button" className="btn btn-primary" onClick={onNext}>
                <ChevronRight aria-hidden="true" />
                {last ? "Τέλος" : "Επόμενη ερώτηση"}
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/** Optional countdown chosen by the student: pause, stop, and nothing happens when it reaches 0. */
function ExamTimer({ minutes }: { minutes: number }) {
  const [left, setLeft] = useState(minutes * 60);
  const [running, setRunning] = useState(true);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!running || left <= 0) return;
    const t = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [running, left]);

  if (!visible) return null;
  const mm = Math.floor(left / 60);
  const ss = String(left % 60).padStart(2, "0");
  return (
    <div className="panel timer">
      <p className="with-icon">
        <Timer aria-hidden="true" />
        {/* role="timer" is not announced every second; the end is announced once below. */}
        <span role="timer" aria-label={`Χρόνος που μένει: ${mm} λεπτά`}>{mm}:{ss}</span>
      </p>
      {left === 0 && (
        <p role="status">Ο χρόνος τελείωσε. Μπορείς να συνεχίσεις όσο θέλεις.</p>
      )}
      <div className="actions actions-row">
        {left > 0 && (
          <button type="button" className="btn" onClick={() => setRunning(!running)}>
            {running ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
            {running ? "Πάγωσε" : "Συνέχισε"}
          </button>
        )}
        <button type="button" className="btn" onClick={() => setVisible(false)}>
          <Square aria-hidden="true" />
          Χωρίς χρονόμετρο
        </button>
      </div>
    </div>
  );
}
