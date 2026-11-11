"""Szenarien: die Handbeispiele H1 und H2, Job-Shop-Zufallsinstanzen (SplitMix64, `lcg_jobshop.py`), das Schubfach und der Rotationsplan (lateinisches Quadrat mit Lücken).

Zufall nur über den ganzzahligen SplitMix64 (`lcg_rng`), nie Pythons `random`. Das Optimum einer Job-Shop-Instanz bestimmt das Mini-CP (`lcg_minicp.loese`, Stufe 2);
in den Tests wird es gegen die Aufzählung und gegen OR-Tools CP-SAT geprüft, in der App steht kein OR-Tools."""

import lcg_minicp as M
from lcg_jobshop import Instance, as_instance, make_jobshop
from lcg_rng import SplitMix64

# ------------------------------------------------------------------------------------------------------------------------------ Handbeispiele
# H1 (Hall-Erklärung): x1 ∈ {1, 2, 3}, x2 ∈ {1, 2}, x3 ∈ {1, 2, 3}, alle verschieden; die Entscheidung x1 ≠ 3 macht {x1, x2} zu einer Hall-Menge mit den Werten {1, 2}.
H1_DOMAENEN = ([1, 2, 3], [1, 2], [1, 2, 3])
H1_NAMEN = ("x1", "x2", "x3")
H1_ENTSCHEIDUNG = (0, 3)          # (Variable x1, Wert 3 wird gestrichen)

# H2 (Mini-Job-Shop 2 × 2): Auftrag 1: a (Maschine 1, Dauer 2) dann b (Maschine 2, Dauer 1); Auftrag 2: c (Maschine 2, Dauer 2) dann d (Maschine 1, Dauer 1).
H2_JOBS = (((0, 2), (1, 1)), ((1, 2), (0, 1)))
H2_NAMEN = ("a", "b", "c", "d")
H2_HORIZONTE = (3, 4, 5)
H2_INSTANZ = as_instance(H2_JOBS)


def op_name_h2(o: int) -> str:
    return H2_NAMEN[o]


def op_name_allgemein(inst: Instance):
    """Anzeigename „J1.2“ (Auftrag 1, zweite Operation) je Operationsnummer."""
    namen = [f"J{j + 1}.{k + 1}" for j, job in enumerate(inst.jobs) for k in range(len(job))]
    return lambda o: namen[o]


# ------------------------------------------------------------------------------------------------------------------------------ Job Shop
def jobshop_instanz(groesse: int, seed: int) -> Instance:
    """Quadratischer Job Shop `groesse` Aufträge × `groesse` Maschinen, Dauern 1 bis 9, deterministisch aus (groesse, seed)."""
    return make_jobshop(groesse, groesse, seed)


def optimum(inst: Instance, budget: int = 200000) -> tuple[int, bool]:
    """Optimaler Makespan nach dem Mini-CP (Stufe 2); (Wert, bewiesen). Bei erschöpftem Budget ist der Wert nur eine obere Schranke."""
    r = M.loese(inst, 2, budget=budget)
    return r.optimum, r.bewiesen


# ------------------------------------------------------------------------------------------------------------------------------ Rotationsplan
def lateinisches_quadrat(ordnung: int, seed: int) -> list:
    """Durchmischtes lateinisches Quadrat mit Werten 1..ordnung: Zyklentausch ab dem zyklischen Quadrat, 30 · ordnung² Tausche (wie in `alldifferent-demo`). Deterministisch aus (ordnung, seed)."""
    quadrat = [[(r + c) % ordnung for c in range(ordnung)] for r in range(ordnung)]
    if ordnung >= 2:
        rng = SplitMix64(seed)
        for _ in range(30 * ordnung * ordnung):
            r1 = rng.below(ordnung)
            r2 = rng.below(ordnung - 1)
            r2 = r2 if r2 < r1 else r2 + 1
            pos = {quadrat[r1][c]: c for c in range(ordnung)}
            c0 = rng.below(ordnung)
            zyklus, c = [], c0
            while True:
                zyklus.append(c)
                c = pos[quadrat[r2][c]]
                if c == c0:
                    break
            for c in zyklus:
                quadrat[r1][c], quadrat[r2][c] = quadrat[r2][c], quadrat[r1][c]
    return [[v + 1 for v in zeile] for zeile in quadrat]


def rotationsplan(ordnung: int, luecken_prozent: int, seed: int) -> dict:
    """Erfüllbarer Rotationsplan: ein durchmischtes Quadrat, aus dem (100 − Lücken) Prozent der Zellen zufällig vorbelegt bleiben (auf die nächste ganze Zahl gerundet, 0,5 nach oben).
    Rückgabe {(Zeile, Spalte): Schicht} der vorbelegten Zellen."""
    quadrat = lateinisches_quadrat(ordnung, seed)
    rng = SplitMix64(seed * 7919 + 13)
    zellen = [(r, c) for r in range(ordnung) for c in range(ordnung)]
    rng.shuffle(zellen)
    anzahl = (ordnung * ordnung * (100 - luecken_prozent) * 2 + 100) // 200
    return {(r, c): quadrat[r][c] for r, c in zellen[:anzahl]}
