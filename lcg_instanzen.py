# Herkunft: Kopie von sat-cp-planung/kern/instanzen.py (Kern-Version 6795de796b66fff8, Datei HASHES.txt vom 2026-11-10), nur Importe auf lcg_ umgestellt.
# Nicht von Hand ändern: tests/test_copies.py vergleicht diese Datei mit dem Kern-Hash.
"""Instanzerzeuger des Kern-Pakets: Zufalls-3-SAT, Schubfach, Schur, Färbung, Rampen.

Alle Zufallsinstanzen laufen über SplitMix64 (`rng.py`), nie über Python-`random`.
Eine Instanz ist `Instanz(n, klauseln, meta)`: n Variablen (1..n), Klauseln als Tupel von Literalen
(+v = Variable v, -v = nicht v), `meta` ein Dictionary mit Angaben zur Aufgabe.
`rand3` zieht die Klauseln genau wie `random_formula` in `reduktionskette-demo/red_scenario.py`
(gleicher n, m, Seed gibt dieselbe Formel; wächst m, bleiben die früheren Klauseln).
"""
import itertools
from typing import NamedTuple

from lcg_rng import SplitMix64


class Instanz(NamedTuple):
    n: int
    klauseln: list
    meta: dict


def zufallsklausel(n: int, rng: SplitMix64) -> tuple:
    """Drei verschiedene Variablen aus 1..n mit zufälligem Vorzeichen; zieht immer sechs Zahlen aus dem Strom."""
    variablen = list(range(1, n + 1))
    for i in range(3):
        j = i + rng.below(n - i)
        variablen[i], variablen[j] = variablen[j], variablen[i]
    vorzeichen = [rng.coin() for _ in range(3)]
    return tuple(v if s else -v for v, s in zip(variablen[:3], vorzeichen))


def rand3(n: int, m: int, seed: int) -> Instanz:
    """Zufalls-3-SAT mit n Variablen und m Klauseln, deterministisch aus (n, m, seed)."""
    if n < 3:
        raise ValueError("3-KNF braucht mindestens drei Variablen")
    rng = SplitMix64(seed)
    return Instanz(n, [zufallsklausel(n, rng) for _ in range(m)], {"art": "rand3", "m": m, "verhaeltnis": m / n, "seed": seed})


def pigeonhole(h: int) -> Instanz:
    """h + 1 Tauben, h Löcher: unerfüllbar. Variable (Taube p, Loch l) = p*h + l + 1."""
    def v(p, l):
        return p * h + l + 1

    klauseln = [tuple(v(p, l) for l in range(h)) for p in range(h + 1)]
    for l in range(h):
        for p, q in itertools.combinations(range(h + 1), 2):
            klauseln.append((-v(p, l), -v(q, l)))
    return Instanz((h + 1) * h, klauseln, {"art": "schubfach", "h": h, "erfuellbar": False})


def schur(n: int, k: int) -> Instanz:
    """Zahlen 1..n auf k Mengen ohne a + b = c in einer Menge (a = b erlaubt). Variable (i, c) = (i-1)*k + c + 1."""
    def v(i, c):
        return (i - 1) * k + c + 1

    klauseln = [tuple(v(i, c) for c in range(k)) for i in range(1, n + 1)]
    for i in range(1, n + 1):
        for c, d in itertools.combinations(range(k), 2):
            klauseln.append((-v(i, c), -v(i, d)))
    for a in range(1, n + 1):
        for b in range(a, n + 1):
            if a + b <= n:
                for c in range(k):
                    klauseln.append(tuple(sorted({-v(a, c), -v(b, c), -v(a + b, c)})))
    return Instanz(n * k, klauseln, {"art": "schur", "n_zahlen": n, "k": k})


def schur_mengen(instanz: Instanz, modell: dict) -> list:
    """Liest aus einem Modell die k Mengen der Zahlen ab (Zahl i gehört zur ersten wahren Menge)."""
    k = instanz.meta["k"]
    mengen = [[] for _ in range(k)]
    for i in range(1, instanz.meta["n_zahlen"] + 1):
        for c in range(k):
            if modell[(i - 1) * k + c + 1]:
                mengen[c].append(i)
                break
    return mengen


def faerbung(n_knoten: int, kanten, k: int) -> Instanz:
    """k-Färbung: jeder Knoten hat mindestens eine Farbe, benachbarte Knoten nie dieselbe.
    Variable (Knoten i, Farbe c) = i*k + c + 1; „höchstens eine Farbe“ fehlt bewusst (eine zweite Farbe schadet nicht)."""
    def v(i, c):
        return i * k + c + 1

    klauseln = [tuple(v(i, c) for c in range(k)) for i in range(n_knoten)]
    for (i, j) in kanten:
        for c in range(k):
            klauseln.append((-v(i, c), -v(j, c)))
    return Instanz(n_knoten * k, klauseln, {"art": "faerbung", "n_knoten": n_knoten, "k": k, "kanten": [tuple(e) for e in kanten]})


def faerbung_aus_modell(instanz: Instanz, modell: dict) -> list:
    """Farbe je Knoten (die erste wahre) oder None."""
    n_knoten, k = instanz.meta["n_knoten"], instanz.meta["k"]
    farben = []
    for i in range(n_knoten):
        farben.append(next((c for c in range(k) if modell[i * k + c + 1]), None))
    return farben


def zufallskanten(n_knoten: int, anzahl: int, seed: int) -> list:
    """Genau `anzahl` verschiedene Kanten (a, b), a < b, auf n_knoten Knoten, sortiert, deterministisch aus dem Seed
    (partielles Fisher-Yates über alle Paare wie `random_graph` in red_scenario.py)."""
    paare = [(a, b) for a in range(n_knoten) for b in range(a + 1, n_knoten)]
    if not 0 <= anzahl <= len(paare):
        raise ValueError(f"{anzahl} Kanten passen nicht in einen Graphen mit {n_knoten} Knoten")
    rng = SplitMix64(seed)
    for i in range(anzahl):
        j = i + rng.below(len(paare) - i)
        paare[i], paare[j] = paare[j], paare[i]
    return sorted(paare[:anzahl])


def flat_graph(n_knoten: int, grad: float, seed: int, k: int = 3) -> Instanz:
    """k-Färbung eines Zufallsgraphen mit mittlerem Grad `grad` (Kantenzahl = gerundet n·grad/2)."""
    kanten = zufallskanten(n_knoten, int(round(n_knoten * grad / 2)), seed)
    inst = faerbung(n_knoten, kanten, k)
    inst.meta.update({"grad": grad, "seed": seed})
    return inst


def rampen_instanz(n_auftraege: int, grad: float, seed: int, k: int) -> Instanz:
    """Aufträge auf k Rampen: zwei Aufträge im Konflikt (überlappende Zeitfenster) dürfen nicht dieselbe Rampe bekommen.
    Der Konfliktgraph ist ein Zufallsgraph wie in `flat_graph`; die Einkleidung steht im Meta-Eintrag."""
    inst = flat_graph(n_auftraege, grad, seed, k)
    inst.meta.update({"einkleidung": "rampen", "auftraege": n_auftraege, "rampen": k})
    return inst


def pruefe_modell(klauseln, modell: dict) -> bool:
    """Wahr genau dann, wenn jede Klausel mindestens ein wahres Literal hat (unabhängig vom Löser)."""
    return all(any((modell[abs(l)] if l > 0 else not modell[abs(l)]) for l in c) for c in klauseln)
