"""Messskript: schreibt `lcg_messreihen.json` (Stand des Baus). Aufruf (Wurzelordner des Repos, Test-venv, weil OR-Tools nur dort liegt):

    python tools/messung_messreihen.py [--out lcg_messreihen.json] [--teil jobshop|schubfach|pruefung|alle]

Teile:
  jobshop    je Größe 4 × 4 bis 8 × 8 die Zufalls-Seeds 0 bis 11 (SplitMix64-Erzeuger `lcg_jobshop.make_jobshop`, Dauern 1 bis 9); Entscheidung „Makespan ≤ Optimum − 1“ (unerfüllbar):
             Konflikte der vier CNF-Varianten und des Standard-CDCL (Budget 5 000), Knoten des Mini-CP Stufe 1 und 2 (Budget 20 000), Konflikte von OR-Tools CP-SAT (ein Arbeiter);
             jede Antwort und jedes Optimum wird gegen CP-SAT geprüft, die Zahl der Abweichungen steht in `meta.antwortfehler`.
  schubfach  h = 3 bis 8: Konflikte des Kern-CDCL und des CDCL mit Hall-Erklärung.
  pruefung   jede erzeugte Erklärungsklausel (Hall) und gelernte Klauseln des Job-Shop-CDCL einzeln gegen die CNF: CNF plus verneinte Klausel muss unerfüllbar sein (Kern-CDCL, Budget 20 000).
Gespeichert werden nur Zähler, nie Sekunden. OR-Tools nur hier und in den Tests (`requirements-dev.txt`), nie in der App."""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lcg_algorithm as A  # noqa: E402
import lcg_constants as C  # noqa: E402
import lcg_evaluation as E  # noqa: E402
import lcg_kodierung as K  # noqa: E402
import lcg_minicp as M  # noqa: E402
import lcg_scenario as S  # noqa: E402
from lcg_rng import SplitMix64  # noqa: E402


def cpsat_jobshop(inst, H=None):
    """Optimum (H=None) beziehungsweise Entscheidung „Makespan ≤ H“ mit CP-SAT: (Wert oder Antwort, Konflikte)."""
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    horizont = H if H is not None else inst.total_duration
    per, s = {}, {}
    for j, job in enumerate(inst.jobs):
        for k, (mc, d) in enumerate(job):
            s[j, k] = m.NewIntVar(0, horizont, "")
            per.setdefault(mc, []).append(m.NewIntervalVar(s[j, k], d, s[j, k] + d, ""))
            if k:
                m.Add(s[j, k] >= s[j, k - 1] + job[k - 1][1])
    ende = m.NewIntVar(0, horizont, "")
    for j, job in enumerate(inst.jobs):
        m.Add(ende >= s[j, len(job) - 1] + job[-1][1])
    for p in per.values():
        m.AddNoOverlap(p)
    if H is None:
        m.Minimize(ende)
    sol = cp_model.CpSolver()
    sol.parameters.num_workers = 1
    sol.parameters.max_time_in_seconds = 300
    r = sol.Solve(m)
    if H is None:
        return (int(sol.ObjectiveValue()) if r == cp_model.OPTIMAL else None), sol.NumConflicts()
    return {cp_model.OPTIMAL: True, cp_model.FEASIBLE: True, cp_model.INFEASIBLE: False}.get(r), sol.NumConflicts()


def teil_jobshop(daten, fehler):
    daten["jobshop"] = {}
    for g in C.MESS_GROESSEN:
        zeilen = []
        for seed in C.MESS_SEEDS:
            inst = S.jobshop_instanz(g, seed)
            row = E.jobshop_lauf(inst, C.MESS_BUDGET, C.MESS_BUDGET_MINICP)
            opt_cp, _ = cpsat_jobshop(inst)
            if opt_cp != row["opt"]:
                fehler.append(("optimum", g, seed, row["opt"], opt_cp))
            ant, konf = cpsat_jobshop(inst, row["opt"] - 1)
            row["cpsat"] = konf
            if ant is not False:
                fehler.append(("cpsat-antwort", g, seed, ant))
            for name, a in row["antworten"].items():
                if a not in (False, None):
                    fehler.append(("antwort", g, seed, name, a))
            del row["antworten"]
            row["seed"] = seed
            zeilen.append(row)
            print(g, seed, {k: row[k] for k in ("opt", "klauseln", "ohne_stat", "ohne_gew", "mit_stat", "mit_gew", "standard", "mini1", "mini2", "cpsat")}, flush=True)
        daten["jobshop"][str(g)] = zeilen


def teil_schubfach(daten):
    daten["schubfach"] = []
    for h in range(3, 9):
        r = E.schubfach_lauf(h)
        daten["schubfach"].append(r)
        print("schubfach", r, flush=True)


def _pruefe_liste(n, klauseln, liste, budget):
    z = {"geprueft": 0, "gueltig": 0, "ungueltig": 0, "unentschieden": 0}
    for k in liste:
        p = A.pruefe_klausel(n, klauseln, list(k), budget)
        z["geprueft"] += 1
        z[{"gueltig": "gueltig", "ungueltig": "ungueltig", "unentschieden": "unentschieden"}[p.urteil]] += 1
    return z


def _verteile(klauseln, grenze):
    """Gleichmäßig über die Liste verteilte Auswahl von höchstens `grenze` verschiedenen Klauseln."""
    eindeutig = list(dict.fromkeys(tuple(sorted(k)) for k in klauseln))
    if len(eindeutig) <= grenze:
        return eindeutig
    schritt = len(eindeutig) / grenze
    return [eindeutig[int(i * schritt)] for i in range(grenze)]


def teil_pruefung(daten):
    budget = C.KLAUSEL_PRUEF_BUDGET
    ergebnis = []

    # (a) Rotationsplan mit Lücken
    zaehler = {"instanzen": 0, "mit_klauseln": 0, "geprueft": 0, "gueltig": 0, "ungueltig": 0, "unentschieden": 0}
    for ordnung in (10, 12, 14):
        for luecken in (50, 55, 60):
            for seed in range(4):
                vor = S.rotationsplan(ordnung, luecken, seed)
                doms, gruppen = K.rotationsplan_domaenen(ordnung, vor)
                kod = K.kodiere_alldifferent(doms, gruppen)
                r, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen, protokoll=True, budget=5000)
                zaehler["instanzen"] += 1
                auswahl = _verteile([e.klausel for e in s.protokoll], 6)
                if auswahl:
                    zaehler["mit_klauseln"] += 1
                    for k, v in _pruefe_liste(kod.n_var, kod.klauseln, auswahl, budget).items():
                        zaehler[k] += v
                print("pruefung rotation", ordnung, luecken, seed, len(s.protokoll), zaehler, flush=True)
    ergebnis.append(dict(familie="Rotationsplan mit Lücken (Ordnung 10, 12, 14; 50, 55, 60 % Lücken; Seeds 0 bis 3)", **zaehler))

    # (b) Zufalls-Domänen (kleine AllDifferent-Gruppen mit zufälligen Teilmengen als Domäne)
    zaehler = {"instanzen": 0, "mit_klauseln": 0, "geprueft": 0, "gueltig": 0, "ungueltig": 0, "unentschieden": 0}
    rng = SplitMix64(2026)
    for _ in range(240):
        p = 5 + rng.below(4)                    # 5 bis 8 Variablen
        wmax = p + rng.below(2)                 # Werte 1..p oder 1..p+1
        doms = []
        for _i in range(p):
            d = [w for w in range(1, wmax + 1) if rng.below(100) < 62]
            doms.append(d or [1 + rng.below(wmax)])
        kod = K.kodiere_alldifferent(doms)
        r, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen, protokoll=True, budget=5000)
        zaehler["instanzen"] += 1
        auswahl = _verteile([e.klausel for e in s.protokoll], 12)
        if auswahl:
            zaehler["mit_klauseln"] += 1
            for k, v in _pruefe_liste(kod.n_var, kod.klauseln, auswahl, budget).items():
                zaehler[k] += v
    print("pruefung zufall", zaehler, flush=True)
    ergebnis.append(dict(familie="Zufalls-Domänen (5 bis 8 Variablen, 240 Instanzen)", **zaehler))

    # (c) Schubfach h = 3 bis 8: die erklärte Klausel ist leer, ihre Gültigkeit ist die Unerfüllbarkeit der Formel
    import lcg_instanzen as I

    zaehler = {"instanzen": 0, "mit_klauseln": 0, "geprueft": 0, "gueltig": 0, "ungueltig": 0, "unentschieden": 0}
    for h in range(3, 9):
        inst = I.pigeonhole(h)
        klauseln = [list(k) for k in inst.klauseln]
        r, s = A.loese_mit_hall(inst.n, klauseln, [K.schubfach_gruppe(h)], protokoll=True)
        zaehler["instanzen"] += 1
        zaehler["mit_klauseln"] += 1
        for k, v in _pruefe_liste(inst.n, klauseln, [e.klausel for e in s.protokoll], budget).items():
            zaehler[k] += v
        print("pruefung schubfach", h, zaehler, flush=True)
    ergebnis.append(dict(familie="Schubfach h = 3 bis 8 (die erklärte Klausel ist leer)", **zaehler))

    # (d) gelernte Klauseln des Job-Shop-CDCL (1-UIP), 6 × 6, Seeds 0 bis 11
    zaehler = {"instanzen": 0, "mit_klauseln": 0, "geprueft": 0, "gueltig": 0, "ungueltig": 0, "unentschieden": 0}
    for seed in range(12):
        inst = S.jobshop_instanz(6, seed)
        opt, _ = S.optimum(inst)
        kod = K.kodiere_jobshop([list(j) for j in inst.jobs], opt - 1)
        s = A.Suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, lernen=True, proof=True)
        e = s.loese(conflict_budget=C.MESS_BUDGET)
        gelernt = [k for art, k in e.beweis if art == "a" and k]
        zaehler["instanzen"] += 1
        auswahl = _verteile(gelernt, 12)
        if auswahl:
            zaehler["mit_klauseln"] += 1
            for k, v in _pruefe_liste(kod.n_var, kod.klauseln, auswahl, budget).items():
                zaehler[k] += v
    print("pruefung gelernt", zaehler, flush=True)
    ergebnis.append(dict(familie="Gelernte Klauseln des Job-Shop-CDCL (6 × 6, Seeds 0 bis 11, bis zu 12 je Instanz)", **zaehler))
    daten["pruefung"] = ergebnis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / C.MESSREIHEN_DATEI))
    ap.add_argument("--teil", default="alle", choices=("alle", "jobshop", "schubfach", "pruefung"))
    args = ap.parse_args()
    out = Path(args.out)
    daten = json.loads(out.read_text(encoding="utf-8")) if out.exists() and args.teil != "alle" else {}
    fehler = []
    t0 = time.time()
    if args.teil in ("alle", "jobshop"):
        teil_jobshop(daten, fehler)
    if args.teil in ("alle", "schubfach"):
        teil_schubfach(daten)
    if args.teil in ("alle", "pruefung"):
        teil_pruefung(daten)
    import ortools

    meta = daten.get("meta", {})
    meta.update({
        "skript": C.MESS_SKRIPT, "datum": date.today().isoformat(), "ortools": ortools.__version__, "budget_cnf": C.MESS_BUDGET, "budget_minicp": C.MESS_BUDGET_MINICP,
        "seeds": list(C.MESS_SEEDS), "groessen": list(C.MESS_GROESSEN), "erzeuger": "lcg_jobshop.make_jobshop (SplitMix64, Dauern 1 bis 9, quadratisch)",
        "hinweis": "vorgerechnet, nicht live; CP-SAT mit einem Arbeiter, Konflikte seines Entscheidungsmodells „Makespan ≤ Optimum − 1“",
    })
    if args.teil in ("alle", "jobshop"):
        meta["antwortfehler"] = len(fehler)
        meta["fehler"] = [list(map(str, f)) for f in fehler]
    daten["meta"] = meta
    out.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fertig; Abweichungen gegen CP-SAT:", len(fehler), fehler, "| Sekunden (nur Lauf, kein Befund):", round(time.time() - t0))


if __name__ == "__main__":
    main()
