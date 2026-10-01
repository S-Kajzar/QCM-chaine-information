#!/usr/bin/env python3
"""Génère index.html à partir du gabarit et du contenu du QCM.

    python3 tools/build.py

Le bloc <style>, le moteur Grading et le moteur applicatif sont repris du
gabarit sans modification (seule la constante CONSEIL_MIN, durée conseillée
qui fait virer le chronomètre au jaune, est ajustée au sujet). Les questions
à choix multiples s'appuient sur une petite extension séparée (style et
script « QCM ») qui coche les propositions et recopie les lettres choisies
dans le champ .q-input que le moteur corrige avec le type « code ».
"""
import base64
import html
import itertools
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GABARIT = os.path.join(HERE, "gabarit-exercice-interactif.html")
QUESTIONS = os.path.join(HERE, "questions.json")
OUT = os.path.join(ROOT, "index.html")

TITLE = "La chaîne d'information"

# Parties : le numéro d'origine de la section (« 1 — … ») sert de clé.
PARTS = [
    {"num": "1", "title": "Numération et codage", "minutes": 15,
     "intro": "Bases 2, 10 et 16 : compter les valeurs codables, convertir d'une base à l'autre, "
              "reconnaître bits et octets."},
    {"num": "2", "title": "Portes logiques : identification du symbole", "minutes": 10,
     "intro": "Chaque symbole est dessiné soit selon la norme européenne (cadre rectangulaire et "
              "signe intérieur), soit selon la norme américaine (formes distinctives). Identifie la "
              "fonction et la norme."},
    {"num": "3", "title": "Tables de vérité", "minutes": 5,
     "intro": "Pour chaque fonction logique à deux entrées, retrouve la table de vérité parmi les "
              "cinq proposées."},
    {"num": "4", "title": "Échantillonnage et conversion analogique / numérique", "minutes": 20,
     "intro": "Échantillonnage, résolution, quantum : du signal analogique au mot binaire (CAN) "
              "et retour (CNA)."},
    {"num": "5", "title": "Les capteurs", "minutes": 10,
     "intro": "Nature du signal délivré, principes de détection et place du capteur dans la "
              "chaîne d'information."},
]
TOTAL_MIN = sum(p["minutes"] for p in PARTS)


def hm(minutes):
    h, m = divmod(minutes, 60)
    return "%d h %02d" % (h, m) if h else "%d min" % m


def fr_pct(x):
    return ("%.1f" % x).replace(".", ",")


# ---------------------------------------------------------------- gabarit
def gabarit_blocks(src):
    style = re.search(r"<style>:root\{.*?</style>", src, re.S).group(0)
    grading = re.search(r"<script>/\*GRADING-START\*/.*?</script>", src, re.S).group(0)
    app = re.search(r"<script>\(function \(\) \{.*</script>", src, re.S).group(0)
    assert app.count("var CONSEIL_MIN = 300;") == 1
    app = app.replace("var CONSEIL_MIN = 300;", "var CONSEIL_MIN = %d;" % TOTAL_MIN)
    return style, grading, app


# ---------------------------------------------------------------- illustration d'accueil
def hero_svg():
    W, H = 960, 330
    enc, jau, bleu, trait = "#1C2530", "#F2B705", "#1F5FA8", "#A5ADAA"
    ft = "Bahnschrift,'DIN Alternate','Roboto Condensed','Arial Narrow',sans-serif"
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
         '<rect width="%d" height="%d" fill="#fff"/>' % (W, H)]
    # quadrillage léger
    for x in range(0, W + 1, 24):
        s.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#EEF0EC"/>' % (x, x, H))
    for y in range(0, H + 1, 24):
        s.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="#EEF0EC"/>' % (y, W, y))
    boxes = [("1", "Grandeur physique"), ("2", "Signal numérisé"),
             ("3", "Mot binaire"), ("4", "Traitement logique")]
    bw, bh, gap, x0, y0 = 196, 210, 42, 22, 60
    for i, (n, lab) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        s.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fff" stroke="%s" stroke-width="2.5"/>' % (x, y0, bw, bh, enc))
        s.append('<rect x="%d" y="%d" width="%d" height="34" fill="%s"/>' % (x, y0, bw, enc))
        s.append('<rect x="%d" y="%d" width="34" height="34" fill="%s"/>' % (x, y0, jau))
        s.append('<text x="%d" y="%d" font-family="%s" font-weight="700" font-size="20" fill="%s" text-anchor="middle">%s</text>' % (x + 17, y0 + 24, ft, enc, n))
        s.append('<text x="%d" y="%d" font-family="%s" font-weight="700" font-size="15" fill="#fff">%s</text>' % (x + 44, y0 + 23, ft, html.escape(lab)))
        if i < 3:
            ax = x + bw + 4
            ay = y0 + bh / 2 + 17
            s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>' % (ax, ay, ax + gap - 18, ay, enc))
            s.append('<path d="M%d %d l-13 -8 v16 z" fill="%s"/>' % (ax + gap - 6, ay, enc))
    # 1 : courbe continue
    import math
    x = x0
    pts = []
    for k in range(0, 161):
        t = k / 160
        pts.append("%.1f,%.1f" % (x + 18 + t * 160, y0 + 135 - 58 * math.sin(t * 2 * math.pi * 1.25) * (0.6 + 0.4 * t)))
    s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (x + 14, y0 + 135, x + 182, y0 + 135, trait))
    s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3.5" stroke-linecap="round"/>' % (" ".join(pts), bleu))
    # 2 : signal en escalier
    x = x0 + (bw + gap)
    base = y0 + 190
    s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (x + 16, base, x + 182, base, trait))
    s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (x + 16, base, x + 16, y0 + 50, trait))
    levels = [3, 5, 6, 6, 5, 3, 1, 0, 1, 3]
    d = []
    for k, lv in enumerate(levels):
        xa, xb = x + 18 + k * 16, x + 18 + (k + 1) * 16
        yy = base - 12 - lv * 17
        d.append(("M" if k == 0 else "L") + "%d %d L%d %d" % (xa, yy, xb, yy))
    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="3"/>' % (" ".join(d), enc))
    # 3 : bits
    x = x0 + 2 * (bw + gap)
    bits = "01101001"
    for k, b in enumerate(bits):
        bx = x + 14 + (k % 4) * 43
        by = y0 + 62 + (k // 4) * 62
        on = b == "1"
        s.append('<rect x="%d" y="%d" width="38" height="50" fill="%s" stroke="%s" stroke-width="2"/>' % (bx, by, jau if on else "#fff", enc))
        s.append('<text x="%d" y="%d" font-family="%s" font-weight="700" font-size="30" fill="%s" text-anchor="middle">%s</text>' % (bx + 19, by + 36, ft, enc, b))
    s.append('<text x="%d" y="%d" font-family="%s" font-size="15" fill="#46525C" text-anchor="middle">1 octet = 8 bits</text>' % (x + bw / 2, y0 + 196, ft))
    # 4 : circuit
    x = x0 + 3 * (bw + gap)
    cx, cy = x + 98, y0 + 125
    for k in range(4):
        yy = cy - 42 + k * 28
        s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>' % (cx - 78, yy, cx - 46, yy, enc))
        s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>' % (cx + 46, yy, cx + 78, yy, enc))
    s.append('<rect x="%d" y="%d" width="92" height="120" fill="%s"/>' % (cx - 46, cy - 60, enc))
    s.append('<circle cx="%d" cy="%d" r="6" fill="%s"/>' % (cx - 30, cy - 44, jau))
    s.append('<text x="%d" y="%d" font-family="%s" font-weight="700" font-size="22" fill="%s" text-anchor="middle">μC</text>' % (cx, cy + 8, ft, jau))
    s.append('</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode("".join(s).encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------- questions
def letters_label(keys):
    keys = list(keys)
    if len(keys) == 1:
        return keys[0]
    return ", ".join(keys[:-1]) + " et " + keys[-1]


def build_questions(raw):
    qcfg, by_part = {}, {p["num"]: [] for p in PARTS}
    counters = {p["num"]: 0 for p in PARTS}
    for q in raw:
        part = q["sec"].split(" ")[0]
        counters[part] += 1
        qid = "q%s_%d" % (part, counters[part])
        label = "Q%s.%d" % (part, counters[part])
        q = dict(q, id=qid, label=label, part=part)
        if q["type"] == "number":
            grader = {"type": "num", "value": float(q["accept"][0]), "absTol": 0}
        else:
            ans = "".join(sorted(q["accept"]))
            # Les lettres sont recopiées triées dans le champ ; les permutations
            # restent acceptées si la saisie arrive dans un autre ordre.
            perms = sorted({"".join(p) for p in itertools.permutations(ans)})
            perms.remove(ans)
            grader = {"type": "code", "equals": [ans] + perms}
        qcfg[qid] = {"label": label, "part": part, "pts": 1, "grader": grader}
        by_part[part].append(q)
    return qcfg, by_part


def split_enonce(enonce):
    """Sépare le texte de l'énoncé de l'éventuelle figure (symbole de porte)."""
    m = re.search(r'<img class="gate" alt="[^"]*" src="([^"]+)">', enonce)
    if not m:
        return enonce, None
    return enonce[:m.start()].strip(), m.group(1)


def q_html(q):
    qid, label = q["id"], q["label"]
    stem, img = split_enonce(q["enonce"])
    out = ['<div class="q%s" id="%s" data-q="%s">' % ("" if q["type"] == "number" else " q-choice", qid, qid),
           '  <p class="q-stem"><span class="q-num">%s</span> <strong>%s</strong></p>' % (label, stem)]
    if img:
        out.append('  <figure class="gate-fig"><img src="%s" alt="Symbole de porte logique à identifier (%s)"></figure>' % (img, label))
    if q["type"] == "number":
        hint = "Réponds par un nombre entier."
        inp_attr = ""
    elif q["multi"]:
        hint = ("Plusieurs propositions sont justes : coche toutes les bonnes réponses, et seulement elles. "
                "La question n'est juste que si la sélection est exacte.")
        inp_attr = ' readonly tabindex="-1" aria-hidden="true"'
    else:
        hint = "Une seule proposition est juste : coche-la."
        inp_attr = ' readonly tabindex="-1" aria-hidden="true"'
    out.append('  <p class="q-hint" id="h-%s">%s</p>' % (qid, hint))
    if q["type"] != "number":
        kind = "checkbox" if q["multi"] else "radio"
        has_table = any("<table" in c[1] for c in q["choices"])
        many = len(q["choices"]) >= 8
        cls = "choices" + (" cards" if has_table else (" cols2" if many else ""))
        role = "group" if q["multi"] else "radiogroup"
        out.append('  <div class="%s" role="%s" aria-labelledby="h-%s">' % (cls, role, qid))
        for k, txt in q["choices"]:
            txt = txt.replace('class="tt"', 'class="t tt"')
            out.append('    <label class="choice" data-k="%s"><input type="%s" name="c-%s" value="%s">'
                       '<span class="ck">%s</span><span class="ct">%s</span><span class="cmark" aria-hidden="true"></span></label>'
                       % (k, kind, qid, k, k, txt))
        out.append('  </div>')
    out.append('  <div class="q-row">')
    out.append('    <input type="text" class="q-input%s" id="in-%s" aria-label="Réponse %s" aria-describedby="h-%s" '
               'autocomplete="off" autocapitalize="off" spellcheck="false"%s%s>'
               % ("" if q["type"] == "number" else " q-input-choice", qid, label, qid,
                  ' inputmode="numeric"' if q["type"] == "number" else "", inp_attr))
    out.append('    <button type="button" class="btn btn-validate">Valider</button>')
    out.append('    <span class="q-status" aria-live="polite"></span>')
    out.append('    <span class="print-only pstat">Non validée : comptée fausse</span>')
    out.append('  </div>')
    out.append('  <p class="q-msg" role="alert"></p>')
    out.append('  <div class="q-expl" hidden>')
    out.append('    <p class="q-unit-msg" hidden></p>')
    if q["type"] == "number":
        expected = q["accept"][0]
    else:
        keys = sorted(q["accept"])
        texts = dict(q["choices"])
        if any("<table" in texts[k] for k in keys):
            expected = "table " + letters_label(keys)
        elif len(keys) == 1:
            expected = "%s — %s" % (keys[0], texts[keys[0]])
        else:
            expected = letters_label(keys)
    out.append('    <p class="q-expected"><span>Réponse attendue :</span> %s</p>' % expected)
    out.append('    <div class="q-why"><p>%s</p></div>' % q["expl"])
    out.append('  </div>')
    out.append('</div>')
    return "\n".join("        " + l for l in out)


def part_html(p, questions):
    pts = len(questions)
    weight = p["minutes"] / TOTAL_MIN * 100
    body = "\n".join(q_html(q) for q in questions)
    return """  <section class="part" id="partie-{n}" aria-labelledby="t-partie-{n}">
    <header class="part-head"><div class="part-num" aria-hidden="true">{n}</div>
      <div><h2 id="t-partie-{n}"><span class="sr-only">Partie {n} : </span>{t}</h2>
        <div class="duree">Durée conseillée : {d} · Barème : {pts} points, soit {w} % de la note</div></div></header>
    <div class="part-body">
      <p>{intro}</p>
{body}
    </div>
  </section>
""".format(n=p["num"], t=html.escape(p["title"], quote=False), d=hm(p["minutes"]), pts=pts,
           w=fr_pct(weight), intro=p["intro"], body=body)


# ---------------------------------------------------------------- extension QCM
QCM_STYLE = """<style>/* Extension QCM : propositions à cocher (le bloc de style du gabarit n'est pas modifié) */
.choices{display:grid; gap:6px; margin:6px 0 10px; max-width:74ch}
.choices.cols2{grid-template-columns:repeat(2,minmax(0,1fr))}
.choices.cards{grid-template-columns:repeat(auto-fill,minmax(146px,1fr)); max-width:none}
.choices.cards .choice .ct{flex-basis:100%}
@media (max-width:560px){ .choices.cols2{grid-template-columns:1fr} }
.choice{display:flex; gap:9px; align-items:flex-start; border:1.5px solid var(--trait); background:#fff; padding:7px 10px;
  cursor:pointer; border-radius:2px; transition:background .12s,border-color .12s}
.choices.cards .choice{flex-wrap:wrap; align-content:flex-start}
.choices.cards .choice .cmark{white-space:normal; align-self:auto}
.choice:hover{border-color:var(--encre); background:var(--jaune-pale)}
.choice.picked{border-color:var(--encre); background:var(--jaune-pale); box-shadow:inset 5px 0 0 var(--jaune)}
.choice input{margin:.22rem 0 0; width:17px; height:17px; flex:0 0 auto; accent-color:var(--encre); cursor:inherit}
.choice .ck{font:700 1rem/1.5 var(--f-titre); min-width:1em}
.choice .ct{flex:1; min-width:0}
.choice table.tt{width:auto; margin:2px 0 0; font-size:.86rem}
.choice table.tt th,.choice table.tt td{text-align:center; padding:2px 8px}
.choice .cmark{display:none; font:700 .8rem/1.3 var(--f-titre); padding:2px 7px; white-space:nowrap; align-self:center; border-radius:2px}
.q-choice.locked .choice{cursor:default}
.q-choice.locked .choice:hover{border-color:var(--trait); background:#fff}
.q-choice.locked .choice.c-good{border-color:var(--vert); background:var(--vert-pale); box-shadow:inset 5px 0 0 var(--vert)}
.q-choice.locked .choice.c-missed{border:1.5px dashed var(--vert); background:#fff; box-shadow:none}
.q-choice.locked .choice.c-bad{border-color:var(--rouge); background:var(--rouge-pale); box-shadow:inset 5px 0 0 var(--rouge)}
.q-choice .c-good .cmark,.q-choice .c-missed .cmark{display:inline-block; background:var(--vert); color:#fff}
.q-choice .c-bad .cmark{display:inline-block; background:var(--rouge); color:#fff}
.q-choice .q-input-choice{display:none!important}
.gate-fig{margin:8px 0 10px}
.gate-fig img{display:block; width:220px; max-width:60%; background:#fff; border:1px solid var(--trait-fin); padding:8px}
.rail{display:none!important}
.banner .btn-docs{display:none!important}
@media print{
  .choices{gap:3px}
  .choices.cols2{grid-template-columns:repeat(2,minmax(0,1fr))}
  .choice{padding:3px 8px; background:#fff!important; box-shadow:none!important; break-inside:avoid}
  .choice.picked{border:1.5px solid #000}
  .q-choice.locked .choice.c-good,.q-choice.locked .choice.c-bad{border:1.5px solid #000}
  .q-choice.locked .choice.c-missed{border:1.5px dashed #000}
  .q-choice .cmark{background:#fff!important; color:#000!important; border:1px solid #000}
  body:not(.corrections-open) .q-choice .cmark{display:none!important}
  body.corrections-open .q-choice:not(.locked) .choice.is-answer{border:1.5px dashed #000}
  body.corrections-open .q-choice:not(.locked) .choice.is-answer .cmark{display:inline-block}
  .gate-fig img{width:45mm}
}
</style>"""

QCM_SCRIPT = """<script>/* Extension QCM : coche des propositions -> lettres recopiées dans .q-input,
   puis affichage des bonnes et mauvaises propositions une fois la question corrigée. */
(function () {
  "use strict";
  var QCFG = window.__QCFG__;
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  $$(".q-choice[data-q]").forEach(function (root) {
    var id = root.getAttribute("data-q");
    var answer = QCFG[id].grader.equals[0].split("");
    var input = root.querySelector(".q-input");
    var boxes = $$(".choice input", root);
    var labels = $$(".choice", root);
    labels.forEach(function (l) {
      if (answer.indexOf(l.getAttribute("data-k")) >= 0) {
        l.classList.add("is-answer");
        l.querySelector(".cmark").textContent = "✓ bonne réponse";
      }
    });
    function sync() {
      var picked = boxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; }).sort();
      labels.forEach(function (l) { l.classList.toggle("picked", l.querySelector("input").checked); });
      input.value = picked.join(", ");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    boxes.forEach(function (b) { b.addEventListener("change", sync); });
    // Aucune proposition cochée : message adapté, la validation n'est pas transmise au moteur
    root.addEventListener("click", function (e) {
      if (!e.target.classList || !e.target.classList.contains("btn-validate")) return;
      if (input.value.trim()) return;
      e.stopPropagation();
      root.querySelector(".q-msg").textContent = "Coche au moins une proposition avant de valider.";
    }, true);
    function lock() {
      if (root.classList.contains("locked")) return;
      if (!/(^|\\s)is-(ok|ko|half)(\\s|$)/.test(root.className)) return;
      root.classList.add("locked");
      boxes.forEach(function (b) { b.disabled = true; });
      labels.forEach(function (l) {
        var k = l.getAttribute("data-k"), good = answer.indexOf(k) >= 0, picked = l.querySelector("input").checked;
        var mark = l.querySelector(".cmark");
        if (good && picked) { l.classList.add("c-good"); mark.textContent = "✓ ta réponse, juste"; }
        else if (good) { l.classList.add("c-missed"); mark.textContent = "✓ bonne réponse oubliée"; }
        else if (picked) { l.classList.add("c-bad"); mark.textContent = "✗ ta réponse, fausse"; }
      });
    }
    new MutationObserver(lock).observe(root, { attributes: true, attributeFilter: ["class"] });
  });
})();
</script>"""


# ---------------------------------------------------------------- page
def build():
    src = open(GABARIT, encoding="utf-8").read()
    style, grading, app = gabarit_blocks(src)
    raw = json.load(open(QUESTIONS, encoding="utf-8"))
    qcfg, by_part = build_questions(raw)
    nq = len(raw)
    parts_cfg = [{"num": p["num"], "title": p["title"], "minutes": p["minutes"],
                  "duration": hm(p["minutes"]), "points": len(by_part[p["num"]])} for p in PARTS]
    parts = "".join(part_html(p, by_part[p["num"]]) for p in PARTS)
    duree = hm(TOTAL_MIN)

    page = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Fichier généré par tools/build.py à partir de tools/gabarit-exercice-interactif.html
     et de tools/questions.json : modifier ces sources puis relancer le script. -->
<title>{title} — exercice interactif</title>
<meta name="description" content="QCM sur la chaîne d'information : numération et codage, portes logiques, tables de vérité, conversion analogique / numérique, capteurs.">
{style}
{qcm_style}
</head>
<body class="no-mode">

<!-- Aucun document de présentation ni dossier technique : QCM de connaissances.
     Le panneau reste en place car le moteur s'y appuie. -->
<nav class="rail" aria-label="Documents" hidden></nav>

<aside id="docpanel" aria-label="Documents du sujet" aria-hidden="true">
  <div class="dp-head">
    <h3 id="dp-title">Documents</h3>
    <button type="button" id="dp-out" aria-label="Réduire">−</button><span id="dp-zoom" class="small">100 %</span>
    <button type="button" id="dp-in" aria-label="Agrandir">+</button>
    <button type="button" id="dp-fit">Ajuster</button>
    <button type="button" id="dp-close">Fermer</button>
  </div>
  <div class="dp-body"></div>
</aside>

<section id="home" aria-labelledby="home-title">
  <div class="home-inner">
    <header class="home-head">
      <h1 id="home-title">{title}</h1>
      <p class="home-sub">De la grandeur physique au traitement logique : comment une information est codée en binaire, numérisée par un convertisseur, détectée par un capteur et traitée par des portes logiques. {nq} questions à choix ou à réponse courte, en cinq parties.</p>
    </header>
    <figure class="home-hero">
      <img src="{hero}" width="960" height="330" alt="Schéma : une grandeur physique continue est numérisée en un signal en escalier, codée en un mot binaire de 8 bits puis traitée par un microcontrôleur.">
      <figcaption class="small">Le parcours de l'information : grandeur physique, signal numérisé, mot binaire, traitement logique.</figcaption>
    </figure>
    <div class="home-facts">
      <div><b>5 parties</b><span>de la numération aux capteurs</span></div>
      <div><b>{duree}</b><span>durée conseillée, qui fixe la pondération</span></div>
      <div><b>{nq} questions</b><span>1 point chacune, réponses verrouillées</span></div>
      <div><b>Sans document</b><span>ni tracé : QCM de connaissances</span></div>
    </div>
    <h2 class="home-choose">Choisis ton mode de travail</h2>
    <div class="modes">
      <article class="mode-card">
        <div class="mc-head"><span class="mc-tag">Mode 1</span><h3>Mode entraînement</h3></div>
        <p class="mc-lead">Pour apprendre en avançant, question par question.</p>
        <ul><li>Chaque question se valide isolément ; la correction et sa justification s'affichent aussitôt.</li>
          <li>La note pondérée s'actualise en continu dans le bandeau.</li>
          <li>Le chronomètre tourne, sans contrainte de temps.</li></ul>
        <button type="button" class="btn btn-mode" data-mode="training">Commencer l'entraînement</button>
      </article>
      <article class="mode-card exam">
        <div class="mc-head"><span class="mc-tag">Mode 2</span><h3>Mode examen</h3></div>
        <p class="mc-lead">Pour se placer dans les conditions d'une évaluation.</p>
        <ul><li>Aucune correction et aucune note pendant la composition ; les réponses restent modifiables.</li>
          <li>Le chronomètre tourne, à comparer à la durée conseillée.</li>
          <li>En fin de sujet, le bouton « J'ai fini, je fais corriger ma copie » dévoile d'un coup les corrections, les notes par partie et la note globale.</li></ul>
        <button type="button" class="btn btn-mode" data-mode="exam">Composer en mode examen</button>
      </article>
    </div>
    <p class="home-note small">Le mode se choisit une seule fois : pour en changer, recharge la page. Rien n'est enregistré sur l'ordinateur.</p>
  </div>
</section>

<main class="page">
  <section class="print-only print-summary">
    <p>Élève : <span class="print-nom"></span> | Copie imprimée le <span class="print-date"></span></p>
    <p>Mode : <span class="print-mode"></span> | Temps de rédaction : <strong class="print-time"></strong> (durée conseillée : {duree})</p>
    <p class="print-note-line">Note finale pondérée : <strong class="final-note"></strong></p>
    <p class="print-nograde">Copie non corrigée : les corrections et la note n'apparaissent qu'après la remise de la copie en mode examen.</p>
  </section>

  <header class="cartouche">
    <div class="title">
      <h1>{title}</h1>
      <p>{nq} questions notées sur 1 point, réparties en 5 parties pondérées par leur durée.</p></div>
    <div class="nom"><label for="nom-eleve">Nom et prénom</label><input id="nom-eleve" type="text" autocomplete="name"></div>
  </header>

  <div class="consignes">
    <p class="only-training"><strong>Mode entraînement.</strong> Coche ta réponse (ou saisis-la) puis clique sur « Valider » : une réponse validée est définitive et sa correction s'affiche aussitôt.</p>
    <p class="only-exam"><strong>Mode examen.</strong> Compose tout le sujet sans correction ni note : tes réponses restent modifiables jusqu'au bout. Le bouton « J'ai fini, je fais corriger ma copie », en fin de sujet, dévoile d'un coup les corrections, les notes par partie et la note globale.</p>
    <p><strong>Une ou plusieurs réponses.</strong> La consigne de chaque question l'indique. Quand plusieurs propositions sont justes, la question ne rapporte son point que si tu coches toutes les bonnes réponses et aucune fausse.</p>
    <p>Les trois premières questions attendent un <strong>nombre entier</strong>, à saisir dans le champ.</p>
    <p><strong>Barème pondéré par la durée conseillée</strong> : chaque partie est notée sur 20, puis pèse au prorata de son temps. Le récapitulatif de fin de sujet donne le détail partie par partie.</p>
  </div>

{parts}
  <section class="recap" id="recap" aria-labelledby="t-recap">
    <header class="recap-head"><h2 id="t-recap">Récapitulatif et note finale</h2>
      <p class="small">Les questions non validées comptent comme fausses. Chaque partie est ramenée sur 20, puis pondérée par sa durée conseillée.</p></header>
    <div id="exam-submit-wrap">
      <p class="es-lead">Ta copie n'est pas encore corrigée : aucune réponse n'est verrouillée, tu peux encore revenir sur les questions.</p>
      <button type="button" class="btn btn-exam" id="exam-submit">J'ai fini, je fais corriger ma copie</button>
      <p class="es-warn" id="exam-warn" role="alert"></p>
    </div>
    <div id="recap-graded">
      <div class="recap-wrap">
        <table class="t recap-table">
          <thead><tr><th>Partie</th><th>Durée</th><th>Poids</th><th>Points</th><th>Note /20</th><th>Contribution</th></tr></thead>
          <tbody id="recap-body"></tbody>
          <tfoot><tr><th colspan="4">Note globale pondérée</th><th class="final-note"></th><th></th></tr></tfoot>
        </table>
      </div>
      <p class="final-detail small"></p>
    </div>
    <div class="recap-foot" id="recap-foot"><button type="button" class="btn btn-print">Imprimer ma copie</button>
      <span class="small no-print">L'impression reprend tes réponses, les corrections et ce récapitulatif.</span></div>
  </section>
</main>

<footer class="banner" aria-label="Suivi de la composition">
  <div class="score-block"><div class="lab">Note provisoire</div><div class="score" id="score-val">–<small>/20</small></div></div>
  <div class="exam-block"><div class="lab">Mode examen</div><div class="exam-state">Note masquée</div></div>
  <div class="timer-block"><div class="lab">Temps</div><div class="timer" id="timer-val">0:00:00</div></div>
  <div class="count" id="score-count" aria-live="polite"></div>
  <div class="spacer"></div>
  <button type="button" class="btn-docs" id="btn-docs">Documents</button>
</footer>

<!-- CONFIGURATION DU SUJET -->
<script>window.__PARTS__ = {parts_cfg};
window.__QCFG__ = {qcfg};
window.__SKCFG__ = {{}};</script>
{grading}
{app}
{qcm_script}
</body>
</html>
""".format(title=TITLE, style=style, qcm_style=QCM_STYLE, hero=hero_svg(), nq=nq, duree=duree,
           parts=parts, parts_cfg=json.dumps(parts_cfg, ensure_ascii=False),
           qcfg=json.dumps(qcfg, ensure_ascii=False), grading=grading, app=app, qcm_script=QCM_SCRIPT)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print("index.html : %d questions, %d parties, %s, %d octets" % (nq, len(PARTS), duree, len(page.encode("utf-8"))))


if __name__ == "__main__":
    build()
