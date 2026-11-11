"""Order-Kodierung des Job Shops als CNF und die direkte Kodierung von AllDifferent (eigener Code dieser Demo, nur Standardbibliothek).

**Order-Kodierung.** Zu jeder Operation o und jeder Zeit t gibt es eine Variable `x[o, t]` mit der Bedeutung „o beginnt spätestens zur Zeit t“ (s_o ≤ t).
Das Fenster der Startzeit ist `[est_o, lst_o]`; für t < est_o ist `x[o, t]` falsch, für t ≥ lst_o wahr, Variablen gibt es nur für t von est_o bis lst_o − 1 (Konstanten
werden beim Bau herausgekürzt, eine Klausel mit einem wahren Literal entfällt). Klauseln:
  * Monotonie:  x[o, t] → x[o, t + 1];
  * Vorrang in einem Auftrag (o vor p):  x[p, t] → x[o, t − d_o];
  * je Paar (a, b) auf einer Maschine eine Reihenfolgevariable y = „a vor b“:  y ∧ x[b, t] → x[a, t − d_a]  und  ¬y ∧ x[a, t] → x[b, t − d_b].
Mit `schranken=False` ist das Fenster `[0, H − d_o]` (so zählt das Handbeispiel H3 der Planung); mit `schranken=True` (Standard der Messungen) liegt der frühest mögliche Start
beim Vorlauf des Auftrags und der späteste bei H minus der Restdauer (Kopf- und Schwanzdauern).
Entscheidungsvariablen der Suche sind nur die Reihenfolgevariablen y; die Startzeiten ergeben sich durch Einheitspropagation.

**Direkte Kodierung von AllDifferent.** Je Variable i und Wert w aus ihrer Anfangsdomäne eine Variable `x[i, w]` („i hat den Wert w“), mindestens ein Wert je Variable,
höchstens ein Wert je Variable (paarweise), und je Wert höchstens eine Variable (paarweise).
"""

from dataclasses import dataclass, field
from itertools import combinations

TRUE, FALSE = "T", "F"


def _neg(lit):
    return FALSE if lit == TRUE else TRUE if lit == FALSE else -lit


@dataclass
class Kodierung:
    """CNF eines Job-Shop-Entscheidungsproblems „Makespan ≤ H“."""

    n_var: int
    klauseln: list
    horizont: int
    leer: bool                       # schon beim Bau eine leere Klausel (Fenster einer Operation leer)
    est: list
    lst: list
    d: list
    maschine: list
    var: dict = field(default_factory=dict)        # (Operation, t) -> Variable von [s_o ≤ t]
    paar: dict = field(default_factory=dict)       # (a, b) -> Variable „a vor b“
    ketten: list = field(default_factory=list)     # (o, p): p folgt o im Auftrag

    @property
    def entscheidungs_vars(self) -> list:
        return sorted(self.paar.values())

    def _rueck(self) -> dict:
        """Variable -> ("paar", a, b) oder ("start", o, t), einmal aufgebaut."""
        r = getattr(self, "_rueck_tabelle", None)
        if r is None:
            r = {y: ("paar", a, b) for (a, b), y in self.paar.items()}
            r.update({x: ("start", o, t) for (o, t), x in self.var.items()})
            self._rueck_tabelle = r
        return r

    def name(self, v: int, ops=None) -> str:
        """Lesbarer Name einer Variablen: „a vor d“ oder „[s_a ≤ 3]“; `ops` übersetzt Operationsnummern in Namen."""
        ops = ops or (lambda o: f"o{o}")
        art, p, q = self._rueck()[v]
        return f"{ops(p)} vor {ops(q)}" if art == "paar" else f"[s_{ops(p)} ≤ {q}]"

    def literal_text(self, lit: int, ops=None) -> str:
        """Text eines Literals; ein negiertes Paar-Literal liest sich als umgekehrte Reihenfolge („d vor a“), jedes andere als „nicht [s_a ≤ 3]“."""
        ops = ops or (lambda o: f"o{o}")
        art, p, q = self._rueck()[abs(lit)]
        if art == "paar":
            return f"{ops(p)} vor {ops(q)}" if lit > 0 else f"{ops(q)} vor {ops(p)}"
        return f"[s_{ops(p)} ≤ {q}]" if lit > 0 else f"nicht [s_{ops(p)} ≤ {q}]"


def fenster(jobs, H: int, schranken: bool = True):
    """(est, lst, d, maschine, ketten) je Operation; Operation (j, k) hat die Nummer `Summe der Längen der Aufträge davor + k`."""
    est, lst, d, mc, ketten = [], [], [], [], []
    for job in jobs:
        basis = len(d)
        rest = sum(p for _, p in job)
        vorlauf = 0
        for k, (m, p) in enumerate(job):
            d.append(p)
            mc.append(m)
            est.append(vorlauf if schranken else 0)
            lst.append(H - rest if schranken else H - p)
            vorlauf += p
            rest -= p
            if k:
                ketten.append((basis + k - 1, basis + k))
    return est, lst, d, mc, ketten


def kodiere_jobshop(jobs, H: int, schranken: bool = True) -> Kodierung:
    """CNF zu „gibt es einen Plan mit Makespan ≤ H?“ (Aufbau siehe Modulkopf). `jobs[j][k] = (Maschine, Dauer)`."""
    est, lst, d, mc, ketten = fenster(jobs, H, schranken)
    n = len(d)
    if any(lst[o] < est[o] for o in range(n)):
        return Kodierung(0, [[]], H, True, est, lst, d, mc, {}, {}, ketten)
    var, nv = {}, 0
    for o in range(n):
        for t in range(est[o], lst[o]):
            nv += 1
            var[(o, t)] = nv

    def le(o, t):
        if t >= lst[o]:
            return TRUE
        if t < est[o]:
            return FALSE
        return var[(o, t)]

    klauseln, gesehen = [], set()
    leer = [False]

    def add(lits):
        out = []
        for l in lits:
            if l == TRUE:
                return
            if l != FALSE:
                out.append(l)
        if not out:
            leer[0] = True                                   # die leere Klausel gehört zur CNF (sie macht sie unerfüllbar) und zählt als Klausel
        k = tuple(sorted(set(out)))
        if k not in gesehen:
            gesehen.add(k)
            klauseln.append(list(k))

    for o in range(n):                                       # Monotonie
        for t in range(est[o], lst[o] - 1):
            add([_neg(le(o, t)), le(o, t + 1)])
    for o, p in ketten:                                      # Vorrang im Auftrag
        for t in range(est[p], lst[p] + 1):
            add([_neg(le(p, t)), le(o, t - d[o])])
    paar = {}
    for m in sorted(set(mc)):
        ops = [o for o in range(n) if mc[o] == m]
        for a, b in combinations(ops, 2):
            nv += 1
            y = nv
            paar[(a, b)] = y
            for t in range(est[b], lst[b] + 1):              # a vor b
                add([-y, _neg(le(b, t)), le(a, t - d[a])])
            for t in range(est[a], lst[a] + 1):              # b vor a
                add([y, _neg(le(a, t)), le(b, t - d[b])])
    return Kodierung(nv, klauseln, H, leer[0], est, lst, d, mc, var, paar, ketten)


def plan_aus_modell(kod: Kodierung, modell: dict) -> list:
    """Startzeiten aus einem Modell der CNF: kleinstes t mit wahrem [s_o ≤ t], sonst der späteste Start."""
    starts = []
    for o in range(len(kod.d)):
        t_start = kod.lst[o]
        for t in range(kod.est[o], kod.lst[o]):
            if modell[kod.var[(o, t)]]:
                t_start = t
                break
        starts.append(t_start)
    return starts


# ------------------------------------------------------------------------------------------------------------- AllDifferent, direkte Kodierung
@dataclass
class AllDiffKodierung:
    n_var: int
    klauseln: list
    var: dict                      # (i, w) -> Variable „i hat den Wert w“
    domaenen: list                 # Anfangsdomänen (sortierte Listen)
    gruppen: list = field(default_factory=list)   # je Gruppe eine Liste von Mitgliedern {Wert: Variable} (Eingabe des `HallLoeser`)

    def literal_text(self, lit: int, namen=None) -> str:
        namen = namen or (lambda i: f"x{i + 1}")
        for (i, w), v in self.var.items():
            if v == abs(lit):
                return f"{namen(i)} = {w}" if lit > 0 else f"{namen(i)} ≠ {w}"
        raise KeyError(lit)


def kodiere_alldifferent(domaenen, gruppen=None) -> AllDiffKodierung:
    """Direkte Kodierung (siehe Modulkopf). `domaenen[i]`: erlaubte Werte der Variablen i; `gruppen`: Liste von Gruppen (Listen von Variablenindizes),
    in jeder müssen die Werte paarweise verschieden sein (Standard: eine Gruppe über alle Variablen)."""
    doms = [sorted(set(d)) for d in domaenen]
    if gruppen is None:
        gruppen = [list(range(len(doms)))]
    var, nv = {}, 0
    for i, d in enumerate(doms):
        for w in d:
            nv += 1
            var[(i, w)] = nv
    klauseln, gesehen = [], set()

    def add(k):
        key = tuple(sorted(k))
        if key not in gesehen:
            gesehen.add(key)
            klauseln.append(list(k))

    for i, d in enumerate(doms):
        add([var[(i, w)] for w in d])
        for a, b in combinations(d, 2):
            add([-var[(i, a)], -var[(i, b)]])
    for g in gruppen:
        for w in sorted({w for i in g for w in doms[i]}):
            trager = [i for i in g if w in doms[i]]
            for i, j in combinations(trager, 2):
                add([-var[(i, w)], -var[(j, w)]])
    gruppen_map = [[{w: var[(i, w)] for w in doms[i]} for i in g] for g in gruppen]
    return AllDiffKodierung(nv, klauseln, var, doms, gruppen_map)


def schubfach_gruppe(h: int):
    """Schubfach h + 1 Tauben auf h Löcher als AllDifferent-Gruppe: Variable (Taube p, Loch l) = p*h + l + 1 wie in `lcg_instanzen.pigeonhole`.
    Rückgabe: Liste der Mitglieder, jedes ein Wörterbuch {Loch: Variable}."""
    return [{loch: p * h + loch + 1 for loch in range(h)} for p in range(h + 1)]


def rotationsplan_domaenen(ordnung: int, vorbelegt: dict):
    """Rotationsplan (lateinisches Quadrat mit Vorbelegung) als Domänenliste und Gruppen: Zelle (r, c) ist Variable r * ordnung + c mit Werten 1..ordnung
    (vorbelegte Zellen: nur ihr Wert); Gruppen sind zuerst die Zeilen, dann die Spalten."""
    doms = [[vorbelegt[(r, c)]] if (r, c) in vorbelegt else list(range(1, ordnung + 1)) for r in range(ordnung) for c in range(ordnung)]
    zeilen = [[r * ordnung + c for c in range(ordnung)] for r in range(ordnung)]
    spalten = [[r * ordnung + c for r in range(ordnung)] for c in range(ordnung)]
    return doms, zeilen + spalten
