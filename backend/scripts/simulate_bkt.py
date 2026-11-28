"""Simulation: is BKT a better judge than the simple rules of WHEN to offer less support?

200 virtual students work on one section with 2 concepts (questions alternate between them).
For every student and concept we know the true moment it is learned. Before that moment the
student answers right only by luck (depends on the question type) and often asks for hints;
after it, the student answers right except for careless slips.

For both methods we record the first "less support" proposal and compare it with the moment
the student really knew BOTH concepts:
  - early (false positive): proposed BEFORE the student really knew both concepts
  - delay: how many answers AFTER really knowing both concepts the proposal came
  - never: no proposal within 30 answers

Run from backend/:  .venv\\Scripts\\python -m scripts.simulate_bkt
Writes docs/bkt-simulation.md and docs/bkt-simulation.svg (deterministic: fixed seed).
"""

import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from app.config import FadingConfig, load_config
from app.learning import bkt
from app.learning.fading import Outcome, propose

STUDENTS = 200
MAX_ANSWERS = 30
SEED = 2026
TRUE_LEARN = 0.2  # chance per practice to really learn a concept (the "true" world)
ALREADY_KNOWN = 0.2  # share of concepts a student already knows at the start
SLIP = 0.1
HINTS_IF_UNKNOWN = ([0, 1, 2, 3], [0.35, 0.25, 0.2, 0.2])
HINTS_IF_KNOWN = ([0, 1], [0.85, 0.15])
RIGHT_WITH_HELP = 0.7  # with 2+ hints, the unknown student often gets it right anyway

SCENARIOS = [("Ερωτήσεις 2 επιλογών", 2), ("Ερωτήσεις 3 επιλογών", 3), ("Ανοιχτές ερωτήσεις", 0)]
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "docs"


@dataclass
class Answer:
    concept: int
    right_first_time: bool
    hints: int


@dataclass
class Result:
    early: bool
    delay: int | None  # None when there was no proposal or it was early
    never: bool


def simulate_student(rng: random.Random, options: int) -> tuple[list[Answer], int]:
    """Answers of one student and the answer number (1-based) after which both concepts are known."""
    learn_at = []
    for _ in range(2):
        if rng.random() < ALREADY_KNOWN:
            learn_at.append(0)
        else:
            k = 1
            while rng.random() >= TRUE_LEARN:
                k += 1
            learn_at.append(k)  # known from its k-th practice on
    guess = {2: 0.5, 3: 1 / 3, 0: 0.05}[options]
    answers, practice, known_since = [], [0, 0], [None, None]
    for n in range(1, MAX_ANSWERS + 1):
        c = (n - 1) % 2
        practice[c] += 1
        knows = practice[c] > learn_at[c]
        if knows and known_since[c] is None:
            known_since[c] = n
        if knows:
            hints = rng.choices(*HINTS_IF_KNOWN)[0]
            right = rng.random() >= SLIP
        else:
            hints = rng.choices(*HINTS_IF_UNKNOWN)[0]
            right = rng.random() < (guess if hints <= 1 else RIGHT_WITH_HELP)
        answers.append(Answer(c, right, hints))
    both = max(known_since) if None not in known_since else MAX_ANSWERS + 1
    return answers, both


def first_proposal_rules(answers: list[Answer], cfg: FadingConfig) -> int | None:
    outcomes = []
    for n, a in enumerate(answers, 1):
        outcomes.append(Outcome(a.hints, correct=True, wrong_tries=0 if a.right_first_time else 1))
        if propose(1, outcomes, cfg) == "up":
            return n
    return None


def first_proposal_bkt(answers: list[Answer], options: int) -> int | None:
    cfg = load_config().bkt
    p = [cfg.p_init, cfg.p_init]
    for n, a in enumerate(answers, 1):
        ev = bkt.evidence(a.right_first_time, 0 if a.right_first_time else 1, a.hints, False, options, cfg)
        p[a.concept] = bkt.update(p[a.concept], ev.correct, ev.guess, cfg)
        if n >= cfg.min_observations and all(x > cfg.up_threshold for x in p):
            return n
    return None


def judge(proposal: int | None, both_known: int) -> Result:
    if proposal is None:
        return Result(early=False, delay=None, never=True)
    if proposal < both_known:
        return Result(early=True, delay=None, never=False)
    return Result(early=False, delay=proposal - both_known, never=False)


def run(students: int = STUDENTS, seed: int = SEED) -> list[dict]:
    rows = []
    fading = load_config().fading
    for name, options in SCENARIOS:
        rng = random.Random(f"{seed}-{options}")
        results = {"BKT": [], "Απλοί κανόνες": []}
        for _ in range(students):
            answers, both = simulate_student(rng, options)
            results["BKT"].append(judge(first_proposal_bkt(answers, options), both))
            results["Απλοί κανόνες"].append(judge(first_proposal_rules(answers, fading), both))
        for method, rs in results.items():
            delays = [r.delay for r in rs if r.delay is not None]
            rows.append({
                "scenario": name,
                "method": method,
                "early": 100 * sum(r.early for r in rs) / len(rs),
                "delay": statistics.median(delays) if delays else None,
                "never": 100 * sum(r.never for r in rs) / len(rs),
            })
    return rows


def fmt(x: float | None, suffix: str = "") -> str:
    return "–" if x is None else f"{x:.1f}{suffix}".replace(".", ",")


def svg(rows: list[dict]) -> str:
    """Grouped bars: % early proposals per scenario, BKT vs simple rules. Direct labels, no colour-only meaning."""
    width, height, left, top, bottom = 720, 330, 64, 56, 70
    plot_w, plot_h = width - left - 24, height - top - bottom
    colors = {"BKT": "#2a63c4", "Απλοί κανόνες": "#c2571a"}  # checked with the dataviz palette validator
    vmax = max(50, max(r["early"] for r in rows) * 1.15)
    group_w = plot_w / len(SCENARIOS)
    bar_w = min(56, group_w / 3.2)
    y = lambda v: top + plot_h - v / vmax * plot_h  # noqa: E731
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="t d" font-family="Segoe UI, Arial, sans-serif">',
        '<title id="t">Προτάσεις για λιγότερη υποστήριξη ΠΡΙΝ ο φοιτητής μάθει τις έννοιες</title>',
        f'<desc id="d">{"; ".join(f"{r["scenario"]}, {r["method"]}: {fmt(r["early"], "%")}" for r in rows)}</desc>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{left}" y="26" font-size="17" font-weight="700" fill="#111418">'
        'Πρόωρες προτάσεις για λιγότερη υποστήριξη (% των 200 φοιτητών)</text>',
    ]
    for v in range(0, int(vmax) + 1, 10):
        out.append(f'<line x1="{left}" x2="{width - 24}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#d5d9e0" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y(v) + 4:.1f}" font-size="12" text-anchor="end" fill="#3b4350">{v}%</text>')
    for g, (name, _) in enumerate(SCENARIOS):
        gx = left + g * group_w + group_w / 2
        for i, method in enumerate(colors):
            r = next(r for r in rows if r["scenario"] == name and r["method"] == method)
            x = gx + (i - 1) * (bar_w + 4) + 2
            h = max(2, r["early"] / vmax * plot_h)
            out.append(f'<path d="M{x:.1f},{top + plot_h} v{-h + 4:.1f} q0,-4 4,-4 h{bar_w - 8:.1f} q4,0 4,4 v{h - 4:.1f} z" fill="{colors[method]}"/>')
            out.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h - h - 6:.1f}" font-size="12" font-weight="700" '
                       f'text-anchor="middle" fill="#111418">{fmt(r["early"], "%")}</text>')
        out.append(f'<text x="{gx:.1f}" y="{top + plot_h + 22}" font-size="13" text-anchor="middle" fill="#111418">{name}</text>')
    lx = left
    for method, color in colors.items():
        out.append(f'<rect x="{lx}" y="{height - 26}" width="14" height="14" rx="3" fill="{color}"/>')
        out.append(f'<text x="{lx + 20}" y="{height - 14}" font-size="13" fill="#111418">{method}</text>')
        lx += 150
    out.append("</svg>")
    return "\n".join(out) + "\n"


def markdown(rows: list[dict]) -> str:
    lines = [
        "# Προσομοίωση: BKT ή απλοί κανόνες;",
        "",
        f"{STUDENTS} εικονικοί φοιτητές ανά σενάριο, μία ενότητα με 2 έννοιες, έως {MAX_ANSWERS} απαντήσεις.",
        "Για κάθε φοιτητή ξέρουμε πότε έμαθε πραγματικά κάθε έννοια. Πριν από αυτό απαντά σωστά μόνο με τύχη "
        f"(ή με βοήθεια), μετά απαντά σωστά εκτός από απροσεξία ({int(SLIP * 100)}%). "
        f"Seed {SEED}: τα αποτελέσματα βγαίνουν πάντα ίδια.",
        "",
        "- **Πρόωρη πρόταση**: πρόταση για λιγότερη υποστήριξη ΠΡΙΝ ο φοιτητής μάθει πραγματικά και τις 2 έννοιες.",
        "- **Καθυστέρηση**: πόσες απαντήσεις μετά την πραγματική εκμάθηση ήρθε η πρόταση (διάμεσος).",
        f"- **Καμία πρόταση**: δεν ήρθε πρόταση μέσα σε {MAX_ANSWERS} απαντήσεις.",
        "",
        "![Πρόωρες προτάσεις ανά σενάριο](bkt-simulation.svg)",
        "",
        "| Σενάριο | Μέθοδος | Πρόωρες προτάσεις | Καθυστέρηση (απαντήσεις) | Καμία πρόταση |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['scenario']} | {r['method']} | {fmt(r['early'], '%')} | {fmt(r['delay'])} | {fmt(r['never'], '%')} |")
    bkt2 = next(r for r in rows if r["method"] == "BKT")
    rules2 = next(r for r in rows if r["method"] != "BKT")
    lines += [
        "",
        "## Τι σημαίνει",
        "",
        f"- Με ερωτήσεις 2 επιλογών, οι απλοί κανόνες πρότειναν λιγότερη υποστήριξη **πριν** ο φοιτητής μάθει "
        f"τις έννοιες στο {fmt(rules2['early'], '%')} των φοιτητών (τρεις τυχερές σωστές απαντήσεις αρκούν). "
        f"Το BKT στο {fmt(bkt2['early'], '%')}, γιατί ξέρει ότι στις 2 επιλογές η τύχη είναι 50%.",
        "- Το τίμημα: το BKT προτείνει **αργότερα** (περισσότερες απαντήσεις μετά την εκμάθηση) και σε "
        "κάποιους φοιτητές καθόλου μέσα στις 30 απαντήσεις. Προτιμά να περιμένει παρά να αφαιρέσει "
        "βοήθεια πολύ νωρίς. Ο φοιτητής μπορεί πάντα να αλλάξει μόνος του τον τρόπο μελέτης.",
        "- Στις ανοιχτές ερωτήσεις η τύχη είναι μικρή, οπότε η διαφορά των δύο μεθόδων μικραίνει.",
        "",
        "Παράμετροι BKT από το `backend/config.toml`. Οι απλοί κανόνες είναι αυτοί της ενότητας `[fading]` "
        "(3 επιτυχίες στη σειρά με 0–1 υποδείξεις). Η προσομοίωση είναι εικονική: δείχνει πώς συμπεριφέρονται "
        "οι δύο μέθοδοι με λογικές υποθέσεις, δεν αντικαθιστά δοκιμή με πραγματικούς φοιτητές.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = run()
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "bkt-simulation.svg").write_text(svg(rows), encoding="utf-8")
    (OUT_DIR / "bkt-simulation.md").write_text(markdown(rows), encoding="utf-8")
    for r in rows:
        print(f"{r['scenario']:22s} {r['method']:14s} πρόωρες {fmt(r['early'], '%'):>7s}  "
              f"καθυστέρηση {fmt(r['delay']):>5s}  καμία {fmt(r['never'], '%'):>6s}")
    print(f"Έτοιμο: {OUT_DIR / 'bkt-simulation.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
