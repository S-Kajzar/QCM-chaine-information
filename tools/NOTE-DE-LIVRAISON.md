# Note de livraison — QCM « La chaîne d'information »

`index.html` est généré par `python3 tools/build.py` à partir de :

- `tools/gabarit-exercice-interactif.html` : charte graphique et moteur repris tels quels ;
- `tools/questions.json` : énoncés, propositions, réponses et explications.

Tests : `NODE_PATH=$(npm root -g) node tools/test.js`. Le script teste le moteur de correction en Node, puis les parcours entraînement, examen, impression et mobile avec Playwright. Les captures et les PDF sont écrits dans `test-output/`, un dossier ignoré par git.

## Écarts par rapport au gabarit

- **Questions à choix.** Le moteur du gabarit ne corrige que des champs texte. Les propositions à cocher reposent donc sur une petite extension séparée (un bloc `<style>` et un `<script>` « QCM », placés après ceux du gabarit) :
  - les cases cochées sont recopiées, triées, dans le champ `.q-input` (masqué) ;
  - ce champ est corrigé par le type `code` du moteur ;
  - après correction, l'extension marque chaque proposition : juste, fausse ou bonne réponse oubliée.

  Le bloc de style, le moteur Grading et le moteur applicatif du gabarit ne sont pas modifiés.
- **`CONSEIL_MIN`.** Cette constante est passée de 300 à 60 min. C'est la durée conseillée du sujet, au-delà de laquelle le chronomètre vire au jaune.
- **Pas de document ni de tracé.** C'est un QCM de connaissances, donc :
  - le rail d'onglets et le bouton « Documents » sont masqués ;
  - le panneau reste dans la page, vide, parce que le moteur en a besoin ;
  - les chiffres clés de l'accueil affichent « 49 questions » et « Sans document » à la place des nombres de documents et de tracés.
- **Illustration d'accueil.** Il n'y a pas de dossier de présentation, donc l'illustration est un schéma SVG intégré. Il montre la grandeur physique, le signal numérisé, le mot binaire et le traitement logique, sans dévoiler de réponse.

## Barème

| Partie | Questions | Durée conseillée | Poids |
|---|---|---|---|
| 1 — Numération et codage | 15 | 15 min | 25,0 % |
| 2 — Portes logiques | 10 | 10 min | 16,7 % |
| 3 — Tables de vérité | 5 | 5 min | 8,3 % |
| 4 — Conversion A/N | 13 | 20 min | 33,3 % |
| 5 — Capteurs | 6 | 10 min | 16,7 % |

- Le sujet d'origine n'indique pas de durées : elles ont été fixées à environ 1 min par question, et 1 min 30 pour la partie 4, qui demande des calculs (quantum, intervalles du CAN, sorties du CNA).
- Chaque question vaut 1 point.
- Les questions à plusieurs réponses (Q4.2, Q4.3, Q4.5, Q5.1) sont notées en tout ou rien, comme dans la version précédente.
- Aucune question ne porte d'unité : les trois questions numériques (Q1.1 à Q1.3) attendent un nombre de valeurs, sans demi-point d'unité.

## Corrections apportées au contenu

- **Q1.5** : les propositions a et d étaient identiques (« 10 symboles »). La d devient « 16 symboles ».
- **Q2.1 à Q2.10** : « la porte logique ci-contre » devient « ci-dessous », car le symbole est maintenant placé sous l'énoncé.
- **Q5.5** : la proposition a « détecter » devient « acquérir (détecter) », pour reprendre le nom de la fonction de la chaîne d'information (acquérir, traiter, communiquer).
- **Q1.12** : coquille « héxa » corrigée en « hexa » dans l'explication.
- Les renvois « voir note de livraison » ont été retirés des explications affichées aux élèves.

## Décisions d'interprétation conservées

- **Q1.15** (`01001110`) : réponse « on ne peut pas savoir ». Sans indice de base, ce nombre est aussi valide en décimal et en hexadécimal.
- **Q4.5** : la réponse « un signal numérique est moins précis qu'un signal analogique » est conservée (perte liée à la quantification). Cette formulation reste discutable.
- **Q4.6** : le quantum vaut q = U_ref / 2ⁿ = 2 V. C'est la convention du cours ; avec q = U_ref / (2ⁿ − 1), on obtiendrait 2,29 V, qui n'est pas proposé.
- **Q5.1** : la réponse retenue est a, b, e, f. La résistance (d) n'est pas retenue comme grandeur de sortie, et l'explication précise que certains cours l'acceptent pour les capteurs résistifs.

## Points vérifiés par les tests

- Chaque question a une réponse juste et des réponses fausses testées : lettre fausse, lettre en trop, sélection incomplète, ordre et casse.
- Une réponse validée est verrouillée.
- Un sujet entièrement juste donne 20/20, et la note pondérée est contrôlée avec une erreur en entraînement et avec des réponses vides en examen.
- En mode examen :
  - la note et les corrections restent masquées jusqu'à la remise, y compris à l'impression (mention « Copie non corrigée ») ;
  - la remise demande une confirmation en deux temps qui annonce le nombre de réponses vides.
- Aucune erreur JavaScript, et pas de défilement horizontal à 390 px.
