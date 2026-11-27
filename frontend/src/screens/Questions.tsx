import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  BookOpen, ChartColumn, ChevronRight, CircleCheck, HandHelping, Image as ImageIcon, Lightbulb, Send, Users,
  Volume2, X,
} from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { EasyBlocks, blockSpeech, visibleBlocks } from "../components/Blocks";
import { Loading, Notice, Pictogram } from "../components/common";
import { ProposalCard } from "./Course";
import { useSettings } from "../settings";
import { useSpeech } from "../speech";
import type { AnswerResult, Course, Hint, Option, Question, Questions, Study } from "../types";
import { useLoad } from "../useLoad";

type Phase = "intro" | "question" | "proposal" | "strategy" | "done";

export function QuestionsScreen() {
  const { id } = useParams();
  return <QuestionsFlow key={id} sectionId={id!} />;
}

function QuestionsFlow({ sectionId }: { sectionId: string }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const speech = useSpeech();
  const set = useLoad<Questions>(`/sections/${sectionId}/questions`);
  const study = useLoad<Study>(`/sections/${sectionId}/study`);
  const [phase, setPhase] = useState<Phase | null>(null);
  const [index, setIndex] = useState(0);
  const [proposalCourse, setProposalCourse] = useState<Course | null>(null);
  const [showSection, setShowSection] = useState(false);

  const data = set.data;
  useEffect(() => {
    if (data && phase === null) setPhase(data.last_strategy ? "intro" : data.questions.length ? "question" : "done");
  }, [data, phase]);

  const nextQuestion = async (result: AnswerResult) => {
    if (result.proposal && data) {
      const course = await api.get<Course>(`/courses/${data.course_id}`).catch(() => null);
      if (course?.proposal) {
        setProposalCourse(course);
        setPhase("proposal");
        return;
      }
    }
    advance();
  };

  const advance = () => {
    if (!data) return;
    if (index + 1 < data.questions.length) {
      setIndex(index + 1);
      setPhase("question");
    } else {
      setPhase(data.ask_strategy ? "strategy" : "done");
    }
  };

  const back = `/sections/${sectionId}`;
  const sectionView = study.data && (
    <section className="panel inline-section" aria-label="Η ενότητα">
      <h2>{study.data.title}</h2>
      <EasyBlocks blocks={visibleBlocks(study.data.easy.blocks, study.data.level)} glossary={study.data.easy.glossary} idPrefix="s" />
      <button type="button" className="btn" onClick={() => setShowSection(false)}>
        <X aria-hidden="true" />
        Κλείσε την ενότητα
      </button>
    </section>
  );

  if (set.error) {
    return (
      <Screen title="Ερωτήσεις" back={back}>
        <Notice tone="error" live>{set.error}</Notice>
      </Screen>
    );
  }
  if (!data || phase === null) {
    return (
      <Screen title="Ερωτήσεις" back={back}>
        <Loading />
      </Screen>
    );
  }

  if (phase === "intro" && data.last_strategy) {
    const strategy = data.last_strategy;
    const useIt = () => {
      if (strategy.choice === "listen" && study.data) {
        speech.speak(blockSpeech(visibleBlocks(study.data.easy.blocks, study.data.level), study.data.easy.glossary, "s"));
      }
      setShowSection(true);
    };
    return (
      <Screen title="Πριν τις ερωτήσεις" back={back}
        listen={[{ text: `Την προηγούμενη φορά σε βοήθησε: ${strategy.label}. Θες να το χρησιμοποιήσεις και τώρα;` }]}>
        <p className="lead">Την προηγούμενη φορά σε βοήθησε: <strong>{strategy.label}</strong>.</p>
        <p>Θες να το χρησιμοποιήσεις και τώρα;</p>
        {showSection && sectionView}
        <div className="actions">
          {!showSection && (
            <button type="button" className="btn btn-primary" onClick={useIt}>
              <BookOpen aria-hidden="true" />
              Ναι, δείξε μου την ενότητα
            </button>
          )}
          <button type="button" className={`btn ${showSection ? "btn-primary" : ""}`} onClick={() => { setShowSection(false); setPhase(data.questions.length ? "question" : "done"); }}>
            <ChevronRight aria-hidden="true" />
            Πάμε στις ερωτήσεις
          </button>
        </div>
      </Screen>
    );
  }

  if (phase === "proposal" && proposalCourse) {
    return (
      <Screen title="Μια πρόταση" back={back} autoRead={settings.autoRead}
        listen={[{ text: proposalCourse.proposal?.message ?? "" }]}>
        <ProposalCard course={proposalCourse} onDone={() => advance()} />
        <p>Η αλλαγή ισχύει από την επόμενη ενότητα.</p>
      </Screen>
    );
  }

  if (phase === "strategy") {
    return <StrategyQuestion courseId={data.course_id} back={back} onDone={() => setPhase("done")} />;
  }

  if (phase === "done") {
    const next = study.data?.next_id;
    return (
      <Screen title="Τέλος ερωτήσεων" back={back} autoRead={settings.autoRead}
        listen={[{ text: data.questions.length ? "Τελείωσες τις ερωτήσεις αυτής της ενότητας." : "Για αυτή την ενότητα δεν έχουμε ερωτήσεις." }]}>
        <Notice tone="success" icon={CircleCheck}>
          <p>{data.questions.length ? "Τελείωσες τις ερωτήσεις αυτής της ενότητας." : "Για αυτή την ενότητα δεν έχουμε ερωτήσεις."}</p>
        </Notice>
        <div className="actions">
          {next ? (
            <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${next}`)}>
              <ChevronRight aria-hidden="true" />
              Επόμενη ενότητα
            </button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => navigate(study.data ? `/chapters/${study.data.document_id}` : "/")}>
              <BookOpen aria-hidden="true" />
              Πίσω στο κεφάλαιο
            </button>
          )}
          <button type="button" className="btn" onClick={() => navigate("/progress")}>
            <ChartColumn aria-hidden="true" />
            Δες την πρόοδό σου
          </button>
        </div>
      </Screen>
    );
  }

  const question = data.questions[index];
  return (
    <OneQuestion
      key={question.id}
      question={question}
      number={index + 1}
      total={data.questions.length}
      level={data.level}
      back={back}
      sectionView={sectionView}
      showSection={showSection}
      setShowSection={setShowSection}
      onNext={nextQuestion}
    />
  );
}

function OneQuestion(props: {
  question: Question;
  number: number;
  total: number;
  level: number;
  back: string;
  sectionView: ReactNode;
  showSection: boolean;
  setShowSection: (v: boolean) => void;
  onNext: (result: AnswerResult) => void;
}) {
  const { question, number, total, level, back, sectionView, showSection, setShowSection, onNext } = props;
  const { settings } = useSettings();
  const speech = useSpeech();
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [hints, setHints] = useState<Hint[]>([]);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [tried, setTried] = useState<number[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // React StrictMode runs effects twice in development
    started.current = true;
    api.post<{ attempt_id: number }>(`/questions/${question.id}/attempts`)
      .then((r) => setAttemptId(r.attempt_id))
      .catch((err) => setError(errorText(err)));
  }, [question.id]);

  useEffect(() => {
    if (result) feedback.current?.focus();
  }, [result]);

  const twoChoices = hints.find((h) => h.step === 3)?.choices ?? [];
  const options: Option[] = question.mode === "choice" && twoChoices.length ? twoChoices : question.options;
  const finished = result?.done === true;
  const hintsLeft = 4 - hints.length;

  const ask = async () => {
    if (!attemptId) return;
    try {
      const hint = await api.post<Hint>(`/attempts/${attemptId}/hint`);
      setHints((h) => [...h, hint]);
      setError(null);
      if (speech.enabled && settings.autoRead) speech.speak(`Υπόδειξη ${hint.step}. ${hint.text}`);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const send = async (body: { option_id?: number; text?: string }) => {
    if (!attemptId || finished) return;
    try {
      const r = await api.post<AnswerResult>(`/attempts/${attemptId}/answer`, body);
      if (r.outcome === "try_again" && body.option_id !== undefined) setTried((t) => [...t, body.option_id!]);
      setResult(r);
      setError(null);
      if (speech.enabled && settings.autoRead) speech.speak([{ text: r.message }, ...(r.done && r.key_point ? [{ text: r.key_point }] : [])]);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const submitText = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setError("Γράψε την απάντησή σου ή πάτησε «Βοήθεια».");
      return;
    }
    send({ text });
  };

  const selfCheck = async (close: boolean) => {
    if (!attemptId) return;
    setResult(await api.post<AnswerResult>(`/attempts/${attemptId}/self-check`, { close }));
  };

  const explain = async () => {
    if (!attemptId) return;
    setResult(await api.post<AnswerResult>(`/attempts/${attemptId}/explain`));
  };

  const listen = [
    { text: `Ερώτηση ${number} από ${total}. ${question.prompt}` },
    ...(question.mode === "choice" || twoChoices.length
      ? [{ text: `Οι επιλογές είναι: ${options.map((o) => o.text).join(". ")}.` }]
      : [{ text: "Γράψε την απάντησή σου με δικά σου λόγια." }]),
    ...hints.map((h) => ({ text: `Υπόδειξη ${h.step}. ${h.text}` })),
    ...(result ? [{ text: result.message }] : []),
  ];

  const openSection = () => {
    setShowSection(true);
    if (attemptId) api.post(`/attempts/${attemptId}/flags`, { opened_section: true }).catch(() => undefined);
  };

  const showChoices = question.mode === "choice" || twoChoices.length > 0;

  return (
    <Screen title={`Ερώτηση ${number} από ${total}`} back={back} listen={listen}
      autoRead={settings.autoRead && level <= 2}>
      <h2 className="question-prompt">{question.prompt}</h2>
      {question.image && <Pictogram name={question.image} alt={question.image_alt ?? ""} />}

      {showChoices && (
        <div className="answer-options" role="group" aria-label="Επιλογές απάντησης">
          {question.mode === "open" && <p>Γράψε την απάντηση ή διάλεξε μία από αυτές:</p>}
          {options.map((o) => {
            const wasTried = tried.includes(o.id);
            return (
              <button key={o.id} type="button" className={`btn btn-option ${wasTried ? "is-tried" : ""}`}
                aria-disabled={finished || wasTried} onClick={() => !wasTried && send({ option_id: o.id })}>
                {o.image && <img src={`/pictos/${o.image}.svg`} alt="" className="option-picto" />}
                <span>{o.text}</span>
                {wasTried && <span className="tried-note">Το δοκίμασες</span>}
              </button>
            );
          })}
        </div>
      )}

      {question.mode === "open" && !finished && result?.outcome !== "self_check" && (
        <form onSubmit={submitText} noValidate className="field">
          <label htmlFor="answer">Γράψε την απάντησή σου με δικά σου λόγια</label>
          <textarea id="answer" rows={3} value={text} onChange={(e) => setText(e.target.value)} />
          <button type="submit" className="btn btn-primary">
            <Send aria-hidden="true" />
            Στείλε την απάντηση
          </button>
        </form>
      )}

      {error && <Notice tone="error" live>{error}</Notice>}

      {result && (
        <div ref={feedback} tabIndex={-1} className="feedback">
          <Notice tone={result.outcome === "correct" ? "success" : "calm"} icon={result.outcome === "correct" ? CircleCheck : Users}>
            <p className="feedback-message">{result.message}</p>
            {result.key_point && (result.done || result.outcome === "self_check") && <p>{result.key_point}</p>}
          </Notice>
          {result.outcome === "self_check" && (
            <div className="actions actions-row">
              <button type="button" className="btn btn-primary" onClick={() => selfCheck(true)}>Ναι, είναι κοντά</button>
              <button type="button" className="btn" onClick={() => selfCheck(false)}>Όχι ακόμα</button>
            </div>
          )}
        </div>
      )}

      <section aria-label="Υποδείξεις" aria-live="polite" className="hints">
        {hints.map((h) => (
          <div key={h.step} className="hint">
            <p className="hint-step">
              <Lightbulb aria-hidden="true" /> Υπόδειξη {h.step} από 4
            </p>
            <p>{h.text}</p>
            {h.action === "open_section" && !showSection && (
              <button type="button" className="btn" onClick={openSection}>
                <BookOpen aria-hidden="true" />
                Άνοιξε την ενότητα
              </button>
            )}
            {h.action === "replay_example" && h.example && (
              <div className="hint-example">
                <EasyBlocks blocks={[h.example]} glossary={[]} idPrefix="ex" />
                <button type="button" className="btn" onClick={() => {
                  speech.speak(blockSpeech([h.example!], [], "ex"));
                  if (attemptId) api.post(`/attempts/${attemptId}/flags`, { listened: true }).catch(() => undefined);
                }}>
                  <Volume2 aria-hidden="true" />
                  Άκου το παράδειγμα
                </button>
              </div>
            )}
          </div>
        ))}
      </section>

      {showSection && sectionView}

      <div className="actions">
        {finished ? (
          <button type="button" className="btn btn-primary" onClick={() => onNext(result!)}>
            <ChevronRight aria-hidden="true" />
            {number < total ? "Επόμενη ερώτηση" : "Συνέχεια"}
          </button>
        ) : (
          <>
            <button type="button" className="btn btn-help" onClick={ask} aria-disabled={hintsLeft === 0 || !attemptId}
              aria-describedby="help-count">
              <HandHelping aria-hidden="true" />
              Βοήθεια
            </button>
            <p id="help-count" className="help-count">
              {hintsLeft > 0 ? `Υπάρχουν ακόμα ${hintsLeft} υποδείξεις.` : "Είδες όλες τις υποδείξεις."}
            </p>
            {(tried.length > 0 || result?.outcome === "try_again") && (
              <button type="button" className="btn" onClick={explain}>
                <Lightbulb aria-hidden="true" />
                Δείξε μου την εξήγηση
              </button>
            )}
          </>
        )}
      </div>
    </Screen>
  );
}

function StrategyQuestion({ courseId, back, onDone }: { courseId: number; back: string; onDone: () => void }) {
  const choices = [
    { key: "listen", label: "Να ακούσω το κείμενο", icon: Volume2 },
    { key: "image", label: "Να δω την εικόνα", icon: ImageIcon },
    { key: "example", label: "Το παράδειγμα", icon: Lightbulb },
  ];
  const pick = async (choice: string) => {
    await api.post(`/courses/${courseId}/strategy`, { choice }).catch(() => undefined);
    onDone();
  };
  return (
    <Screen title="Τι σε βοήθησε σήμερα;" back={back}
      listen={[{ text: `Τι σε βοήθησε σήμερα; ${choices.map((c) => c.label).join(". ")}.` }]}>
      <p>Θα σου το θυμίσουμε την επόμενη φορά.</p>
      <div className="choices" role="group" aria-label="Τι σε βοήθησε σήμερα;">
        {choices.map(({ key, label, icon: Icon }) => (
          <button key={key} type="button" className="btn btn-choice" onClick={() => pick(key)}>
            <Icon aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
      <div className="actions">
        <button type="button" className="btn" onClick={onDone}>
          Τίποτα από αυτά
        </button>
      </div>
    </Screen>
  );
}
