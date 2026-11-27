// Builds the simple pictograms in public/pictos/ (plain SVG, white background,
// dark strokes, so they work in both the normal and the high-contrast theme).
// Run: node scripts/make-pictos.mjs

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "pictos");
const INK = "#111418";
const PERSON = "#1b2a4a";
const BLUE = "#0a3d8f";
const GREY = "#6b7280";
const COFFEE = "#6b3e1f";

const defs = `<defs>
  <g id="p"><circle cx="0" cy="-15" r="6.5" fill="${PERSON}"/><path d="M-8,11 v-11 a8,8 0 0 1 16,0 v11 z" fill="${PERSON}"/></g>
  <g id="cup"><path d="M0,0 h26 v14 a13,13 0 0 1 -26,0 z" fill="${COFFEE}"/><path d="M26,4 a7,7 0 0 1 0,14" fill="none" stroke="${COFFEE}" stroke-width="3.5"/>
    <path d="M7,-6 q-3,-5 0,-10 M15,-6 q-3,-5 0,-10" fill="none" stroke="${GREY}" stroke-width="2.5" stroke-linecap="round"/></g>
</defs>`;

const svg = (body, label) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240" role="img" aria-label="${label}">
${defs}
<rect width="400" height="240" rx="16" fill="#ffffff"/>
${body}
</svg>
`;

const person = (x, y, s = 1) => `<use href="#p" transform="translate(${x},${y}) scale(${s})"/>`;
const grid = (x0, y0, cols, rows, dx, dy, s = 1) => {
  let out = "";
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) out += person(x0 + c * dx, y0 + r * dy, s);
  return out;
};
const text = (x, y, t, size = 22, weight = 700, anchor = "middle") =>
  `<text x="${x}" y="${y}" font-family="Segoe UI, Arial, sans-serif" font-size="${size}" font-weight="${weight}" fill="${INK}" text-anchor="${anchor}">${t}</text>`;
const band = (x1, x2, y, color = BLUE, h = 18) =>
  `<rect x="${x1}" y="${y - h / 2}" width="${x2 - x1}" height="${h}" rx="${h / 2}" fill="${color}"/>`;
const axis = (y, x1 = 40, x2 = 360) => `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="${INK}" stroke-width="3" stroke-linecap="round"/>`;
const tick = (x, y, label) =>
  `<line x1="${x}" y1="${y - 8}" x2="${x}" y2="${y + 8}" stroke="${INK}" stroke-width="3"/>${text(x, y + 32, label, 20, 600)}`;
const arrow = (x1, x2, y, color = INK) => {
  const dir = Math.sign(x2 - x1);
  return `<line x1="${x1}" y1="${y}" x2="${x2 - dir * 4}" y2="${y}" stroke="${color}" stroke-width="4" stroke-linecap="round"/>
<path d="M${x2},${y} l${-dir * 14},-9 v18 z" fill="${color}"/>`;
};

const pictos = {
  "coffee-samples": svg(
    `<rect x="16" y="16" width="176" height="208" rx="14" fill="none" stroke="${GREY}" stroke-width="2"/>
<rect x="208" y="16" width="176" height="208" rx="14" fill="none" stroke="${GREY}" stroke-width="2"/>
${grid(44, 66, 5, 2, 30, 48)}${grid(236, 66, 5, 2, 30, 48)}
<use href="#cup" transform="translate(52,160)"/>${text(130, 190, "2", 44, 800)}
<use href="#cup" transform="translate(244,160)"/>${text(322, 190, "3", 44, 800)}`,
    "Δύο ομάδες με 10 ανθρώπους. Η πρώτη πίνει 2 καφέδες, η δεύτερη 3.",
  ),
  "small-group": svg(`${person(160, 140, 2.4)}${person(200, 130, 2.6)}${person(240, 140, 2.4)}`, "Λίγοι άνθρωποι."),
  "big-crowd": svg(grid(60, 52, 8, 4, 40, 50, 1), "Πολλοί άνθρωποι."),
  interval: svg(
    `${axis(140)}${[0, 1, 2, 3, 4].map((v) => tick(40 + v * 80, 140, v)).join("")}
${band(160, 240, 100, BLUE, 22)}<circle cx="200" cy="100" r="9" fill="#ffffff" stroke="${BLUE}" stroke-width="4"/>
${text(160, 66, "1,5", 22)}${text(240, 66, "2,5", 22)}`,
    "Γραμμή με αριθμούς. Το διάστημα πάει από 1,5 μέχρι 2,5.",
  ),
  "confidence-95": svg(
    `<line x1="200" y1="34" x2="200" y2="226" stroke="${INK}" stroke-width="3" stroke-dasharray="8 6"/>
${text(200, 26, "πραγματικός αριθμός", 18, 700)}
${Array.from({ length: 19 }, (_, i) => {
  const y = 46 + i * 9.6;
  const miss = i === 12;
  const shift = [-20, 14, -6, 22, -14, 6, -24, 10, -2, 18, -10, 4, 0, -18, 12, -8, 20, -4, 8][i];
  const x1 = miss ? 222 : 150 + shift, x2 = miss ? 302 : 230 + shift;
  return miss
    ? `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="${GREY}" stroke-width="5" stroke-linecap="round" stroke-dasharray="6 5"/>`
    : `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="${BLUE}" stroke-width="5" stroke-linecap="round"/>`;
}).join("")}`,
    "Πολλές γραμμές. Σχεδόν όλες περνούν από τον πραγματικό αριθμό. Μία δεν περνά.",
  ),
  margin: svg(
    `${axis(170)}${tick(120, 170, "1,5")}${tick(200, 170, "2")}${tick(280, 170, "2,5")}
<circle cx="200" cy="100" r="10" fill="${BLUE}"/>${arrow(194, 124, 100)}${arrow(206, 276, 100)}
${text(158, 80, "− 0,5", 20)}${text(242, 80, "+ 0,5", 20)}`,
    "Από τη μέση τιμή 2 πάμε 0,5 αριστερά και 0,5 δεξιά.",
  ),
  "coffee-10-vs-100": svg(
    `<rect x="16" y="16" width="150" height="208" rx="14" fill="none" stroke="${GREY}" stroke-width="2"/>
<rect x="182" y="16" width="202" height="208" rx="14" fill="none" stroke="${GREY}" stroke-width="2"/>
${grid(38, 70, 5, 2, 26, 48, 0.9)}<use href="#cup" transform="translate(60,160)"/>${text(91, 214, "10", 26, 800)}
${grid(196, 40, 10, 10, 19.5, 15.5, 0.42)}${text(283, 214, "100", 26, 800)}`,
    "Αριστερά 10 άνθρωποι. Δεξιά 100 άνθρωποι.",
  ),
  "interval-shrinks": svg(
    `${person(40, 82, 1)}${text(70, 88, "10", 22, 800, "start")}${band(120, 360, 76)}
${grid(26, 168, 3, 1, 16, 0, 0.6)}${text(70, 174, "100", 22, 800, "start")}${band(205, 275, 162)}
<line x1="240" y1="40" x2="240" y2="200" stroke="${INK}" stroke-width="2" stroke-dasharray="6 6"/>`,
    "Με 10 ανθρώπους το διάστημα είναι μακρύ. Με 100 ανθρώπους είναι κοντό.",
  ),
  "interval-narrow": svg(
    `${axis(150)}${band(165, 235, 110)}${arrow(70, 152, 110)}${arrow(330, 248, 110)}`,
    "Το διάστημα μικραίνει.",
  ),
  "interval-wide": svg(
    `${axis(150)}${band(80, 320, 110)}${arrow(150, 66, 70)}${arrow(250, 334, 70)}`,
    "Το διάστημα μεγαλώνει.",
  ),
  "interval-same": svg(
    `${axis(150)}${band(140, 260, 110)}${text(100, 120, "=", 44, 800)}${text(300, 120, "=", 44, 800)}`,
    "Το διάστημα μένει ίδιο.",
  ),
};

mkdirSync(OUT, { recursive: true });
for (const [name, content] of Object.entries(pictos)) writeFileSync(join(OUT, `${name}.svg`), content);

writeFileSync(
  join(OUT, "..", "icon.svg"),
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="96" fill="${BLUE}"/>
<rect x="96" y="336" width="72" height="80" rx="10" fill="#ffffff"/>
<rect x="184" y="272" width="72" height="144" rx="10" fill="#ffffff"/>
<rect x="272" y="208" width="72" height="208" rx="10" fill="#ffffff"/>
<rect x="360" y="144" width="72" height="272" rx="10" fill="#ffffff" opacity="0.55"/>
</svg>
`,
);
console.log(`Έτοιμα ${Object.keys(pictos).length} εικονογράμματα στο ${OUT}`);
