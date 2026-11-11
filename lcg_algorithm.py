"""Kern dieser Demo (eigener Code, nur Standardbibliothek): Suche auf einer CNF mit und ohne Lernen, und ein AllDifferent-Propagator, der seine Schlüsse als Klauseln erklärt.

Zwei Unterklassen des kopierten CDCL-Kerns (`lcg_cdcl.Loeser`):

* `Suche` löst **dieselbe CNF** mit derselben Einheitspropagation, derselben Wertregel (immer „wahr“ zuerst) und Entscheidungen nur auf ausgewählten Variablen. Variiert werden nur
  - das **Lernen**: *aus* = chronologisches Zurückspringen (die letzte Entscheidung umdrehen, keine Klauseln, keine Neustarts); *an* = 1-UIP-Lernen mit Rücksprung, ohne Neustarts, ohne VSIDS;
  - die **Reihenfolge**: *statisch* (kleinste Variablennummer zuerst) oder *gewichtet* (jede Entscheidungsvariable in der Gründe-Wolke eines Konflikts bekommt +1, kein Zerfall;
    größtes Gewicht zuerst, Gleichstand kleinste Nummer). Das ist ein Konfliktgewicht (conflict-weighted degree), **nicht** dom/wdeg im Wortsinn: Boolesche Variablen haben immer Domänengröße 2.
* `HallLoeser` hängt an die CDCL-Schleife einen **AllDifferent-Propagator mit Erklärung**: bei jedem Fixpunkt der Einheitspropagation wird je Gruppe ein Matching (Wert je Variable) berechnet;
  findet es keine vollständige Zuordnung, ist die Gruppe verletzt; sonst fallen alle Werte weg, die in keiner vollständigen Zuordnung vorkommen (Régin). Zu jedem Schluss entsteht erst im Moment des Gebrauchs
  („lazy“) eine Klausel, die ihn als Folgerung der Anfangsdomänen begründet (Schubfachprinzip, siehe `erklaerungsklausel`).

`hall_analyse` und `erklaerungsklausel` sind reine Funktionen auf Domänen und werden von der Schritt-Ansicht der App und vom CDCL-Anschluss gemeinsam benutzt.
Aufwand wird in Konflikten gezählt (CNF) beziehungsweise Knoten (Mini-CP), nie in Sekunden.
"""

from dataclasses import dataclass, field

from lcg_cdcl import Loeser, solve


# ------------------------------------------------------------------------------------------------------------------------------ Suche (Lernen an/aus)
class Suche(Loeser):
    """Kern-CDCL mit fester Verzweigung (siehe Modulkopf). `entscheidungs_vars=None`: alle Variablen; `lernen` und `reihenfolge` sind die zwei Schalter des Vergleichs."""

    def __init__(self, n, klauseln, *, entscheidungs_vars=None, reihenfolge="statisch", lernen=True, wahr_zuerst=True, **kw):
        if reihenfolge not in ("statisch", "gewichtet"):
            raise ValueError("reihenfolge muss 'statisch' oder 'gewichtet' sein")
        kw.setdefault("restarts", "none")
        super().__init__(n, klauseln, learn=lernen, vsids=False, phase_saving=False, **kw)
        self.dvars = sorted(entscheidungs_vars) if entscheidungs_vars is not None else list(range(1, n + 1))
        self.reihenfolge = reihenfolge
        self.wahr_zuerst = wahr_zuerst
        self.gewicht = {}
        self._dmenge = set(self.dvars)

    def waehle(self):
        if self.reihenfolge == "gewichtet":
            best, bw = None, -1
            for v in self.dvars:
                if self.wert[v] == 0:
                    g = self.gewicht.get(v, 0)
                    if g > bw:
                        best, bw = v, g
            if best is not None:
                return best
        else:
            for v in self.dvars:
                if self.wert[v] == 0:
                    return v
        for v in range(1, self.n + 1):          # Rest (Variablen, die keine Entscheidungsvariablen sind)
            if self.wert[v] == 0:
                return v
        return None

    def waehle_literal(self, v):
        return v if self.wahr_zuerst else -v

    def propagiere(self):
        konflikt = super().propagiere()
        if konflikt is not None and self.reihenfolge == "gewichtet":
            gesehen, todo = set(), [abs(l) for l in self.klauseln[konflikt]]
            while todo:
                v = todo.pop()
                if v in gesehen:
                    continue
                gesehen.add(v)
                r = self.grund[v]
                if r is None:
                    if v in self._dmenge and self.stufe[v] > 0:
                        self.gewicht[v] = self.gewicht.get(v, 0) + 1
                else:
                    todo.extend(abs(l) for l in self.klauseln[r] if abs(l) != v)
        return konflikt


def suche(n, klauseln, *, lernen=True, reihenfolge="statisch", entscheidungs_vars=None, budget=None, trace=False):
    """Ein Lauf der `Suche`; gibt (Ergebnis, Loeser) zurück. `budget` = Konfliktbudget (None: unbegrenzt)."""
    s = Suche(n, klauseln, entscheidungs_vars=entscheidungs_vars, reihenfolge=reihenfolge, lernen=lernen, trace=trace)
    return s.loese(conflict_budget=budget), s


# ------------------------------------------------------------------------------------------------------------- Hall-Analyse und Erklärung (reine Funktionen)
def maximales_matching(doms):
    """Matching Variable -> Wert (Erweiterungspfade). Rückgabe (mate_var, mate_val, erste_nicht_zugeordnete_Variable oder None)."""
    mv, mval = {}, {}

    def erweitere(i, gesehen):
        for w in sorted(doms[i]):
            if w in gesehen:
                continue
            gesehen.add(w)
            if w not in mval or erweitere(mval[w], gesehen):
                mv[i] = w
                mval[w] = i
                return True
        return False

    for i in range(len(doms)):
        if not erweitere(i, set()):
            return mv, mval, i
    return mv, mval, None


def abschluss(start, doms, mval):
    """Variablen, die von `start` über „Variable → Wert aus der Domäne → Variable, der der Wert zugeordnet ist“ erreichbar sind; `frei`: ein freier Wert wird erreicht."""
    gesehen, todo, frei = {start}, [start], False
    while todo:
        u = todo.pop()
        for w in sorted(doms[u]):
            y = mval.get(w)
            if y is None:
                frei = True
            elif y not in gesehen:
                gesehen.add(y)
                todo.append(y)
    return gesehen, frei


def hall_analyse(doms):
    """Schlüsse des AllDifferent-Propagators auf den aktuellen Domänen (Liste von Mengen).

    Rückgabe ("fehl", S, V): keine vollständige Zuordnung; S = Abschluss einer nicht zuordenbaren Variablen, V = Vereinigung ihrer Domänen, |V| < |S| (Hall-Verletzung).
    Sonst ("ok", streichungen) mit Einträgen (x, w, R, V): der Wert w fällt aus der Domäne von x, weil R (eine Hall-Menge: Variablen, die sich die Werte V mit |V| = |R| teilen)
    den Wert w braucht. Jede Streichung kommt einmal vor (ein Wert hat genau eine zugeordnete Variable)."""
    mv, mval, schlecht = maximales_matching(doms)
    if schlecht is not None:
        s, _ = abschluss(schlecht, doms, mval)
        v = set()
        for u in s:
            v |= doms[u]
        return "fehl", sorted(s), sorted(v)
    streichungen = []
    for w in sorted(mval):
        y = mval[w]
        r, frei = abschluss(y, doms, mval)
        if frei:
            continue
        v = set()
        for u in r:
            v |= doms[u]
        for x in range(len(doms)):
            if x not in r and w in doms[x]:
                streichungen.append((x, w, sorted(r), sorted(v)))
    return "ok", streichungen


def erklaerungsklausel(doms0, x, w, R, V):
    """Erklärung einer Streichung (x, w) als Klausel über Paaren (Variable i, Wert v), Vorzeichen True = „i = v“, False = „i ≠ v“:

        x ≠ w  ∨  ⋁ { u = w' : u ∈ R, w' ∈ D₀(u) ∖ V }.

    Gilt in jeder Lösung der Anfangsdomänen `doms0` (Schubfachprinzip): Hat jede Variable aus R einen Wert in V, so teilen sich |R| Variablen |V| = |R| Werte, und alle Werte von V sind vergeben,
    also hat x nicht w. Für x = None (Fehlschlag einer Hall-Verletzung) entfällt der erste Term: Die Klausel besagt, dass nicht alle Variablen aus S ihre Werte in V haben können (|V| < |S|)."""
    lits = [] if x is None else [(x, w, False)]
    for u in R:
        for w2 in sorted(doms0[u]):
            if w2 not in V:
                lits.append((u, w2, True))
    return lits


# ------------------------------------------------------------------------------------------------------------------------------ CDCL mit Hall-Propagator
class _Unerfuellbar(Exception):
    pass


@dataclass
class Erklaerung:
    """Protokolleintrag zu einer vom Propagator erzeugten Klausel (für die Prüfung und die Anzeige)."""

    art: str            # "streichung" oder "fehlschlag"
    gruppe: int
    variable: int | None
    wert: int | None
    menge: tuple        # R beziehungsweise S (Variablen der Gruppe)
    werte: tuple        # V
    klausel: tuple      # Literale (Variablen der CNF, mit Vorzeichen)
    stufe: int          # Entscheidungsstufe beim Erzeugen


class HallLoeser(Loeser):
    """CDCL-Kern plus AllDifferent-Propagator mit Erklärung. `gruppen`: Liste von Gruppen; eine Gruppe ist eine Liste von Mitgliedern, ein Mitglied ein Wörterbuch {Wert: Variable der CNF}
    (Variable wahr = „das Mitglied hat diesen Wert“). Die CNF enthält die Klauseln der direkten Kodierung selbst; der Propagator ergänzt nur, was er zusätzlich schließt."""

    def __init__(self, n, klauseln, gruppen, *, protokoll=False, max_protokoll=5000, **kw):
        self.gruppen = [list(g) for g in gruppen]
        self.protokoll = [] if protokoll else None
        self.max_protokoll = max_protokoll
        self.hall_streichungen = 0
        self.hall_fehlschlaege = 0
        self.hall_aufrufe = 0
        self._bekannt = {}
        super().__init__(n, klauseln, **kw)

    def loese(self, annahmen=(), conflict_budget=None):
        try:
            return super().loese(annahmen, conflict_budget)
        except _Unerfuellbar:
            self.ok = False
            self.kern = []
            return self._ergebnis(False)

    def _dom(self, mitglied):
        return {w for w, v in mitglied.items() if self.wert[v] != -1}

    def _notiere(self, art, gi, x, w, menge, werte, klausel):
        if self.protokoll is not None and len(self.protokoll) < self.max_protokoll:
            self.protokoll.append(Erklaerung(art, gi, x, w, tuple(menge), tuple(werte), tuple(klausel), len(self.grenzen)))

    def _klausel(self, g, x, w, R, V):
        """Erklärungsklausel (`erklaerungsklausel`) als Literale der CNF; bei einer Streichung steht das erzwungene Literal `-g[x][w]` vorn."""
        doms0 = [set(m) for m in g]
        lits = [(g[u][w2] if pos else -g[u][w2]) for (u, w2, pos) in erklaerungsklausel(doms0, x, w, R, V)]
        return list(dict.fromkeys(lits))

    def propagiere(self):
        while True:
            konflikt = super().propagiere()
            if konflikt is not None:
                return konflikt
            r = self._hall_runde()
            if r is None:
                return None
            if r is not True:
                return r

    def _hall_runde(self):
        """Ein Durchgang über alle Gruppen. None: nichts geschlossen; True: Literale belegt (weiter propagieren); int: Index einer Konfliktklausel."""
        geaendert = False
        for gi, g in enumerate(self.gruppen):
            self.hall_aufrufe += 1
            doms = [self._dom(m) for m in g]
            if any(not d for d in doms):
                continue          # leere Domäne: „mindestens ein Wert“ ist verletzt, das findet die Einheitspropagation
            a = hall_analyse(doms)
            if a[0] == "fehl":
                _, S, V = a
                klausel = self._klausel(g, None, None, S, set(V))
                self.hall_fehlschlaege += 1
                self._notiere("fehlschlag", gi, None, None, S, V, klausel)
                return self._konfliktklausel(klausel)
            for (x, w, R, V) in a[1]:
                lit = -g[x][w]
                if self.wert_lit(lit) != 0:
                    continue
                klausel = self._klausel(g, x, w, R, set(V))
                self.hall_streichungen += 1
                self._notiere("streichung", gi, x, w, R, V, klausel)
                if self._schliesse(klausel):
                    return True       # Rücksprung auf Stufe 0: die übrigen Schlüsse dieser Runde gelten nicht mehr, neu rechnen
                geaendert = True
        return True if geaendert else None

    def _schliesse(self, klausel):
        """`klausel[0]` ist unbelegt, alle übrigen Literale sind falsch: belegt `klausel[0]` mit der Klausel als Grund (lazy erzeugt, einmal je Klausel gespeichert).
        Rückgabe True, wenn dafür auf Stufe 0 zurückgesprungen wurde (Einheitsklausel)."""
        c = list(dict.fromkeys(klausel))
        if len(c) == 1:
            self.springe_zurueck(0)
            if self.wert_lit(c[0]) == -1:
                raise _Unerfuellbar
            if self.wert_lit(c[0]) == 0:
                self._belege(c[0], None)
            return True
        schluessel = frozenset(c)
        idx = self._bekannt.get(schluessel)
        if idx is None:
            c = [c[0]] + sorted(c[1:], key=lambda l: -self.stufe[abs(l)])
            self._fuege_hinzu(c, True, 0)
            idx = len(self.klauseln) - 1
            self._bekannt[schluessel] = idx
        self._belege(klausel[0], idx)
        return False

    def _konfliktklausel(self, klausel):
        """Klausel, deren Literale alle falsch sind. Springt auf die höchste Stufe der Literale zurück und gibt den Index zurück; auf Stufe 0 ist die Formel unerfüllbar."""
        c = list(dict.fromkeys(klausel))
        if not c:
            raise _Unerfuellbar
        c.sort(key=lambda l: -self.stufe[abs(l)])
        oben = self.stufe[abs(c[0])]
        if oben == 0:
            raise _Unerfuellbar
        if len(c) == 1:                       # Einheitsklausel: gilt global
            self.springe_zurueck(0)
            self._belege(c[0], None)
            return True
        self.springe_zurueck(oben)
        self._fuege_hinzu(c, True, 0)
        return len(self.klauseln) - 1


def loese_mit_hall(n, klauseln, gruppen, *, budget=None, protokoll=False, **optionen):
    """Ein Lauf des `HallLoeser`; gibt (Ergebnis, Loeser) zurück."""
    s = HallLoeser(n, klauseln, gruppen, protokoll=protokoll, **optionen)
    return s.loese(conflict_budget=budget), s


# ------------------------------------------------------------------------------------------------------------------------- Prüfung einer Klausel gegen die CNF
@dataclass(frozen=True)
class Pruefung:
    urteil: str                   # "gueltig", "ungueltig", "unentschieden"
    gegenbeispiel: dict | None    # bei "ungueltig": ein Modell der CNF, das die Klausel verletzt
    konflikte: int                # Konflikte des Prüflaufs
    budget: int


def pruefe_klausel(n, klauseln, klausel, budget=20000) -> Pruefung:
    """Folgt `klausel` aus der CNF? Entscheidung mit dem Kern-CDCL: CNF plus verneinte Klausel (je Literal eine Einheitsklausel) muss unerfüllbar sein.
    „ungueltig“ kommt mit einem Gegenbeispiel (Modell der CNF, das die Klausel verletzt), „unentschieden“ bei erreichtem Budget."""
    zusatz = [[-l] for l in klausel]
    e = solve(n, [list(k) for k in klauseln] + zusatz, conflict_budget=budget)
    if e.antwort is False:
        return Pruefung("gueltig", None, e.stat["konflikte"], budget)
    if e.antwort is True:
        return Pruefung("ungueltig", e.modell, e.stat["konflikte"], budget)
    return Pruefung("unentschieden", None, e.stat["konflikte"], budget)


# ------------------------------------------------------------------------------------------------------------------ Schritt-für-Schritt (Domänenebene, für die App)
def hall_schritte(doms0, entscheidungen=()):
    """Schlüsse des Propagators Schritt für Schritt auf Domänen (Listen von Mengen), mit der Erklärungsklausel zu jedem Schluss.

    `entscheidungen`: Folge von (Variable, Wert), die als „Variable ≠ Wert“ in die Domäne eingreifen (ein Entscheidungsschritt je Eintrag, danach läuft der Propagator bis zum Fixpunkt).
    Rückgabe: Liste von Ereignissen (Wörterbücher) mit dem Schlüssel `art` ∈ {start, entscheidung, streichung, fehlschlag, fixpunkt} und `doms` (Domänen danach, Listen sortierter Werte);
    `streichung` hat `var`, `wert`, `menge` (Hall-Menge R), `werte` (V) und `klausel` (Literale (Variable, Wert, Vorzeichen) der Erklärung), `fehlschlag` hat `menge`, `werte` und `klausel`."""
    doms = [set(d) for d in doms0]
    d0 = [set(d) for d in doms0]

    def kopie():
        return [sorted(d) for d in doms]

    ereignisse = [{"art": "start", "doms": kopie()}]

    def propagiere():
        while True:
            leer = next((i for i, d in enumerate(doms) if not d), None)
            if leer is not None:          # leere Domäne: die Klausel „mindestens ein Wert der Anfangsdomäne“ ist verletzt
                ereignisse.append({"art": "fehlschlag", "menge": [leer], "werte": [], "klausel": erklaerungsklausel(d0, None, None, [leer], set()), "doms": kopie()})
                return
            a = hall_analyse(doms)
            if a[0] == "fehl":
                _, S, V = a
                ereignisse.append({"art": "fehlschlag", "menge": S, "werte": V, "klausel": erklaerungsklausel(d0, None, None, S, set(V)), "doms": kopie()})
                return
            if not a[1]:
                ereignisse.append({"art": "fixpunkt", "doms": kopie()})
                return
            x, w, R, V = a[1][0]
            klausel = erklaerungsklausel(d0, x, w, R, set(V))
            doms[x].discard(w)
            ereignisse.append({"art": "streichung", "var": x, "wert": w, "menge": R, "werte": V, "klausel": klausel, "doms": kopie()})

    for (x, w) in entscheidungen:
        doms[x].discard(w)
        ereignisse.append({"art": "entscheidung", "var": x, "wert": w, "doms": kopie()})
    propagiere()
    return ereignisse


def klausel_text(klausel, namen=None) -> str:
    """Erklärungsklausel (Literale (Variable, Wert, Vorzeichen)) als Text, zum Beispiel „x3 ≠ 1 ∨ x1 = 3“; die leere Klausel heißt „(leer)“."""
    namen = namen or (lambda i: f"x{i + 1}")
    if not klausel:
        return "(leer: Widerspruch)"
    return " ∨ ".join(f"{namen(i)} {'=' if pos else '≠'} {w}" for i, w, pos in klausel)
