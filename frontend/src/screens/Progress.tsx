import { useState } from "react";
import { useParams } from "react-router-dom";
import { CircleCheck, Hand, Info, TrendingDown } from "lucide-react";
import { Screen } from "../components/Screen";
import { CourseIcon, LevelSteps, Loading, Notice } from "../components/common";
import { useSettings } from "../settings";
import type { CourseProgress, Progress } from "../types";
import { useLoad } from "../useLoad";

const dayFmt = new Intl.DateTimeFormat("el-GR", { day: "numeric", month: "short" });
const fullFmt = new Intl.DateTimeFormat("el-GR", { weekday: "long", day: "numeric", month: "long" });
const num = (x: number) => x.toLocaleString("el-GR", { maximumFractionDigits: 1 });

/** Each week as a row of hands: one hand = one hint per question. Text says the same thing. */
function WeekHands({ course }: { course: CourseProgress }) {
  return (
    <ul className="weeks">
      {course.weeks.map((w) => {
        const hands = w.hints_per_question === null ? 0 : Math.round(w.hints_per_question);
        return (
          <li key={w.label} className="week">
            <span className="week-label">{w.label}</span>
            <span className="hands" aria-hidden="true">
              {Array.from({ length: 4 }, (_, i) => (
                <Hand key={i} className={i < hands ? "hand-on" : "hand-off"} />
              ))}
            </span>
            <span className="week-value">
              {w.hints_per_question === null
                ? "Δεν υπάρχουν απαντήσεις"
                : `${num(w.hints_per_question)} υποδείξεις ανά ερώτηση (${w.questions} ερωτήσεις)`}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Daily bars: hints per question. One series, so no legend; hover or focus shows the value. */
function DailyChart({ course }: { course: CourseProgress }) {
  const [active, setActive] = useState<number | null>(null);
  const days = course.days;
  if (days.length < 2) return null;
  const W = 640, H = 220, left = 36, bottom = 28, top = 16;
  const plotW = W - left - 8, plotH = H - top - bottom;
  const max = 4;
  const slot = plotW / days.length;
  const barW = Math.min(28, slot - 2);
  const y = (v: number) => top + plotH - (v / max) * plotH;
  const labelled = new Set([0, days.length - 1]);
  const titleId = `chart-title-${course.id}`;
  const tip = active !== null ? days[active] : null;

  return (
    <figure className="chart">
      <figcaption id={titleId} className="chart-title">
        Υποδείξεις ανά ερώτηση, κάθε μέρα
      </figcaption>
      <div className="chart-box" onMouseLeave={() => setActive(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={titleId}
          aria-describedby={`chart-summary-${course.id}`}>
          {[0, 1, 2, 3, 4].map((v) => (
            <g key={v}>
              <line x1={left} x2={W - 8} y1={y(v)} y2={y(v)} className="grid" />
              <text x={left - 8} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
            </g>
          ))}
          {days.map((d, i) => {
            const x = left + i * slot + (slot - barW) / 2;
            const h = Math.max(2, (d.hints_per_question / max) * plotH);
            const r = Math.min(4, barW / 2, h);
            const yTop = top + plotH - h;
            const path = `M${x},${top + plotH} V${yTop + r} Q${x},${yTop} ${x + r},${yTop} H${x + barW - r} Q${x + barW},${yTop} ${x + barW},${yTop + r} V${top + plotH} Z`;
            return (
              <g key={d.day} onMouseEnter={() => setActive(i)}>
                <rect x={left + i * slot} y={top} width={slot} height={plotH} fill="transparent" />
                <path d={path} className={`bar ${active === i ? "bar-active" : ""}`} />
                {labelled.has(i) && (
                  <text x={x + barW / 2} y={yTop - 6} textAnchor="middle" className="value">{num(d.hints_per_question)}</text>
                )}
                {(labelled.has(i) || i % 3 === 0) && (
                  <text x={x + barW / 2} y={H - 8} textAnchor="middle" className="axis">{dayFmt.format(new Date(d.day))}</text>
                )}
              </g>
            );
          })}
        </svg>
        {tip && (
          <div className="tooltip" style={{ left: `${((left + (active! + 0.5) * slot) / W) * 100}%` }}>
            <strong>{dayFmt.format(new Date(tip.day))}</strong>
            <span>{num(tip.hints_per_question)} υποδείξεις ανά ερώτηση</span>
            <span>{tip.questions} ερωτήσεις</span>
          </div>
        )}
      </div>
      <p id={`chart-summary-${course.id}`} className="sr-only">
        Από {num(days[0].hints_per_question)} υποδείξεις ανά ερώτηση στις {dayFmt.format(new Date(days[0].day))}
        {" "}σε {num(days[days.length - 1].hints_per_question)} στις {dayFmt.format(new Date(days[days.length - 1].day))}.
      </p>
      <details className="table-view">
        <summary>Δες τα νούμερα σε πίνακα</summary>
        <table>
          <caption className="sr-only">Υποδείξεις ανά ερώτηση, κάθε μέρα</caption>
          <thead>
            <tr><th scope="col">Μέρα</th><th scope="col">Ερωτήσεις</th><th scope="col">Υποδείξεις ανά ερώτηση</th></tr>
          </thead>
          <tbody>
            {days.map((d) => (
              <tr key={d.day}>
                <th scope="row">{fullFmt.format(new Date(d.day))}</th>
                <td>{d.questions}</td>
                <td>{num(d.hints_per_question)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

function CourseCard({ course }: { course: CourseProgress }) {
  return (
    <section className="panel" aria-labelledby={`course-${course.id}`}>
      <h2 id={`course-${course.id}`} className="with-icon">
        <CourseIcon name={course.icon} />
        {course.name}
      </h2>
      <LevelSteps level={course.level} compact />
      <Notice tone={course.message.includes("λιγότερη") ? "success" : "info"} icon={course.message.includes("λιγότερη") ? TrendingDown : Info}>
        <p>{course.message}</p>
      </Notice>
      <WeekHands course={course} />
      <DailyChart course={course} />
      {course.level_history.length > 0 && (
        <>
          <h3>Αλλαγές επιπέδου</h3>
          <ul className="history">
            {course.level_history.map((h) => (
              <li key={h.at}>
                <CircleCheck aria-hidden="true" />
                {dayFmt.format(new Date(h.at))}: από επίπεδο {h.from_level} σε επίπεδο {h.to_level}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function SimulatedBanner() {
  return (
    <Notice tone="info" icon={Info}>
      <p>
        <strong>Προσομοιωμένα δεδομένα.</strong> Αυτά τα νούμερα φτιάχτηκαν για την παρουσίαση. Δεν είναι πραγματική χρήση.
      </p>
    </Notice>
  );
}

function ProgressBody({ data, impersonal = false }: { data: Progress; impersonal?: boolean }) {
  return (
    <>
      {data.simulated && <SimulatedBanner />}
      <p className="lead">{data.message}</p>
      <p>
        {impersonal
          ? "Ένα χεράκι = μία υπόδειξη ανά ερώτηση. Λιγότερα χεράκια σημαίνουν λιγότερη βοήθεια."
          : "Ένα χεράκι = μία υπόδειξη ανά ερώτηση. Λιγότερα χεράκια σημαίνουν ότι τα καταφέρνεις με λιγότερη βοήθεια."}
      </p>
      {data.courses.map((c) => (
        <CourseCard key={c.id} course={c} />
      ))}
    </>
  );
}

export function ProgressScreen() {
  const { data, error } = useLoad<Progress>("/progress");
  const { settings } = useSettings();
  return (
    <Screen
      title="Η πρόοδός μου"
      back="/"
      autoRead={settings.autoRead && !!data}
      listen={data ? [{ text: data.message }, ...data.courses.map((c) => ({ text: `${c.name}. Επίπεδο ${c.level} από 4. ${c.message}` }))] : undefined}
    >
      {error && <Notice tone="error" live>{error}</Notice>}
      {!data && !error && <Loading />}
      {data && <ProgressBody data={data} />}
    </Screen>
  );
}

/** What a supporter sees, only with the student's consent: levels and help per course. */
export function SharedProgress() {
  const { token } = useParams();
  const { data, error } = useLoad<Progress>(`/shared/${token}`);
  return (
    <Screen title="Κοινή πρόοδος" hideNav>
      <p>Αυτή η σελίδα δείχνει μόνο την πρόοδο ανά μάθημα. Δεν δείχνει απαντήσεις.</p>
      <p>Το άτομο που σας έδωσε τον σύνδεσμο μπορεί να σταματήσει την πρόσβαση όποτε θέλει.</p>
      {error && <Notice tone="calm" live>{error}</Notice>}
      {!data && !error && <Loading />}
      {data && <ProgressBody data={data} impersonal />}
    </Screen>
  );
}
