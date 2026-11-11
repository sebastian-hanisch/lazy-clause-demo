"""Aufzählung aller Lösungen kleiner Beispiele: der unabhängige Rechenweg für die Handbeispiele und die Tests (nur Standardbibliothek, kein Solver).

`alldifferent_loesungen`: alle Belegungen mit paarweise verschiedenen Werten. `jobshop_plaene`: alle ganzzahligen Pläne mit Makespan ≤ H (Operation für Operation
mit Vorrangprüfung im Auftrag und Überlappungsprüfung auf der Maschine). Der Aufwand wächst exponentiell: nur für Beispiele mit höchstens etwa 6 Operationen gedacht
(`MAX_OPERATIONEN`)."""

from itertools import product

MAX_OPERATIONEN = 7


def alldifferent_loesungen(domaenen) -> list:
    """Alle Belegungen (Tupel) mit x_i ∈ domaenen[i] und paarweise verschiedenen Werten, in lexikographischer Reihenfolge."""
    doms = [sorted(set(d)) for d in domaenen]
    return [v for v in product(*doms) if len(set(v)) == len(v)]


def jobshop_plaene(jobs, H: int) -> list:
    """Alle Pläne (Startzeiten je Operation, Operation (j, k) an Stelle `Summe der Längen davor + k`) mit Makespan ≤ H, lexikographisch.
    Eine Operation beginnt frühestens am Ende ihres Vorgängers im Auftrag (Wartezeiten sind erlaubt); eine Maschine bearbeitet höchstens eine Operation zugleich."""
    d, mc, vorg = [], [], []
    for job in jobs:
        for k, (m, p) in enumerate(job):
            vorg.append(len(d) - 1 if k else None)
            d.append(p)
            mc.append(m)
    n = len(d)
    if n > MAX_OPERATIONEN:
        raise ValueError(f"mehr als {MAX_OPERATIONEN} Operationen: die Aufzählung wäre zu groß")
    out = []
    starts = [0] * n

    def rek(o):
        if o == n:
            out.append(tuple(starts))
            return
        lo = 0 if vorg[o] is None else starts[vorg[o]] + d[vorg[o]]
        for t in range(lo, H - d[o] + 1):
            if any(mc[q] == mc[o] and starts[q] < t + d[o] and t < starts[q] + d[q] for q in range(o)):
                continue
            starts[o] = t
            rek(o + 1)

    rek(0)
    return out


def optimum_aufzaehlung(jobs, H_max: int = 40):
    """Kleinster Makespan, für den die Aufzählung einen Plan findet (None, wenn bis H_max keiner existiert)."""
    for H in range(1, H_max + 1):
        if jobshop_plaene(jobs, H):
            return H
    return None
