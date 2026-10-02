// Tests du QCM : moteur de correction (Node) puis parcours navigateur (Playwright).
//   node tools/test.js
// Playwright doit être résolvable (NODE_PATH vers un node_modules qui le contient).
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");

const FILE = path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(FILE, "utf8");
let failures = 0;
function check(name, fn) {
  try { fn(); console.log("  ok   " + name); }
  catch (e) { failures++; console.log("  FAIL " + name + "\n       " + e.message); }
}

// ------------------------------------------------------------ moteur
console.log("Moteur de correction");
const ctx = { module: {}, window: {} };
vm.createContext(ctx);
vm.runInContext(html.match(/<script>\/\*GRADING-START\*\/([\s\S]*?)<\/script>/)[1], ctx);
vm.runInContext(html.match(/<script>(window\.__PARTS__[\s\S]*?)<\/script>/)[1], ctx);
const G = ctx.module.exports, QCFG = ctx.window.__QCFG__, PARTS = ctx.window.__PARTS__;
const ids = Object.keys(QCFG);

check("49 questions, 5 parties, 1 point chacune", () => {
  assert.strictEqual(ids.length, 49);
  assert.strictEqual(PARTS.length, 5);
  ids.forEach((id) => assert.strictEqual(QCFG[id].pts, 1));
  PARTS.forEach((p) => assert.strictEqual(p.points, ids.filter((id) => QCFG[id].part === p.num).length));
});

const NUM = { q1_1: 4, q1_2: 8, q1_3: 256 };
check("questions numériques : justes, tolérances de saisie, fausses", () => {
  for (const [id, v] of Object.entries(NUM)) {
    const g = QCFG[id].grader;
    for (const ok of [String(v), " " + v + " ", v + " valeurs", v + ",0", "n = " + v]) assert.strictEqual(G.grade(ok, g).score, 1, id + " " + ok);
    for (const ko of [String(v + 1), String(v * 2), "0"]) assert.strictEqual(G.grade(ko, g).score, 0, id + " " + ko);
    assert.ok(G.grade("", g).invalid, id + " vide");
    assert.ok(G.grade("beaucoup", g).invalid, id + " non numérique");
  }
});

const letters = "abcdefghijkl".split("");
check("questions à choix : bonne sélection (triée ou non), sélections fausses", () => {
  ids.filter((id) => QCFG[id].grader.type === "code").forEach((id) => {
    const g = QCFG[id].grader, ans = g.equals[0].split("");
    assert.strictEqual(G.grade(ans.join(", "), g).score, 1, id + " juste");
    assert.strictEqual(G.grade(ans.slice().reverse().join(", "), g).score, 1, id + " ordre inversé");
    assert.strictEqual(G.grade(ans.join(", ").toUpperCase(), g).score, 1, id + " majuscules");
    const wrong = letters.find((l) => ans.indexOf(l) < 0);
    assert.strictEqual(G.grade(wrong, g).score, 0, id + " lettre fausse");
    assert.strictEqual(G.grade(ans.concat([wrong]).sort().join(", "), g).score, 0, id + " lettre en trop");
    if (ans.length > 1) assert.strictEqual(G.grade(ans.slice(1).join(", "), g).score, 0, id + " sélection incomplète");
  });
});

// ------------------------------------------------------------ navigateur
async function browser() {
  const { chromium } = require("playwright");
  const b = await chromium.launch();
  const url = "file://" + FILE;
  const errors = [];
  async function open() {
    const page = await b.newPage({ viewport: { width: 1280, height: 900 } });
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    page.on("dialog", (d) => d.accept());
    await page.goto(url);
    return page;
  }
  async function answer(page, id, wrong) {
    const g = QCFG[id].grader;
    if (g.type === "num") {
      await page.fill("#in-" + id, String(wrong ? g.value + 1 : g.value));
      return;
    }
    const ans = g.equals[0].split("");
    const pick = wrong ? [letters.find((l) => ans.indexOf(l) < 0)] : ans;
    for (const k of pick) await page.click("#" + id + ' .choice[data-k="' + k + '"]');
  }
  const out = path.join(__dirname, "..", "test-output");
  fs.mkdirSync(out, { recursive: true });

  console.log("Parcours entraînement");
  let page = await open();
  await page.screenshot({ path: path.join(out, "accueil.png"), fullPage: true });
  const homeOnly = (await page.isVisible("#home")) && !(await page.isVisible("main.page"));
  check("accueil seul visible avant le choix du mode", () => assert.ok(homeOnly));
  await page.click('[data-mode="training"]');
  // validation sans réponse
  await page.click("#q1_4 .btn-validate");
  const msg = await page.textContent("#q1_4 .q-msg");
  check("validation sans case cochée refusée avec un message", () => assert.match(msg, /Coche au moins/));
  const stillOpen = !(await page.isDisabled("#q1_4 .btn-validate"));
  check("question non verrouillée après un refus", () => assert.ok(stillOpen));
  // une fausse réponse pour vérifier le marquage
  await answer(page, "q4_3", true);
  await page.click("#q4_3 .btn-validate");
  const marks = await page.$$eval("#q4_3 .choice", (ls) => ls.map((l) => l.className));
  check("réponse fausse : proposition cochée en rouge, bonnes réponses oubliées signalées", () => {
    assert.ok(marks.some((c) => /c-bad/.test(c)));
    assert.strictEqual(marks.filter((c) => /c-missed/.test(c)).length, 3);
  });
  const lockedQ = (await page.isDisabled("#q4_3 .choice input >> nth=0")) && (await page.isDisabled("#q4_3 .btn-validate"));
  check("réponse verrouillée après validation", () => assert.ok(lockedQ));
  for (const id of ids) {
    if (id === "q4_3") continue;
    await answer(page, id, false);
    await page.click("#" + id + " .btn-validate");
  }
  const sc = await page.textContent("#score-val");
  const fin = await page.textContent("#recap .final-note");
  check("note provisoire et finale cohérentes avec une seule erreur", () => {
    // partie 4 : 12/13 -> 18,46 ; poids 20/60 -> 20 - 1,54/3 = 19,5
    assert.match(sc, /^19,5/);
    assert.match(fin, /^19,5\/20/);
  });
  const greens = await page.$$eval("#q1_4 .choice.c-good", (l) => l.length);
  check("bonnes réponses marquées en vert", () => assert.strictEqual(greens, 1));
  await page.screenshot({ path: path.join(out, "entrainement.png"), fullPage: true });
  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.pdf({ path: path.join(out, "copie-entrainement.pdf"), format: "A4" });
  const pmode = await page.textContent(".print-mode");
  check("impression entraînement : en-tête de copie et mode", () => assert.match(pmode, /entraînement/));
  await page.close();

  console.log("Parcours entraînement parfait");
  page = await open();
  await page.click('[data-mode="training"]');
  for (const id of ids) { await answer(page, id, false); await page.click("#" + id + " .btn-validate"); }
  const perfect = await page.textContent("#recap .final-note");
  check("sujet entièrement juste = 20/20", () => assert.strictEqual(perfect, "20,0/20"));
  await page.close();

  console.log("Parcours examen");
  page = await open();
  await page.click('[data-mode="exam"]');
  const examUi = !(await page.isVisible("#q1_4 .btn-validate")) && (await page.isVisible(".exam-block"));
  check("bouton Valider masqué et note masquée en examen", () => assert.ok(examUi));
  for (const id of ids.slice(0, 40)) await answer(page, id, false);
  // changement d'avis : réponses modifiables avant la remise
  await page.click('#q1_4 .choice[data-k="b"]');
  await page.click('#q1_4 .choice[data-k="a"]');
  const count = await page.textContent("#score-count");
  check("décompte des réponses renseignées", () => assert.match(count, /^40 réponse/));
  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  const nograde = await page.isVisible(".print-nograde");
  const explVisible = await page.$$eval(".q-expl", (els) => els.some((e) => getComputedStyle(e).display !== "none"));
  const markVisible = await page.$$eval(".cmark", (els) => els.some((e) => getComputedStyle(e).display !== "none"));
  check("impression avant remise : « copie non corrigée », aucune correction", () => {
    assert.ok(nograde); assert.ok(!explVisible); assert.ok(!markVisible);
  });
  await page.pdf({ path: path.join(out, "copie-examen-non-corrigee.pdf"), format: "A4" });
  await page.emulateMedia({ media: "screen" });
  await page.click("#exam-submit");
  const warn = await page.textContent("#exam-warn");
  check("confirmation en deux temps annonçant les réponses vides", () => assert.match(warn, /^9 réponse/));
  await page.click("#exam-submit");
  const examNote = await page.textContent("#recap .final-note");
  // parties 1 à 4 juste sauf partie 4 : 40 premières questions -> parties 1,2,3 complètes, partie 4 : 10/13
  // partie 5 : 0/6. Note = (15*20 + 10*20 + 5*20 + 20*(10/13*20) + 10*0)/60
  const expected = Math.round((15 * 20 + 10 * 20 + 5 * 20 + 20 * (10 / 13 * 20)) / 60 * 10) / 10;
  check("note examen pondérée attendue (" + expected + ")", () => assert.strictEqual(examNote, expected.toFixed(1).replace(".", ",") + "/20"));
  const lockedAll = await page.$$eval(".q-input, .choice input", (els) => els.every((e) => e.disabled));
  const emptyStatus = await page.textContent("#q5_1 .q-status");
  check("après remise : tout verrouillé, réponses vides signalées", () => {
    assert.ok(lockedAll); assert.match(emptyStatus, /Non répondue/);
  });
  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await page.pdf({ path: path.join(out, "copie-examen-corrigee.pdf"), format: "A4" });
  await page.emulateMedia({ media: "screen" });
  await page.screenshot({ path: path.join(out, "examen-corrige.png"), fullPage: true });
  await page.close();

  console.log("Affichage mobile");
  page = await b.newPage({ viewport: { width: 390, height: 800 } });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url);
  await page.click('[data-mode="training"]');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  check("pas de défilement horizontal à 390 px", () => assert.ok(!overflow));
  await page.screenshot({ path: path.join(out, "mobile.png") });
  await page.close();

  check("aucune erreur JavaScript", () => assert.deepStrictEqual(errors, []));
  await b.close();
}

browser().catch((e) => { failures++; console.log("  FAIL " + e.stack); }).then(() => {
  console.log(failures ? failures + " échec(s)" : "Tous les tests passent");
  process.exit(failures ? 1 : 0);
});
