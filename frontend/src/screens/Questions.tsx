import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  BookOpen, ChartColumn, ChevronRight, CircleCheck, CircleHelp, Footprints, HandHelping, Image as ImageIcon,
  Lightbulb, ListChecks, MapPin, PenLine, Save, Send, Users, Volume2, X,
} from "lucide-react";
import { api, errorText } from "../api";
import { Screen } from "../components/Screen";
import { EasyBlocks, blockSpeech, visibleBlocks } from "../components/Blocks";
import { ConceptList, LEVELS, Loading, Notice, Pictogram } from "../components/common";
import { MilestoneNotes, OriginalText, SectionProposal } from "../components/Support";
import { useSettings } from "../settings";
import { useSpeech } from "../speech";
import type {
  AnswerResult, Concept, Hint, Milestone, Note, Option, PickResult, Proposal, Question, Questions, Study, Support,
} from "../types";
import { useLoad } from "../useLoad";

type Phase = "intro" | "menu" | "keypoints" | "own" | "question" | "proposal" | "strategy" | "done";

export function QuestionsScreen() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const limit = Number(search.get("limit")) || undefined; // "Θες 2 ερωτήσεις...;" from Σήμερα
  return <QuestionsFlow key={id} sectionId={id!} limit={limit} />;
}

function QuestionsFlow({ sectionId, limit }: { sectionId: string; limit?: number }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const speech = useSpeech();
  const set = useLoad<Questions>(`/sections/${sectionId}/questions`);
  const study = useLoad<Study>(`/sections/${sectionId}/study`);
  const [phase, setPhase] = useState<Phase | null>(null);
  const [index, setIndex] = useState(0);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [showSection, setShowSection] = useState(false);

  const data = set.data && limit ? { ...set.data, questions: set.data.questions.slice(0, limit) } : set.data;
  useEffect(() => {
    if (!data || phase !== null) return;
    if (data.level >= 4) setPhase("menu");
    else if (data.last_strategy) setPhase("intro");
    else setPhase(data.questions.length ? "question" : "done");
  }, [data, phase]);

  const advance = () => {
    if (!data) return;
    if (index + 1 < data.questions.length) {
      setIndex(index + 1);
      setPhase("question");
    } else {
      setPhase(data.ask_strategy ? "strategy" : "done");
    }
  };

  const nextQuestion = (result: AnswerResult) => {
    if (result.proposal) {
      setProposal(result.proposal);
      setPhase("proposal");
      return;
    }
    advance();
  };

  const back = `/sections/${sectionId}`;
  const level = data?.level ?? 1;
  // The Easy-to-Read section is offered inline only at levels 1-2 (or after falling back).
  const easySection = study.data && (
    <section className="panel inline-section" aria-label="Η ενότητα">
      <h2>{study.data.title}</h2>
      <EasyBlocks blocks={visibleBlocks(study.data.easy.blocks, Math.min(level, 2))} glossary={study.data.easy.glossary}
        idPrefix="s" termMode={level <= 1 ? "inline" : "tap"} />
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

  if (phase === "menu") {
    return <Level4Menu sectionId={sectionId} back={back} hasQuestions={data.questions.length > 0}
      onPick={(p) => (p === "exam" ? navigate(`/sections/${sectionId}/exam`) : setPhase(p))} />;
  }
  if (phase === "keypoints") {
    return <KeyPoints sectionId={sectionId} back={() => setPhase("menu")} onDone={(r) => r.proposal ? (setProposal(r.proposal), setPhase("proposal")) : setPhase("menu")} />;
  }
  if (phase === "own") {
    return <OwnQuestion sectionId={sectionId} back={() => setPhase("menu")} />;
  }

  if (phase === "intro" && data.last_strategy) {
    const strategy = data.last_strategy;
    return (
      <Screen title="Πριν τις ερωτήσεις" back={back}
        listen={[{ text: `Την προηγούμενη φορά σε βοήθησε: ${strategy.label}. Θες να το χρησιμοποιήσεις και τώρα;` }]}>
        <p className="lead">Την προηγούμενη φορά σε βοήθησε: <strong>{strategy.label}</strong>.</p>
        <p>Θες να το χρησιμοποιήσεις και τώρα; Μπορείς να γυρίσεις στην ενότητα με το «Πίσω».</p>
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => setPhase(data.questions.length ? "question" : "done")}>
            <ChevronRight aria-hidden="true" />
            Συνέχεια στις ερωτήσεις
          </button>
          {strategy.choice === "listen" && study.data && (
            <button type="button" className="btn" onClick={() => speech.speak(study.data!.original.map((text) => ({ text })))}>
              <Volume2 aria-hidden="true" />
              Άκου το κείμενο
            </button>
          )}
        </div>
      </Screen>
    );
  }

  if (phase === "proposal" && proposal) {
    const support: Support = { section_id: data.section_id, level, level_name: LEVELS[level].name, proposal, new_milestones: [] };
    return (
      <Screen title="Μια πρόταση" back={back} autoRead={settings.autoRead} listen={[{ text: proposal.message }]}>
        <SectionProposal support={support} onDone={() => (level >= 4 ? setPhase("menu") : advance())} />
        <p>Αν πεις ναι, η αλλαγή ισχύει την επόμενη φορά που θα ανοίξεις την ενότητα.</p>
      </Screen>
    );
  }

  if (phase === "strategy") {
    return <StrategyQuestion courseId={data.course_id} back={back} onDone={() => setPhase("done")} />;
  }

  if (phase === "done") {
    return <Finished data={data} study={study.data} back={back} />;
  }

  const question = data.questions[index];
  return (
    <OneQuestion
      key={question.id}
      question={question}
      number={index + 1}
      total={data.questions.length}
      level={level}
      back={back}
      study={study.data}
      easySection={easySection}
      showSection={showSection}
      setShowSection={setShowSection}
      onNext={nextQuestion}
    />
  );
}

function Finished({ data, study, back }: { data: Questions; study: Study | null; back: string }) {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const concepts = useLoad<Concept[]>(`/sections/${data.section_id}/concepts`);
  const text = data.questions.length ? "Τελείωσες τις ερωτήσεις αυτής της ενότητας." : "Αυτή η ενότητα δεν έχει ερωτήσεις.";
  const next = study?.next_id;
  return (
    <Screen title="Τέλος ερωτήσεων" back={back} autoRead={settings.autoRead} listen={[{ text }]}>
      <Notice tone="success" icon={CircleCheck}><p>{text}</p></Notice>
      {concepts.data && concepts.data.length > 0 && (
        <section aria-labelledby="concepts-title">
          <h2 id="concepts-title">Οι έννοιες αυτής της ενότητας</h2>
          <ConceptList concepts={concepts.data} />
        </section>
      )}
      <div className="actions">
        {next ? (
          <button type="button" className="btn btn-primary" onClick={() => navigate(`/sections/${next}`)}>
            <ChevronRight aria-hidden="true" />
            Επόμενη ενότητα
          </button>
        ) : (
          <button type="button" className="btn btn-primary" onClick={() => navigate(study ? `/chapters/${study.document_id}` : "/")}>
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

function OneQuestion(props: {
  question: Question;
  number: number;
  total: number;
  level: number;
  back: string;
  study: Study | null;
  easySection: ReactNode;
  showSection: boolean;
  setShowSection: (v: boolean) => void;
  onNext: (result: AnswerResult) => void;
}) {
  const { question, number, total, level, back, study, easySection, showSection, setShowSection, onNext } = props;
  const { settings } = useSettings();
  const speech = useSpeech();
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [hints, setHints] = useState<Hint[]>([]);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [tried, setTried] = useState<number[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [triedSentences, setTriedSentences] = useState<number[]>([]);
  const [foundSentence, setFoundSentence] = useState<number | null>(null);
  const [pickMessage, setPickMessage] = useState<string | null>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const answerBox = useRef<HTMLTextAreaElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // React StrictMode runs effects twice in development
    started.current = true;
    api.post<{ attempt_id: number; new_milestones: Milestone[] }>(`/questions/${question.id}/attempts`)
      .then((r) => {
        setAttemptId(r.attempt_id);
        setMilestones(r.new_milestones);
      })
      .catch((err) => setError(errorText(err)));
  }, [question.id]);

  useEffect(() => {
    if (result) feedback.current?.focus();
  }, [result]);

  const say = (t: string) => speech.enabled && settings.autoRead && speech.speak(t);
  const addMilestones = (items: Milestone[]) => items.length && setMilestones((m) => [...m, ...items]);

  const explainHints = hints.filter((h) => h.kind === "explain");
  const searchHints = hints.filter((h) => h.kind === "search");
  const lastSearch = searchHints[searchHints.length - 1];
  const fellBack = hints.some((h) => h.fell_back);
  const twoChoices = explainHints.find((h) => h.step === 3)?.choices ?? [];
  const options: Option[] = question.mode === "choice" && twoChoices.length ? twoChoices : question.options;
  const finished = result?.done === true;
  const searching = level >= 3 && !fellBack;

  const ask = async () => {
    if (!attemptId) return;
    try {
      const hint = await api.post<Hint>(`/attempts/${attemptId}/hint`);
      setHints((h) => [...h, hint]);
      setError(null);
      say(hint.text);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const pick = async (sentence: number) => {
    if (!attemptId) return;
    try {
      const r = await api.post<PickResult>(`/attempts/${attemptId}/pick`, { sentence });
      setPickMessage(r.message);
      say(r.message);
      addMilestones(r.new_milestones);
      if (r.correct) {
        setFoundSentence(sentence);
        setTimeout(() => answerBox.current?.focus(), 0);
      } else {
        setTriedSentences((t) => [...t, sentence]);
        if (r.fallback_hint) setHints((h) => [...h, r.fallback_hint!]);
      }
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
      addMilestones(r.new_milestones);
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

  const finishWith = async (path: string, body?: unknown) => {
    if (!attemptId) return;
    const r = await api.post<AnswerResult>(`/attempts/${attemptId}/${path}`, body);
    setResult(r);
    addMilestones(r.new_milestones);
  };

  const listen = [
    { text: `Ερώτηση ${number} από ${total}. ${question.prompt}` },
    ...(question.mode === "choice" || twoChoices.length
      ? [{ text: `Οι επιλογές είναι: ${options.map((o) => o.text).join(". ")}.` }]
      : [{ text: "Γράψε την απάντησή σου με δικά σου λόγια." }]),
    ...hints.map((h) => ({ text: h.text })),
    ...(result ? [{ text: result.message }] : []),
  ];

  const openSection = () => {
    setShowSection(true);
    if (attemptId) api.post(`/attempts/${attemptId}/flags`, { opened_section: true }).catch(() => undefined);
  };

  const showChoices = question.mode === "choice" || twoChoices.length > 0;
  const picking = lastSearch?.step === 3 && !fellBack && lastSearch.paragraph !== null;

  return (
    <Screen title={`Ερώτηση ${number} από ${total}`} back={back} listen={listen} autoRead={settings.autoRead}>
      <MilestoneNotes items={milestones} />
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
          <textarea id="answer" ref={answerBox} rows={3} value={text} onChange={(e) => setText(e.target.value)} />
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
              <button type="button" className="btn btn-primary" onClick={() => finishWith("self-check", { close: true })}>Ναι, είναι κοντά</button>
              <button type="button" className="btn" onClick={() => finishWith("self-check", { close: false })}>Όχι ακόμα</button>
            </div>
          )}
        </div>
      )}

      <section aria-label="Υποδείξεις" aria-live="polite" className="hints">
        {hints.map((h, i) => (
          <div key={i} className={`hint ${h.kind === "search" ? "hint-search" : ""}`}>
            <p className="hint-step">
              {h.kind === "search" ? <MapPin aria-hidden="true" /> : <Lightbulb aria-hidden="true" />}
              {h.kind === "search" ? `Ψάξε στο κείμενο: βήμα ${h.step} από 3` : `Υπόδειξη ${h.step} από 4`}
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
                <EasyBlocks blocks={[h.example]} glossary={[]} idPrefix={`ex${i}`} />
                <button type="button" className="btn" onClick={() => {
                  speech.speak(blockSpeech([h.example!], [], `ex${i}`));
                  if (attemptId) api.post(`/attempts/${attemptId}/flags`, { listened: true }).catch(() => undefined);
                }}>
                  <Volume2 aria-hidden="true" />
                  Άκου το παράδειγμα
                </button>
              </div>
            )}
          </div>
        ))}
        {pickMessage && (
          <Notice tone={foundSentence !== null ? "success" : "calm"} icon={foundSentence !== null ? CircleCheck : MapPin}>
            <p>{pickMessage}</p>
          </Notice>
        )}
      </section>

      {searchHints.length > 0 && study && (
        <section className="panel" aria-labelledby={`orig-title-${question.id}`}>
          <h2 id={`orig-title-${question.id}`}>Το πρωτότυπο κείμενο</h2>
          <OriginalText
            idPrefix={`q${question.id}`}
            paragraphs={study.original}
            highlight={lastSearch.step >= 2 ? lastSearch.paragraph : null}
            pick={picking || foundSentence !== null ? {
              paragraph: lastSearch.paragraph!,
              sentences: lastSearch.sentences,
              tried: triedSentences,
              found: foundSentence,
              onPick: pick,
            } : null}
          />
        </section>
      )}

      {showSection && easySection}

      <div className="actions">
        {finished ? (
          <button type="button" className="btn btn-primary" onClick={() => onNext(result!)}>
            <ChevronRight aria-hidden="true" />
            {number < total ? "Επόμενη ερώτηση" : "Συνέχεια"}
          </button>
        ) : (
          <>
            <button type="button" className="btn btn-help" onClick={ask} aria-disabled={!attemptId} aria-describedby="help-note">
              <HandHelping aria-hidden="true" />
              Βοήθεια
            </button>
            <p id="help-note" className="help-count">
              {searching
                ? "Η βοήθεια σού δείχνει πού να ψάξεις στο κείμενο."
                : explainHints.length < 4 ? `Υπάρχουν ακόμα ${4 - explainHints.length} υποδείξεις.` : "Είδες όλες τις υποδείξεις."}
            </p>
            {(tried.length > 0 || result?.outcome === "try_again") && (
              <button type="button" className="btn" onClick={() => finishWith("explain")}>
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

/** Level 4: the student chooses what to do. Help only if they ask for it. */
function Level4Menu({ sectionId, back, hasQuestions, onPick }: {
  sectionId: string;
  back: string;
  hasQuestions: boolean;
  onPick: (p: "keypoints" | "own" | "question" | "exam") => void;
}) {
  const choices = [
    { key: "keypoints" as const, label: "Γράψε τα βασικά σημεία", icon: PenLine },
    { key: "own" as const, label: "Γράψε μια δική σου ερώτηση", icon: CircleHelp },
    ...(hasQuestions
      ? [
          { key: "question" as const, label: "Απάντησε σε ερωτήσεις", icon: ListChecks },
          { key: "exam" as const, label: "Εξάσκηση σαν στις εξετάσεις", icon: Footprints },
        ]
      : []),
  ];
  return (
    <Screen title="Τι κράτησες;" back={back} listen={[{ text: `Τι κράτησες; Διάλεξε: ${choices.map((c) => c.label).join(". ")}.` }]}>
      <p>Διάλεξε τι θέλεις να κάνεις με αυτή την ενότητα.</p>
      <div className="choices" role="group" aria-label="Τι θέλεις να κάνεις;" data-section={sectionId}>
        {choices.map(({ key, label, icon: Icon }) => (
          <button key={key} type="button" className="btn btn-choice" onClick={() => onPick(key)}>
            <Icon aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
    </Screen>
  );
}

function KeyPoints({ sectionId, back, onDone }: { sectionId: string; back: () => void; onDone: (r: AnswerResult) => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [points, setPoints] = useState<{ attempt_id: number; key_points: string[] } | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setError("Γράψε τουλάχιστον ένα βασικό σημείο.");
      return;
    }
    try {
      setPoints(await api.post(`/sections/${sectionId}/keypoints`, { text }));
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const check = async (close: boolean) => {
    if (!points) return;
    setResult(await api.post<AnswerResult>(`/attempts/${points.attempt_id}/self-check`, { close }));
  };

  return (
    <Screen title="Τα βασικά σημεία" back={back}>
      {!points ? (
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="keypoints">Γράψε με δικά σου λόγια τα βασικά σημεία της ενότητας</label>
            <textarea id="keypoints" rows={6} value={text} onChange={(e) => setText(e.target.value)}
              aria-describedby={error ? "keypoints-error" : undefined} />
            {error && <p id="keypoints-error" className="field-error" role="alert">{error}</p>}
          </div>
          <div className="actions">
            <button type="submit" className="btn btn-primary"><Send aria-hidden="true" />Δες τα βασικά σημεία</button>
          </div>
        </form>
      ) : (
        <>
          <h2>Τα δικά σου σημεία</h2>
          <p className="own-text">{text}</p>
          <h2>Τα βασικά σημεία της ενότητας</h2>
          <ul className="plain-list">{points.key_points.map((p) => <li key={p}>{p}</li>)}</ul>
          {!result ? (
            <>
              <p className="lead">Τα είχες;</p>
              <div className="actions actions-row">
                <button type="button" className="btn btn-primary" onClick={() => check(true)}>Ναι, τα είχα</button>
                <button type="button" className="btn" onClick={() => check(false)}>Μου έλειπε κάτι</button>
              </div>
            </>
          ) : (
            <>
              <Notice tone="success" icon={CircleCheck} live><p>{result.message}</p></Notice>
              <MilestoneNotes items={result.new_milestones} />
              <div className="actions">
                <button type="button" className="btn btn-primary" onClick={() => onDone(result)}>
                  <ChevronRight aria-hidden="true" />
                  Συνέχεια
                </button>
              </div>
            </>
          )}
        </>
      )}
    </Screen>
  );
}

function OwnQuestion({ sectionId, back }: { sectionId: string; back: () => void }) {
  const notes = useLoad<Note[]>(`/sections/${sectionId}/my-questions`);
  const [text, setText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setError("Γράψε την ερώτησή σου.");
      return;
    }
    await api.post(`/sections/${sectionId}/my-questions`, { text });
    setText("");
    setError(null);
    setMessage("Η ερώτησή σου αποθηκεύτηκε.");
    notes.reload();
  };

  return (
    <Screen title="Μια δική σου ερώτηση" back={back}>
      <p>Τι θα ρωτούσες για αυτή την ενότητα; Οι ερωτήσεις σου μένουν εδώ για την επόμενη φορά.</p>
      <form onSubmit={save} noValidate>
        <div className="field">
          <label htmlFor="own-question">Η ερώτησή σου</label>
          <textarea id="own-question" rows={3} value={text} onChange={(e) => setText(e.target.value)}
            aria-describedby={error ? "own-error" : undefined} />
          {error && <p id="own-error" className="field-error" role="alert">{error}</p>}
        </div>
        <div className="actions">
          <button type="submit" className="btn btn-primary"><Save aria-hidden="true" />Αποθήκευση</button>
        </div>
      </form>
      {message && <Notice tone="success" icon={CircleCheck} live><p>{message}</p></Notice>}
      {notes.data && notes.data.length > 0 && (
        <>
          <h2>Οι ερωτήσεις μου</h2>
          <ul className="plain-list">{notes.data.map((n) => <li key={n.id}>{n.text}</li>)}</ul>
        </>
      )}
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
      <p>Θα το δεις ξανά την επόμενη φορά.</p>
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
