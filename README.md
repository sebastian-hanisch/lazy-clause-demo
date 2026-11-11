# Lazy Clause Generation – ein Propagator erklärt seinen Schluss – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-lazy-clause-demo.streamlit.app/)** -->

Stück der **sat-constraint-programming**-Linie in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“, Konvergenz des SAT-Arms (Stück 1, Konfliktklauseln lernen) und des CP-Arms (Stück 10, AllDifferent, und Stück 11, Disjunktiv und Edge-Finding). Nachfolger ist die Verfahrenswahl (Stück 12), die auf diese Demo verweist. Vehikel: der Job Shop in der Order-Kodierung (Hauptexperimente) und das Schubfach als zweites Beispiel.

## Warum dieses Problem

**Ein Constraint-Propagator, der zu jedem Schluss eine Klausel mitliefert („warum gilt das?“), kann aus dem Suchbaum eine Lernmaschine machen:** Aus einem Fehlschlag lässt sich dann eine Regel ableiten, die spätere Äste sperrt. Die Kernfrage der Demo: **Was bringt das Lernen, und gegen welche Suche?** Der Propagator mit Erklärung liefert die Klauseln; gemessen ist hier das Klausellernen in der Order-Kodierung des Job Shops, dort ohne erklärenden Propagator (die Erklärung zeigt die Demo im Schubfach und in Einzelprüfungen). Gemessen wird der Gewinn gegen eine **gleich schwache Suche** (dieselbe CNF, dieselbe Propagation, dieselbe Reihenfolge, nur Lernen an oder aus), **nicht** gegen eine auf das Problem zugeschnittene Suche. Die Quelle des Verfahrens (Ohrimenko, Stuckey, Codish 2009) ist nur im Abstract gelesen: Die Demo beschreibt den Mechanismus und ihre eigene Messung, nicht die Arbeit.

## Modell

- **Order-Kodierung des Job Shops.** Variable „Operation o beginnt spätestens zur Zeit t“ (Entscheidung „Makespan ≤ H“), Monotonie, Vorrang im Auftrag und je Maschinenpaar eine Reihenfolgevariable „a vor b“ mit zwei Implikationsfamilien. Konstante Literale werden herausgekürzt. Entschieden wird nur auf den Reihenfolgevariablen; die Startzeiten folgen aus der Einheitspropagation. Die Messreihen fragen „Makespan ≤ Optimum − 1“ (unerfüllbar, der schwere Teil).
- **Vier Varianten (gleiche CNF, gleiche Einheitspropagation, immer „wahr“ zuerst):** Lernen aus (chronologisches Zurückspringen, keine Klauseln) oder an (1-UIP mit Rücksprung, ohne Neustarts, ohne VSIDS) mal Reihenfolge statisch (kleinste Variablennummer) oder gewichtet (jede Entscheidungsvariable in der Gründe-Wolke eines Konflikts bekommt +1; ein Konfliktgewicht, **nicht** dom/wdeg im Wortsinn, weil Boolesche Variablen immer Domänengröße 2 haben).
- **Hall-Erklärung für AllDifferent.** An der CDCL-Schleife hängt ein Propagator (Matching, Régin-Streichungen), der zu jeder Streichung und jedem Fehlschlag erst im Moment des Gebrauchs („lazy“) eine Klausel erzeugt: ¬[x = w] ∨ ⋁ [u = w′] über u ∈ R und w′ ∈ D₀(u) ∖ V. Jede Klausel lässt sich einzeln gegen die CNF prüfen (CNF plus verneinte Klausel unerfüllbar).
- **Zähleinheiten.** Konflikte (CNF) und Knoten (Mini-CP aus Stück 11) sind verschiedene Einheiten und werden nie addiert; Abbrüche am Budget gehen mit dem Budget als Wert in Median und Kasten ein (die Zahl ist dann eine Untergrenze).
- **Verdikt-Schwelle.** Zwei Verfahren gelten als gleichauf, wenn der Abstand der Mediane unter dem Faktor 1,5 liegt (vor dem Bau festgelegt, `GLEICHAUF_FAKTOR`).
- Mathematik, Symboltabelle und Quellen: Expander **📐 Mathematische Formulierung** in der App.

## Methodik

| Baustein | Datei | Anmerkung |
|---|---|---|
| CDCL (Kern-Version 832b2c10dfdea62d), SplitMix64, Instanzen (Schubfach) | `lcg_cdcl.py`, `lcg_rng.py`, `lcg_instanzen.py` | Kopien aus `sat-cp-planung/kern/`, Hash im Kopf, `tests/test_copies.py` |
| Job-Shop-Erzeuger (SplitMix64, Dauern 1 bis 9), Mini-CP (Stufe 1 und 2) | `lcg_jobshop.py`, `lcg_minicp.py` | Kopien aus Stück 11 (`disjunktiv-edge-finding-demo`) mit je einer dokumentierten Abweichung |
| Order-Kodierung, direkte Kodierung von AllDifferent | `lcg_kodierung.py` | eigener Code |
| Suche mit und ohne Lernen, Hall-Propagator mit Erklärung, Klauselprüfung | `lcg_algorithm.py` | eigener Code, Unterklassen des kopierten CDCL |
| Aufzählung (unabhängiger Rechenweg) | `lcg_aufzaehlung.py` | alle Lösungen kleiner Beispiele |
| Messreihe (vorgerechnet) | `lcg_messreihen.json`, `tools/messung_messreihen.py` | Instanzen Seeds 0 bis 11 je Größe 4 × 4 bis 8 × 8, OR-Tools CP-SAT als eingefrorener Maßstab |

Die vier Experimente: (1) eine Erklärung von Hand (Handbeispiele H1 und H2, Knopf „Klausel prüfen“, Schalter „Ungültige Klausel einschleusen“), (2) Schubfach mit und ohne Erklärung, (3) Job Shop mit Lernen aus oder an (Einzelinstanz live, Messreihe vorgerechnet, Live-Messreihe auf Knopfdruck bis 6 × 6), (4) gegen die zugeschnittene Suche (Mini-CP gegen CNF mit Lernen).

## Befunde und Korrekturen gegenüber dem Plan

- **Die Zahlen der Vormessung (Python-Erzeuger) reproduzieren sich nicht.** Die Vormessung nannte Mediane ohne → mit Lernen von 81 → 13,5 (6 × 6, 12 Instanzen), 270,5 → 48 (7 × 7, 12) und 1 350 → 75 (8 × 8, 5 von 10 Instanzen). Mit den SplitMix64-Instanzen dieser Demo: 53 → 19 (6 × 6), 198 → 12 (7 × 7), 4 085,5 → 353,5 (8 × 8, je 12 Instanzen). Die Richtung stimmt, die Faktoren nicht: 2,8-fach statt 6,0-fach bei 6 × 6, 16,5-fach statt 5,6-fach bei 7 × 7.
- **Der Abstand wächst nicht in jedem Schritt mit der Größe.** Faktoren 1,0 / 1,3 / 2,8 / 16,5 / 11,6 bei 4 × 4 bis 8 × 8: Er wächst in 3 von 4 Schritten, bei 8 × 8 liegt er unter dem von 7 × 7. Bei 8 × 8 brachen 6 der 12 Läufe ohne Lernen am Budget von 5 000 Konflikten ab, der Median ohne Lernen ist dort eine Untergrenze; der Faktor 11,6 ist also ein Mindestwert.
- **Lernen mit Gewichtung ist nicht überall gleich dem Lernen mit fester Reihenfolge.** Der Plan nannte „14 gegen 13,5; 41,5 gegen 48; 75 gegen 75“. Hier: 13 gegen 19 (6 × 6), 13 gegen 12 (7 × 7) und 187 gegen 353,5 (8 × 8) Konflikte, gewichtet gegen statisch: bei 8 × 8 braucht die gewichtete Variante im Median etwa die Hälfte.
- **Die Handbeispiel-Annahme „der Löser lernt die Einheitsklauseln a vor d und c vor b“ stimmt nicht.** Die Einheitspropagation der CNF legt beide Reihenfolgen bei H = 4 schon an der Wurzel fest, ohne Konflikt; die Klauseln sind Folgerungen der Kodierung (Test `test_kodierung_mit_schranken_ist_kleiner_und_legt_die_wurzel_fest`). In der App heißt das Experiment deshalb „Klausel prüfen“ statt „lernen“.
- **Beide Reihenfolgen gelten auch bei H = 5** (in allen 26 Plänen), erst bei H = 6 gibt es Pläne mit „d vor a“; der Plan nannte nur H = 4.
- **Das Experiment „Messreihe auf Knopfdruck“ rechnet bis Größe 6 × 6**; 7 × 7 und 8 × 8 liegen vorgerechnet vor (Plan: 3 × 3 bis 7 × 7 live, 8 × 8 nur bei 10 Instanzen: hier 12 Instanzen vorgerechnet).
- **Die Schubfach-Zahl „Konflikte ≥ 20 000 bei h = 8“** der Vormessung ist jetzt ein Wert: 27 932 Konflikte (Lauf ohne Budget).
- **Die „Zeitleiste der Konflikte“** ist als Länge der gelernten Klausel je Konflikt umgesetzt (Spur des Kerns).
- **Kein PDF-Export, kein Latin-Rotationsplan im Experiment** (nur als Familie der Einzelprüfung).

## Befunde (gemessen, keine Behauptungen)

Alle Zähler sind ganzzahlig und deterministisch. Messreihe: `lcg_messreihen.json` (Skript `tools/messung_messreihen.py`, Stand 2026-11-11), je Größe die Zufalls-Seeds 0 bis 11, Entscheidung „Makespan ≤ Optimum − 1“, Budget 5 000 Konflikte (CNF) und 20 000 Knoten (Mini-CP); jede Antwort und jedes Optimum ist gegen OR-Tools CP-SAT geprüft (60 Instanzen, 0 Abweichungen). `tests/test_claims.py` rechnet jede Zahl dieser Tabelle aus der Datei nach und liest die Zahlen aus dieser README zurück.

| Frage | Befund | Test |
|---|---|---|
| **Lernen aus gegen an, statische Reihenfolge** (Median der Konflikte, 12 Instanzen je Größe) | 4 × 4: 1 → 1; 5 × 5: 4 → 3; 6 × 6: 53 → 19; 7 × 7: 198 → 12; 8 × 8: 4 085,5 → 353,5. Faktoren 1,0 / 1,3 / 2,8 / 16,5 / 11,6. Abbrüche ohne Lernen 0 / 0 / 0 / 1 / 6, mit Lernen 0 / 0 / 0 / 0 / 1. Der Faktor 1,5 wird bei 4 × 4 und 5 × 5 nicht erreicht, von 6 × 6 an in jeder Größe. | `test_claim_lernen_median_je_groesse` |
| **Je Instanz** | Auf keiner der 59 Instanzen, bei denen beide Varianten enden, braucht „mit Lernen, statisch“ mehr Konflikte als „ohne Lernen, statisch“; bei einer Instanz (8 × 8, Zufalls-Seed 7) brechen beide am Budget ab, dort ist das nicht gezeigt. Es braucht weniger auf 2 / 6 / 10 / 10 / 11 von 12 Instanzen (4 × 4 bis 8 × 8), insgesamt auf 39 von 60. | `test_claim_lernen_je_instanz` |
| **Aufgaben ohne Suche** | Instanzen, bei denen alle vier Varianten höchstens einen Konflikt brauchen: 8 / 5 / 1 / 0 / 0 von 12. Mediane der Klauselzahl der CNF: 744,5 / 1 804 / 4 436,5 / 7 055,5 / 12 350,5. | `test_claim_leichte_instanzen_und_klauselzahl` |
| **Konfliktgewichtung ohne Lernen** | Faktor gegenüber „ohne Lernen, statisch“: 1,0 / 1,1 / 1,8 / 2,2 / 3,5; das Lernen dagegen 1,0 / 1,3 / 2,8 / 16,5 / 11,6. Die Gewichtung kommt dem Lernen bis auf den Faktor 1,5 nahe in 2 von 5 Größen (4 × 4 und 5 × 5, wo die Aufgaben leicht sind), in 6 × 6 bis 8 × 8 nicht. | `test_claim_gewichtung_holt_nicht_alles_auf` |
| **Lernen mit Gewichtung gegen statisch** | Median mit Lernen, gewichtet: 1 / 3 / 13 / 13 / 187 gegen statisch 1 / 3 / 19 / 12 / 353,5. | `test_claim_lernen_gewichtet_gegen_statisch` |
| **Gegen die zugeschnittene Suche** | Mini-CP (Stufe 2, Median der Knoten) 1 / 1 / 2 / 3 / 9 gegen CNF mit Lernen (Median der Konflikte) 1 / 3 / 19 / 12 / 353,5: das Mini-CP hat nach der Schwelle der Demo in 4 von 5 Größen weniger Zähleinheiten (Faktor 1,5), bei 4 × 4 sind beide gleichauf, in keiner Größe hat das Lernen im Median weniger. Knoten und Konflikte sind verschiedene Einheiten, nur die Größenordnung zählt: bei 6 × 6 und 8 × 8 liegt das Mini-CP rund eine Größenordnung oder mehr unter den Konflikten der CNF, bei 5 × 5 und 7 × 7 um den Faktor 3 bis 4. Stufe 1: 1 / 3 / 9 / 12 / 64. | `test_claim_mini_cp_gegen_lernen` |
| **Standard-CDCL** (VSIDS, Luby-Neustarts, Phasenspeicher, alle Variablen) | Median 1 / 2,5 / 10,5 / 11 / 58,5, ab 6 × 6 weniger als „mit Lernen, statisch“ (Zusatzhebel Aktivität und Neustarts, kein Teil der Gegenüberstellung). | `test_claim_standard_cdcl` |
| **CP-SAT** (OR-Tools 9.15.6755, ein Arbeiter, eingefroren) | Median der Konflikte seines Entscheidungsmodells 0 / 0 / 0 / 1,5 / 6,5. Nur ein Maßstab; die Demo sagt nichts über CP-SAT-Interna. | `test_claim_cpsat_massstab` |
| **Schubfach** (h + 1 Tauben auf h Löcher), Konflikte des Kern-CDCL für h = 3 bis 8 | 7 / 28 / 159 / 1 004 / 4 811 / 27 932; Faktor je zusätzlichem Loch 4,0 / 5,7 / 6,3 / 4,8 / 5,8. Mit Hall-Erklärung für jedes h 0 Konflikte der Suche und 1 Fehlschlag des Propagators an der Wurzel (erklärte Klausel leer). Trivial im Sinn der Konstruktion: eine einzige Hall-Verletzung. | `test_claim_schubfach` |
| **Einzelprüfung der Erklärungen** | Stichprobe: 664 Klauseln in 4 Familien einzeln gegen die CNF geprüft (höchstens 6 bzw. 12 je Instanz, gleichmäßig aus den verschiedenen Klauseln gewählt; Kern-CDCL, Budget 20 000): 663 gültig, 0 ungültig, 1 unentschieden (Schubfach h = 8, die Gegenprobe selbst über dem Budget). Rotationsplan mit Lücken 216, Zufalls-Domänen 342, Schubfach 6 (die leere Klausel), gelernte Klauseln des Job-Shop-CDCL 100. | `test_claim_pruefbilanz` |
| **Handbeispiel H1** | x1 ∈ {1, 2, 3}, x2 ∈ {1, 2}, x3 ∈ {1, 2, 3}: 4 Lösungen; nach x1 ≠ 3 bleiben 2, beide mit x3 = 3; die Erklärung „x3 ≠ 1 ∨ x1 = 3“ gilt in allen 4 Lösungen, „x3 ≠ 1“ nicht (Lösung (3, 2, 1)). | `test_h1_*` |
| **Handbeispiel H2 und H3** | Pläne bei H = 2 / 3 / 4 / 5: 0 / 1 / 7 / 26. Order-Kodierung ohne Schranken: 4 / 8 / 12 / 16 Variablen, 9 / 18 / 28 / 38 Klauseln, Modelle 0 / 1 / 7 / 26 (genau die Aufzählung). | `test_h2_*`, `test_h3_*` |

Alle Aussagen gelten für diese Umsetzung (Kern-CDCL ohne Neustarts und VSIDS in den vier Varianten, Konfliktgewicht ohne Zerfall), diesen Erzeuger (quadratisch, Dauern 1 bis 9, Zufalls-Seeds 0 bis 11) und die gemessenen Größen.

## Ehrliche Grenzen

- **Gleich schwache Suche als Vergleich.** Das Lernen schlägt hier die Suche ohne Gedächtnis; die zugeschnittene Suche (Mini-CP) braucht im Messbereich im Median nicht mehr Zähleinheiten als die CNF mit Lernen, in 4 von 5 Größen weniger (andere Einheit, siehe oben). Das Mini-CP kennt die Struktur (Paare, Fenster), die CNF muss sie aus Klauseln herleiten. Wie viel des Vorsprungs an der Verzweigungsregel (Paar mit dem kleinsten Spielraum) und wie viel an der Disjunktiv-Propagation mit der einfachen Edge-Finding-Fassung liegt, ist in dieser Demo nicht getrennt gemessen; auch Stufe 1 liegt bei 6 × 6 und 8 × 8 vor der CNF mit Lernen (9 gegen 19, 64 gegen 353,5).
- **Ein Problem, ein Erzeuger.** Der Befund gilt für den Job Shop mit Dauern 1 bis 9 und diese Zufalls-Seeds. Rotationspläne mit zwei Zählbedingungen waren in der Vormessung zu leicht (Median ein Konflikt in jeder Variante), RCPSP und kumulative Ressourcen sind nicht gemessen.
- **Erklärungen nur für Hall (AllDifferent).** Nur Stichproben dieser Klauseln und der gelernten Klauseln des Job-Shop-CDCL (nur 6 × 6, 100 Stück) sind einzeln geprüft; für Disjunktiv- oder Kumulativ-Propagatoren mit Erklärung gibt es keinen Nachbau.
- **Eager statt lazy im Job Shop.** Die Order-Kodierung wird vorab vollständig gebaut; ein Lazy-Propagator mit Erklärung für Disjunktiv ist nicht nachgebaut. Das Argument „lazy“ (nur ein Teil der Ausgangsklauseln löst je einen Schluss aus) stammt aus der Vormessung der Planung (`out_cp2_cnf_*.txt`; dort lösten an drei Instanzen 4 bis 30 % der Ausgangsklauseln einen Schluss oder Konflikt aus) und ist in dieser Demo nicht nachgemessen.
- **Das Schubfach ist ein Sonderfall.** 0 Konflikte der Suche sind kein Maß für andere Aufgaben.
- **Abbrüche.** Bei 8 × 8 brachen 6 von 12 Läufen ohne Lernen (statisch) am Budget ab: Der Faktor ist ein Mindestwert, und mit einem größeren Budget läge der Median ohne Lernen höher.
- **Eine Messreihe, ein Lauf je Instanz.** Keine Wiederholung mit anderem Zufalls-Seed des Lösers (die Läufe sind deterministisch); ob die Faktoren mit anderen Instanzen gleich ausfallen, zeigt der Vergleich mit der Vormessung: nein, sie schwanken (siehe oben).
- **Quelle nur im Abstract gelesen** (Ohrimenko, Stuckey, Codish 2009); Edge-Finding und kumulative Erklärungen werden nicht behauptet. Die Order-Kodierung ist eine eigene Darstellung des Messgeräts, keine Aussage über CP-SAT.

## Verifikation

- **Kern:** Handbeispiele H1 bis H3 von Hand (`tests/test_algorithm.py`): Aufzählung, Erklärungsklauseln, Fenster, Variablen- und Klauselzahlen, Modelle der CNF gleich der Aufzählung.
- **Orakel** (`tests/test_oracle_lazy_clause.py`): `hall_analyse` gegen die Aufzählung (Streichungen genau die Werte ohne Lösung, 600 Zufalls-Domänen); jede erzeugte Erklärungsklausel gilt in allen Lösungen (Aufzählung) und ist nach Kern-CDCL und OR-Tools CP-SAT gültig; Antwort und Optimum der Job-Shop-CNF gegen Aufzählung (2 × 2, 3 × 2) und CP-SAT; jedes Modell, in einen Plan zurückübersetzt, besteht einen eigenen Plan-Prüfer.
- **Eigenschaften** (`tests/test_properties.py`): auf dem Schubfach h = 3 bis 6 höchstens so viele Konflikte mit Erklärung wie ohne; Dauern mal zwei ändern die Antworten nicht; Monotonie im Horizont; Reihenfolge der Aufträge ändert das Optimum nicht.
- **Zweig-Test:** jede der vier Varianten weicht auf mindestens einer Instanz von ihrer Nachbarvariante ab.
- **Kopien:** `tests/test_copies.py` setzt die dokumentierten Abweichungen zurück und vergleicht mit dem Hash im Kopf; die Kern-Regressionstests (`test_kern_*`) laufen gegen die Kopien.
- **Messreihe:** Aufbau, innere Konsistenz, exakte Nachrechnung einer Stichprobe (`tests/test_messreihen.py`); jede Zahl dieser README in `tests/test_claims.py`.
- **Oberfläche:** AppTest-Rauchtest, Inhalt je Experiment und Preset, Layout (Schnellstart in der Seitenleiste, aktives Preset, ausblendbare Regler), Footer, Laufzeit-Importe.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: vier Experimente, Kernfrage, Grenzen, 📐-Expander |
| `lcg_algorithm.py` | Suche mit und ohne Lernen, Hall-Propagator mit Erklärung, Schritte auf Domänenebene, Klauselprüfung |
| `lcg_kodierung.py` | Order-Kodierung des Job Shops, direkte Kodierung von AllDifferent |
| `lcg_aufzaehlung.py` | Aufzählung aller Lösungen kleiner Beispiele |
| `lcg_cdcl.py`, `lcg_rng.py`, `lcg_instanzen.py` | Kopien aus dem Kern-Paket der Linie |
| `lcg_jobshop.py`, `lcg_minicp.py` | Kopien aus Stück 11 |
| `lcg_constants.py` | Regler-Grenzen, feste Annahmen, Farben, Presets |
| `lcg_evaluation.py` | Läufe, Statistik, Verdikte (reine Funktionen) |
| `lcg_layout.py` | Fester Kopf (Stylesheet) |
| `lcg_presets.py` | Permalink, Presets (Schnellstart in der Seitenleiste), ausblendbare Regler, Zufalls-Seed-Button |
| `lcg_scenario.py` | Handbeispiele, Job-Shop-Instanzen, Rotationsplan |
| `lcg_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `lcg_messreihen.json`, `tools/messung_messreihen.py` | vorgerechnete Messreihe und ihr Skript (OR-Tools nur dort) |
| `requirements.txt`, `requirements-dev.txt` | Laufzeit-Bibliotheken; dazu pytest und OR-Tools (nur Tests und Messskript) |
| `tests/` | Handbeispiele, Orakel, Eigenschaften, Randfälle, Verdikte, Claims, Messreihe, Kopien, Presets, Layout, App, Footer |

## Bewusst nicht umgesetzt

- Lazy Clause Generation für Disjunktiv und Kumulativ (kein Nachbau, keine Prüfung); Edge-Finding in der CNF.
- RCPSP (die zeitindizierte CNF ist mit der Python-Suche ohne Lernen zu langsam; kein Befund).
- Nachmessen des Anteils der genutzten Ausgangsklauseln (Argument für „lazy“).
- Ein anderes Zählmaß als Konflikte und Knoten; keine Zeitmessung als Befund.
- OR-Tools in der App: CP-SAT erscheint nur als eingefrorener Maßstab.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly und pandas.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html).
