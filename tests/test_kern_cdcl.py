"""Regressionstests der kopierten Kern-Einheiten (aus sat-cp-planung/kern/tests/test_cdcl_einheiten.py, Importe auf lcg_ umgestellt, sonst unverändert)."""
import pytest

from lcg_cdcl import Loeser, luby, solve


def test_luby_folge():
    assert [luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]
    with pytest.raises(ValueError):
        luby(0)


def test_propagation_kette():
    # Auf Stufe 0 werden Klauseln schon beim Aufnehmen vereinfacht: (x1)(¬x1 ∨ x2)(¬x2 ∨ x3) ergibt die Einheiten 1, 2, 3 ohne Grund.
    for watch in (True, False):
        s = Loeser(3, [(1,), (-1, 2), (-2, 3)], watch=watch)
        assert s.propagiere() is None
        assert [s.wert[v] for v in (1, 2, 3)] == [1, 1, 1] and s.spur_lit == [1, 2, 3]
        assert not s.grenzen and s.grund[2] is None
        # Auf einer Entscheidungsstufe dagegen: Entscheidung 1 → 2 (Klausel 0) → 3 (Klausel 1), mit Begründungen
        t = Loeser(3, [(-1, 2), (-2, 3)], watch=watch)
        t.entscheide(1)
        assert t.propagiere() is None
        assert t.spur_lit == [1, 2, 3] and t.grund[1] is None and t.grund[2] == 0 and t.grund[3] == 1
        assert [t.stufe[v] for v in (1, 2, 3)] == [1, 1, 1]


def test_widerspruch_schon_beim_aufnehmen():
    # (x1)(¬x1 ∨ x2)(¬x1 ∨ ¬x2): auf Stufe 0 vereinfacht die dritte Klausel zur leeren Klausel
    s = Loeser(2, [(1,), (-1, 2), (-1, -2)])
    assert s.ok is False
    erg = solve(2, [(1,), (-1, 2), (-1, -2)], proof=True)
    assert erg.antwort is False and erg.kern == [] and erg.beweis == [("a", [])]


def lehrbeispiel(watch=True, **kw):
    # Von Hand: c1 = (¬1 ∨ 2), c2 = (¬1 ∨ 3 ∨ 5), c3 = (¬2 ∨ 4), c4 = (¬3 ∨ ¬4)
    return Loeser(5, [(-1, 2), (-1, 3, 5), (-2, 4), (-3, -4)], watch=watch, **kw)


@pytest.mark.parametrize("watch", [True, False])
def test_konfliktanalyse_1uip_handrechnung(watch):
    """Entscheidung ¬5 (Stufe 1), dann 1 (Stufe 2): 1 → 2 (c1), 1 ∧ ¬5 → 3 (c2), 2 → 4 (c3), c4 ist verletzt.
    1-UIP ist die Entscheidung 1 selbst (sie liegt auf beiden Wegen zum Konflikt). Gelernt wird (¬1 ∨ 5),
    Rücksprung auf Stufe 1 (Stufe von 5), LBD 2; dort erzwingt die Klausel ¬1."""
    s = lehrbeispiel(watch)
    s.entscheide(-5)
    assert s.propagiere() is None
    s.entscheide(1)
    k = s.propagiere()
    assert k is not None
    klausel, rueck, lbd = s.analysiere(k)
    assert sorted(klausel) == [-1, 5] and klausel[0] == -1      # Auslöser ¬1 an Position 0
    assert rueck == 1 and lbd == 2


def test_rueckspruengen_stellt_zustand_her():
    s = lehrbeispiel()
    s.entscheide(-5)
    s.propagiere()
    s.entscheide(1)
    s.propagiere()
    assert len(s.grenzen) == 2 and s.wert[4] == 1
    s.springe_zurueck(1)
    assert len(s.grenzen) == 1 and s.spur_lit == [-5]
    assert [s.wert[v] for v in (1, 2, 3, 4)] == [0, 0, 0, 0] and s.wert[5] == -1
    s.springe_zurueck(0)
    assert s.spur_lit == [] and s.wert[5] == 0
    assert s.gemerkt[5] is False and s.gemerkt[1] is True       # Phasenspeicher: 1 war zuletzt wahr


def test_spur_enthaelt_ereignisse():
    # (1 ∨ 2 ∨ 3)(¬1 ∨ 2)(¬2 ∨ 3): Entscheidung ¬1, dann ¬2, dann erzwingt (1 ∨ 2 ∨ 3) die 3
    erg = solve(3, [(1, 2, 3), (-1, 2), (-2, 3)], trace=True, vsids=False)
    assert erg.antwort is True
    assert erg.spur[0][:3] == ("entscheide", -1, 1) and erg.spur[0][3]["art"] == "reihenfolge"
    assert any(e[0] == "schliesse" and e[1] == 3 and sorted(e[2]) == [1, 2, 3] and e[3] == 2 for e in erg.spur)
    kon = solve(*__import__("lcg_instanzen").pigeonhole(3)[:2], trace=True)
    arten = {e[0] for e in kon.spur}
    assert {"entscheide", "schliesse", "konflikt", "lerne", "springe"} <= arten


def test_minimierung_handrechnung():
    """Klauseln (¬1 ∨ 2), (¬3 ∨ ¬1 ∨ ¬2 ∨ 4), (¬3 ∨ ¬1 ∨ ¬2 ∨ ¬4). Entscheidung 1 (Stufe 1) erzwingt 2; Entscheidung 3 (Stufe 2)
    erzwingt 4 und verletzt die dritte Klausel. 1-UIP ist die Entscheidung 3, gelernt wird (¬3 ∨ ¬1 ∨ ¬2); ¬2 ist durch
    (¬1 ∨ 2) schon von ¬1 abgedeckt und entfällt bei der Minimierung: (¬3 ∨ ¬1), Rücksprung auf Stufe 1."""
    klauseln = [(-1, 2), (-3, -1, -2, 4), (-3, -1, -2, -4)]
    ergebnisse = {}
    for minimiere in (False, True):
        s = Loeser(4, klauseln, minimize=minimiere)
        s.entscheide(1)
        assert s.propagiere() is None and s.wert[2] == 1
        s.entscheide(3)
        k = s.propagiere()
        assert k is not None
        klausel, rueck, lbd = s.analysiere(k)
        ergebnisse[minimiere] = (sorted(klausel), klausel[0], rueck, lbd)
    assert ergebnisse[False] == ([-3, -2, -1], -3, 1, 2)
    assert ergebnisse[True] == ([-3, -1], -3, 1, 2)


def test_loeschregel_handrechnung():
    """Gelernte Klauseln mit LBD 2, 2, 3, 4, 5, 6: Kandidaten sind die vier mit LBD > 2 (3, 4, 5, 6); die schlechtere Hälfte
    (zwei Stück) fällt weg, also LBD 6 und LBD 5. LBD 2 bleibt immer."""
    s = Loeser(12, [], delete=True, proof=True)
    indizes = []
    for lbd, klausel in zip([2, 2, 3, 4, 5, 6], [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]):
        s._fuege_hinzu(list(klausel), True, lbd)
        indizes.append(len(s.klauseln) - 1)
    weg = s._reduziere()
    assert sorted(weg) == [indizes[4], indizes[5]]
    assert [s.geloescht[i] for i in indizes] == [False, False, False, False, True, True]
    assert s.stat["geloescht"] == 2
    assert sorted(map(tuple, (c for _, c in s.beweis))) == [(9, 10), (11, 12)] and all(a == "d" for a, _ in s.beweis)


def test_loeschregel_sperrt_gruende():
    """Drei gelernte Klauseln mit LBD 9; Klausel 0 begründet gerade das Literal 2 und ist gesperrt. Kandidaten sind 1 und 2,
    die Hälfte (eine) fällt weg: bei Gleichstand in (LBD, Länge) zuerst die mit dem kleineren Index 1."""
    s = Loeser(6, [], delete=True)
    for k in ([1, 2], [3, 4], [5, 6]):
        s._fuege_hinzu(k, True, 9)
    s.entscheide(-1)
    assert s.propagiere() is None and s.wert[2] == 1 and s.grund[2] == 0
    weg = s._reduziere()
    assert weg == [1] and s.geloescht == [False, True, False]


def test_beobachter_invariante():
    """Nach dem Lösen beobachtet jede lebende Klausel mit mindestens zwei Literalen ihre ersten beiden Positionen."""
    from lcg_instanzen import rand3
    inst = rand3(40, 170, 3)
    s = Loeser(inst.n, inst.klauseln, delete=True, delete_every=20)
    s.loese()
    for i, c in enumerate(s.klauseln):
        if s.geloescht[i]:
            continue
        assert i in s.beobachtet[c[0]] and i in s.beobachtet[c[1]]


def test_annahmen_und_kern():
    # (¬a ∨ b), (¬b ∨ c) mit a = 1, b = 2, c = 3, d = 4 (frei)
    klauseln = [(-1, 2), (-2, 3)]
    ok = solve(4, klauseln, annahmen=[1])
    assert ok.antwort is True and ok.modell[1] and ok.modell[2] and ok.modell[3]
    schlecht = solve(4, klauseln, annahmen=[1, 4, -3])
    assert schlecht.antwort is False
    assert sorted(schlecht.kern) == [-3, 1]                   # die freie Annahme 4 gehört nicht zum Kern
    leer = solve(1, [(1,), (-1,)], annahmen=[1])
    assert leer.antwort is False and leer.kern == []
    with pytest.raises(ValueError):
        solve(4, klauseln, annahmen=[1], learn=False)


def test_inkrementell_und_neue_variable():
    s = Loeser(2, [(1, 2)])
    assert s.loese().antwort is True
    h = s.neue_variable()
    assert h == 3
    s.fuege_klausel_hinzu((-1,))
    s.fuege_klausel_hinzu((-2, h))
    s.fuege_klausel_hinzu((-h,))
    assert s.loese().antwort is False


def test_budget_und_zaehler():
    from lcg_instanzen import pigeonhole
    inst = pigeonhole(6)
    erg = solve(inst.n, inst.klauseln, conflict_budget=50)
    assert erg.antwort is None and erg.stat["konflikte"] == 50
    voll = solve(inst.n, inst.klauseln)
    assert voll.antwort is False
    for schluessel in ("konflikte", "entscheidungen", "propagationen", "besuche", "lesezugriffe", "gelernt", "neustarts", "geloescht"):
        assert schluessel in voll.stat
    assert 0 < voll.stat["gelernt"] <= voll.stat["konflikte"]


def test_spur_begrenzt():
    from lcg_instanzen import pigeonhole
    inst = pigeonhole(6)
    erg = solve(inst.n, inst.klauseln, trace=True)
    assert len(erg.spur) == 5000 and erg.spur_gekuerzt is True
    klein = solve(3, [(1, 2), (-1, 3)], trace=True)
    assert not klein.spur_gekuerzt and len(klein.spur) < 5000


def test_ohne_lernen_ist_chronologisch_und_korrekt():
    from lcg_instanzen import pigeonhole, rand3
    erg = solve(*pigeonhole(4)[:2], learn=False)
    assert erg.antwort is False
    inst = rand3(30, 120, 1)
    a, b = solve(inst.n, inst.klauseln, learn=False), solve(inst.n, inst.klauseln)
    assert a.antwort == b.antwort and a.stat["gelernt"] == 0


def test_phasenspeicher_und_statische_wahl():
    s = Loeser(3, [(1, 2, 3)], vsids=False)
    assert s.waehle() == 1                                     # feste Reihenfolge: kleinste offene Variable
    s.entscheide(-1)
    assert s.waehle() == 2
    assert s.waehle_literal(2) == -2                           # anfangs falsch
    t = Loeser(3, [(1, 2, 3)], phase_saving=False)
    t.gemerkt[2] = True
    assert t.waehle_literal(2) == -2
