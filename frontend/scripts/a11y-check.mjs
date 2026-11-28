// Accessibility check with axe-core on every screen of the demo flow, at every support level.
// Needs the backend running with demo data (python -m scripts.seed_demo --reset) and a built frontend.
//
//   node scripts/a11y-check.mjs [base-url] [screenshot-dir]
//   default base-url: http://127.0.0.1:8000
//
// Checks WCAG 2.0/2.1/2.2 A+AA, the AAA rules axe knows (e.g. 7:1 contrast) and best practices,
// on a phone and a laptop screen, in the normal and the high-contrast theme.
// Also checks that the accessibility settings look exactly the same at support levels 1-4.

import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const SHOTS = process.argv[3];
const PDF = resolve(dirname(fileURLToPath(import.meta.url)), "../../backend/demo/kefalaio-3-diastima-empistosynis.pdf");
const TAGS = ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"];

if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const results = [];
const problems = [];

async function check(page, name, theme, device) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(150);
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  results.push({ name, theme, device, violations });
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `${device}-${theme}-${name}.png`), fullPage: true });
}

async function api(path, method = "GET", body) {
  const r = await fetch(`${BASE}/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.status === 204 ? null : r.json();
}

const setLevel = (sectionId, level) => api(`/sections/${sectionId}/level`, "POST", { level, reason: "manual" });

async function run(theme, device) {
  const settings = await api("/settings");
  const chosen = { ...settings, fontScale: 1.25, lineSpacing: 2, highContrast: theme === "contrast", autoRead: false, onboarded: true };
  await api("/settings", "PUT", chosen);

  const browser = await chromium.launch();
  const viewport = device === "phone" ? { width: 390, height: 844 } : { width: 1280, height: 900 };
  const context = await browser.newContext({ viewport, locale: "el-GR" });
  const page = await context.newPage();
  const go = async (path, name) => {
    await page.goto(`${BASE}${path}`);
    await check(page, name, theme, device);
  };

  await go("/", "courses");
  await go("/courses/new", "new-course");
  await go("/courses/1", "course");

  // Upload: straight to the sections, no placement question.
  await page.goto(`${BASE}/courses/1/upload`);
  await page.setInputFiles("#pdf", PDF);
  await check(page, "upload", theme, device);
  await page.getByRole("button", { name: "Ανέβασε", exact: true }).click();
  await page.getByRole("button", { name: "Ξεκίνα από την αρχή" }).waitFor();
  await check(page, "chapter", theme, device);
  const chapterId = page.url().split("/").pop();
  const chapter = await api(`/documents/${chapterId}`);
  const sec = Object.fromEntries(chapter.sections.map((s) => [s.number, s.id]));

  // --- Level 1 (3.4): Easy-to-Read, explaining hints -------------------------------------------
  await setLevel(sec["3.4"], 1);
  await go(`/sections/${sec["3.4"]}`, "study-level1");
  await page.getByRole("button", { name: "Επίπεδο 3" }).click();
  await check(page, "study-preview-level3", theme, device);
  await page.goto(`${BASE}/sections/${sec["3.4"]}/questions`);
  await page.getByRole("button", { name: "Βοήθεια" }).waitFor();
  await page.getByRole("button", { name: "Βοήθεια" }).click();
  await page.getByText("Υπόδειξη 1 από 4").waitFor();
  await page.getByRole("button", { name: "Βοήθεια" }).click();
  await page.getByText("Υπόδειξη 2 από 4").waitFor();
  await check(page, "question-level1-hints", theme, device);
  await page.getByRole("button", { name: "Το διάστημα μικραίνει" }).click();
  await page.getByText("Σωστά. Το βρήκες.").waitFor();
  await check(page, "question-level1-answered", theme, device);

  // --- Same topic (3.2): a proposal; the student says yes -------------------------------------
  await page.goto(`${BASE}/sections/${sec["3.2"]}`);
  const yes = page.getByRole("button", { name: "Ναι, ας δοκιμάσω" });
  await page.getByRole("link", { name: "Άλλαξε επίπεδο" }).waitFor();
  if (await yes.isVisible().catch(() => false)) {
    await check(page, "study-same-topic-proposal", theme, device);
    await yes.click();
    await page.getByText("Επίπεδο 3 από 4:").first().waitFor();
  } else {
    await setLevel(sec["3.2"], 3);
    await page.reload();
  }
  await check(page, "study-level3-original-first", theme, device);

  // --- Level 3 (3.2): hints point into the original; pick the sentence ------------------------
  await page.goto(`${BASE}/sections/${sec["3.2"]}/questions`);
  await page.getByRole("heading", { level: 1, name: /Πριν τις ερωτήσεις|Ερώτηση 1/ }).waitFor();
  if (await page.getByRole("heading", { name: "Πριν τις ερωτήσεις" }).isVisible()) {
    await page.getByRole("button", { name: "Πάμε στις ερωτήσεις" }).click();
  }
  await page.getByRole("button", { name: "Βοήθεια" }).waitFor();
  for (const step of [1, 2, 3]) {
    await page.getByRole("button", { name: "Βοήθεια" }).click();
    await page.getByText(`Ψάξε στο κείμενο: βήμα ${step} από 3`).waitFor();
  }
  await check(page, "question-level3-pick", theme, device);
  await page.locator(".sentence-btn").nth(1).click();
  await page.getByText("Δεν είναι αυτή.", { exact: false }).waitFor();
  await page.locator(".sentence-btn").nth(0).click();
  await page.getByText("Τη βρήκες. Τώρα απάντησε").waitFor();
  await check(page, "question-level3-found", theme, device);
  await page.getByLabel("Γράψε την απάντησή σου με δικά σου λόγια").fill("ένα εύρος τιμών");
  await page.getByRole("button", { name: "Στείλε την απάντηση" }).click();
  await page.getByText("Σωστά. Το βρήκες.").waitFor();
  await check(page, "question-level3-answered", theme, device);

  // --- Level 4 (3.3): key points, own question, exam practice ---------------------------------
  await setLevel(sec["3.3"], 4);
  await go(`/sections/${sec["3.3"]}`, "study-level4");
  await go(`/sections/${sec["3.3"]}/questions`, "level4-menu");
  await page.getByRole("button", { name: "Γράψε τα βασικά σημεία" }).click();
  await page.getByLabel("Γράψε με δικά σου λόγια τα βασικά σημεία της ενότητας").fill("Μέση τιμή μείον και συν το περιθώριο.");
  await page.getByRole("button", { name: "Δες τι περιμέναμε" }).click();
  await page.getByText("Τα είχες;").waitFor();
  await check(page, "level4-keypoints", theme, device);
  await page.goto(`${BASE}/sections/${sec["3.3"]}/questions`);
  await page.getByRole("button", { name: "Γράψε μια δική σου ερώτηση" }).click();
  await check(page, "level4-own-question", theme, device);
  await page.goto(`${BASE}/sections/${sec["3.3"]}/exam`);
  await page.getByText("Ναι, θέλω χρονόμετρο").click();
  await check(page, "exam-setup", theme, device);
  await page.getByRole("button", { name: "Ξεκίνα" }).click();
  await page.getByLabel("Η απάντησή σου").waitFor();
  await check(page, "exam-question", theme, device);
  await go(`/sections/${sec["3.3"]}/level`, "change-level");

  // --- Accessibility settings are the same at every support level ------------------------------
  const looks = [];
  for (const level of [1, 2, 3, 4]) {
    await setLevel(sec["3.4"], level);
    await page.goto(`${BASE}/sections/${sec["3.4"]}`);
    await page.getByRole("heading", { level: 1 }).waitFor();
    looks.push(await page.evaluate(() => ({
      font: getComputedStyle(document.documentElement).fontSize,
      line: getComputedStyle(document.body).lineHeight,
      contrast: document.documentElement.classList.contains("high-contrast"),
      motion: document.documentElement.classList.contains("reduce-motion"),
    })));
  }
  if (new Set(looks.map((l) => JSON.stringify(l))).size !== 1) {
    problems.push(`[${device}/${theme}] settings differ between levels: ${JSON.stringify(looks)}`);
  }
  const saved = await api("/settings");
  if (JSON.stringify(saved) !== JSON.stringify(chosen)) problems.push(`[${device}/${theme}] settings changed: ${JSON.stringify(saved)}`);
  await setLevel(sec["3.4"], 1);

  await go("/progress", "progress");
  await go("/settings", "settings");
  await go("/settings/text", "settings-text");
  await go("/settings/sound", "settings-sound");
  await go("/settings/supporter", "supporter");
  await go("/accessibility", "statement");
  const supporter = await api("/supporters", "POST", { name: "Έλεγχος" });
  await go(`/shared/${supporter.token}`, "shared");
  await api(`/supporters/${supporter.id}`, "DELETE");
  await go("/nothing-here", "not-found");

  await browser.close();
  await api("/settings", "PUT", { ...settings, onboarded: true });
}

for (const theme of ["normal", "contrast"]) {
  for (const device of ["phone", "laptop"]) await run(theme, device);
}

let total = 0;
for (const r of results) {
  for (const v of r.violations) {
    total += 1;
    const where = v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ");
    console.log(`[${r.device}/${r.theme}] ${r.name}: ${v.id} (${v.impact}) ${v.help} -> ${v.nodes.length} × ${where}`);
  }
}
problems.forEach((p) => console.log(p));
console.log(`\n${results.length} οθόνες ελέγχθηκαν, ${total} προβλήματα axe, ${problems.length} προβλήματα ρυθμίσεων.`);
process.exit(total || problems.length ? 1 : 0);
