// Accessibility check with axe-core on every screen of the demo flow.
// Needs the backend running with demo data (python -m scripts.seed_demo --reset) and a built frontend.
//
//   node scripts/a11y-check.mjs [base-url] [screenshot-dir]
//   default base-url: http://127.0.0.1:8000
//
// Checks WCAG 2.0/2.1/2.2 A+AA, the AAA rules axe knows (e.g. 7:1 contrast) and best practices,
// on a phone and a laptop screen, in the normal and the high-contrast theme.

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

async function run(theme, device) {
  const settings = await api("/settings");
  await api("/settings", "PUT", { ...settings, highContrast: theme === "contrast", autoRead: false, onboarded: true });

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
  await go("/courses/1/level", "change-level");

  // Upload the demo chapter (same file twice is fine: it is not duplicated).
  await page.goto(`${BASE}/courses/1/upload`);
  await page.setInputFiles("#pdf", PDF);
  await check(page, "upload", theme, device);
  await page.getByRole("button", { name: "Ανέβασε", exact: true }).click();
  await page.getByRole("heading", { name: "Από πού θέλεις να ξεκινήσεις;" }).waitFor();
  await check(page, "start-level", theme, device);
  await page.getByRole("button", { name: /^Ναι, από το επίπεδο/ }).click();
  await page.getByRole("button", { name: "Ξεκίνα από την αρχή" }).waitFor();
  await check(page, "chapter", theme, device);

  // Study section 3.4 in Easy-to-Read.
  await page.getByRole("link", { name: /3\.4/ }).click();
  await page.getByText(/Μέρος 1 από/).waitFor();
  await check(page, "study-easy", theme, device);
  await page.getByRole("button", { name: "Πρωτότυπο" }).click();
  await check(page, "study-original", theme, device);
  await page.getByRole("button", { name: "Εύκολο κείμενο" }).click();
  while (await page.getByRole("button", { name: "Συνέχεια" }).isVisible()) {
    await page.getByRole("button", { name: "Συνέχεια" }).click();
  }
  await page.getByRole("button", { name: "Πάμε στις ερωτήσεις" }).click();

  // Questions: optional reminder of the strategy, then the hint ladder.
  await page.getByRole("heading", { level: 1, name: /Πριν τις ερωτήσεις|Ερώτηση 1/ }).waitFor();
  if (await page.getByRole("heading", { name: "Πριν τις ερωτήσεις" }).isVisible()) {
    await check(page, "strategy-reminder", theme, device);
    await page.getByRole("button", { name: "Πάμε στις ερωτήσεις" }).click();
  }
  await page.getByRole("button", { name: "Βοήθεια" }).waitFor();
  await check(page, "question", theme, device);
  await page.getByRole("button", { name: "Βοήθεια" }).click();
  await page.getByText("Υπόδειξη 1 από 4").waitFor();
  await page.getByRole("button", { name: "Βοήθεια" }).click();
  await page.getByText("Υπόδειξη 2 από 4").waitFor();
  await check(page, "question-hints", theme, device);
  const textbox = page.getByLabel("Γράψε την απάντησή σου με δικά σου λόγια");
  if (await textbox.isVisible()) {
    await textbox.fill("μικραίνει");
    await page.getByRole("button", { name: "Στείλε την απάντηση" }).click();
  } else {
    await page.getByRole("button", { name: "Το διάστημα μικραίνει" }).click();
  }
  await page.getByText("Σωστά. Το βρήκες.").waitFor();
  await check(page, "question-answered", theme, device);

  await go("/progress", "progress");
  await go("/settings", "settings");
  await go("/settings/text", "settings-text");
  await go("/settings/sound", "settings-sound");
  await go("/settings/supporter", "supporter");
  await go("/accessibility", "statement");
  await go("/welcome", "welcome");
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
console.log(`\n${results.length} οθόνες ελέγχθηκαν, ${total} προβλήματα.`);
process.exit(total ? 1 : 0);
