"""Unabhängige Rechenwege für die Orakel-Tests: ein eigener Plan-Prüfer, Aufzählung für AllDifferent und OR-Tools CP-SAT (nur im Test-venv).

Nichts hier benutzt den CDCL-Kern oder die Propagatoren der Demo; die Gegenproben sind Aufzählung, ein eigener Zulässigkeitsprüfer und CP-SAT."""

from itertools import product

import pytest


def plan_ok(jobs, starts, H=None) -> bool:
    """Zulässigkeit eines Plans: Startzeiten ≥ 0, Reihenfolge im Auftrag, keine Überlappung auf einer Maschine, Makespan ≤ H (falls angegeben)."""
    ops = [(j, k, m, d) for j, job in enumerate(jobs) for k, (m, d) in enumerate(job)]
    if len(starts) != len(ops) or any(s < 0 for s in starts):
        return False
    for i, (j, k, m, d) in enumerate(ops):
        if k and starts[i - 1] + ops[i - 1][3] > starts[i]:
            return False
        if H is not None and starts[i] + d > H:
            return False
    for a in range(len(ops)):
        for b in range(a + 1, len(ops)):
            if ops[a][2] == ops[b][2] and starts[a] < starts[b] + ops[b][3] and starts[b] < starts[a] + ops[a][3]:
                return False
    return True


def alldiff_loesungen(doms):
    return [v for v in product(*[sorted(d) for d in doms]) if len(set(v)) == len(v)]


def erlaubte_werte(doms):
    """Je Variable die Werte, die in mindestens einer Lösung vorkommen (Bereichskonsistenz per Aufzählung); None, wenn es keine Lösung gibt."""
    sol = alldiff_loesungen(doms)
    if not sol:
        return None
    return [{l[i] for l in sol} for i in range(len(doms))]


def cpsat():
    return pytest.importorskip("ortools.sat.python.cp_model")


def cpsat_jobshop_optimum(jobs):
    cp = cpsat()
    horizont = sum(d for job in jobs for _, d in job)
    m = cp.CpModel()
    s, per = {}, {}
    for j, job in enumerate(jobs):
        for k, (mc, d) in enumerate(job):
            s[j, k] = m.NewIntVar(0, horizont, "")
            per.setdefault(mc, []).append(m.NewIntervalVar(s[j, k], d, s[j, k] + d, ""))
            if k:
                m.Add(s[j, k] >= s[j, k - 1] + job[k - 1][1])
    ende = m.NewIntVar(0, horizont, "")
    for j, job in enumerate(jobs):
        m.Add(ende >= s[j, len(job) - 1] + job[-1][1])
    for p in per.values():
        m.AddNoOverlap(p)
    m.Minimize(ende)
    sol = cp.CpSolver()
    sol.parameters.num_workers = 1
    r = sol.Solve(m)
    assert r == cp.OPTIMAL
    return int(sol.ObjectiveValue())


def cpsat_klausel_gueltig(n, klauseln, klausel) -> bool:
    """Folgt `klausel` aus der CNF? CP-SAT entscheidet: CNF plus verneinte Klausel unerfüllbar."""
    cp = cpsat()
    m = cp.CpModel()
    v = [None] + [m.NewBoolVar("") for _ in range(n)]

    def lit(l):
        return v[l] if l > 0 else v[-l].Not()

    for c in klauseln:
        m.AddBoolOr([lit(l) for l in c])
    for l in klausel:
        m.Add(lit(-l) == 1)
    sol = cp.CpSolver()
    sol.parameters.num_workers = 1
    return sol.Solve(m) == cp.INFEASIBLE


def cpsat_cnf_erfuellbar(n, klauseln) -> bool:
    cp = cpsat()
    m = cp.CpModel()
    v = [None] + [m.NewBoolVar("") for _ in range(n)]
    for c in klauseln:
        m.AddBoolOr([(v[l] if l > 0 else v[-l].Not()) for l in c])
    sol = cp.CpSolver()
    sol.parameters.num_workers = 1
    return sol.Solve(m) in (cp.OPTIMAL, cp.FEASIBLE)


def zaehle_modelle(n, klauseln) -> int:
    """Zahl der Modelle einer CNF über den Variablen 1..n (Rekursion mit Abbruch bei verletzter Klausel; eigener Rechenweg, ohne Kern-Code)."""
    wert = [0] * (n + 1)

    def verletzt():
        for c in klauseln:
            if all(wert[abs(l)] != 0 and (wert[abs(l)] > 0) != (l > 0) for l in c):
                return True
        return False

    def rek(v):
        if verletzt():
            return 0
        if v > n:
            return 1
        gesamt = 0
        for w in (1, -1):
            wert[v] = w
            gesamt += rek(v + 1)
        wert[v] = 0
        return gesamt

    return rek(1)
