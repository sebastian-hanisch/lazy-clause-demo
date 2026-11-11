"""Randfälle (DEMO-PLAYBOOK §12): ein Auftrag, eine Maschine, Horizont kürzer als die längste Kette, Gruppen ohne Hall-Menge, Schubfach h = 1 und 2, leere Eingaben."""

import pytest
from orakel import plan_ok

import lcg_algorithm as A
import lcg_aufzaehlung as Z
import lcg_evaluation as E
import lcg_instanzen as I
import lcg_kodierung as K
import lcg_scenario as S
from lcg_cdcl import solve
from lcg_jobshop import as_instance


def _alle_varianten(kod, budget=1000):
    return [A.suche(kod.n_var, kod.klauseln, lernen=l, reihenfolge=r, entscheidungs_vars=kod.entscheidungs_vars, budget=budget)[0]
            for l in (False, True) for r in ("statisch", "gewichtet")]


def test_ein_auftrag_optimum_ist_die_kettenlaenge():
    jobs = [[(0, 2), (1, 3), (2, 1)]]
    assert Z.optimum_aufzaehlung(jobs) == 6
    kod = K.kodiere_jobshop(jobs, 5)
    assert kod.leer and kod.paar == {} and kod.entscheidungs_vars == []
    assert all(e.antwort is False and e.stat["konflikte"] == 0 for e in _alle_varianten(kod))
    kod = K.kodiere_jobshop(jobs, 6)
    for e in _alle_varianten(kod):
        assert e.antwort is True and K.plan_aus_modell(kod, e.modell) == [0, 2, 5] and plan_ok(jobs, K.plan_aus_modell(kod, e.modell), 6)


def test_eine_maschine_aufgaben_hintereinander():
    jobs = [[(0, 2)], [(0, 3)], [(0, 1)]]                  # drei Aufträge, eine Maschine: Optimum = Summe 6
    assert Z.optimum_aufzaehlung(jobs) == 6
    assert S.optimum(as_instance(jobs)) == (6, True)
    for H, erwartet in ((5, False), (6, True), (7, True)):
        kod = K.kodiere_jobshop(jobs, H)
        for e in _alle_varianten(kod):
            assert e.antwort is erwartet
            if erwartet:
                assert plan_ok(jobs, K.plan_aus_modell(kod, e.modell), H)
    assert len(Z.jobshop_plaene(jobs, 6)) == 6               # 3! Reihenfolgen, ohne Lücke


def test_horizont_kuerzer_als_die_laengste_kette_gibt_die_leere_klausel_vor_der_suche(h2_jobs):
    kod = K.kodiere_jobshop(h2_jobs, 2, schranken=False)                  # 2 < Kette 3
    assert kod.leer and [] in kod.klauseln
    kod2 = K.kodiere_jobshop(h2_jobs, 2, schranken=True)
    assert kod2.leer and kod2.klauseln == [[]] and kod2.n_var == 0
    for k in (kod, kod2):
        for e in _alle_varianten(k):
            assert e.antwort is False and e.stat["konflikte"] == 0
        assert solve(k.n_var, [list(c) for c in k.klauseln]).antwort is False
    assert E.wurzel_literale(kod2.n_var, kod2.klauseln) is None


def test_horizont_null_und_eine_operation_die_nicht_passt():
    kod = K.kodiere_jobshop([[(0, 3)]], 2)
    assert kod.leer
    kod = K.kodiere_jobshop([[(0, 3)]], 3)
    e, _ = A.suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars)
    assert e.antwort is True and K.plan_aus_modell(kod, e.modell) == [0]


def test_gruppe_ohne_hall_menge_erzeugt_keine_klausel():
    kod = K.kodiere_alldifferent([[1, 2, 3, 4, 5]] * 3)
    e, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen, protokoll=True)
    assert e.antwort is True and s.hall_streichungen == 0 and s.hall_fehlschlaege == 0 and s.protokoll == []
    assert A.hall_schritte([{1, 2, 3}] * 3)[-1]["art"] == "fixpunkt" and len(A.hall_schritte([{1, 2, 3}] * 3)) == 2


def test_einzelne_variable_und_leere_gruppe():
    assert A.hall_analyse([{4}]) == ("ok", [])
    assert A.hall_analyse([]) == ("ok", [])
    kod = K.kodiere_alldifferent([[7]])
    e, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen)
    assert e.antwort is True and e.modell[kod.var[(0, 7)]] is True


def test_leere_domaene_ist_ein_fehlschlag_mit_gueltiger_erklaerung():
    ev = A.hall_schritte([{1, 2}, {1, 2}], [(0, 1), (0, 2)])
    assert ev[-1]["art"] == "fehlschlag" and ev[-1]["menge"] == [0]
    assert ev[-1]["klausel"] == [(0, 1, True), (0, 2, True)]                 # „x1 hat einen Wert seiner Anfangsdomäne“


@pytest.mark.parametrize("h,fehlschlaege", [(1, 0), (2, 1)])
def test_schubfach_h1_und_h2(h, fehlschlaege):
    """h = 1: zwei Tauben auf ein Loch; die Einheitsklauseln der Kodierung widersprechen sich schon beim Aufnehmen (kein Propagator-Aufruf, kein Konflikt). h = 2: ein Fehlschlag des Propagators an der Wurzel."""
    inst = I.pigeonhole(h)
    kl = [list(k) for k in inst.klauseln]
    assert solve(inst.n, kl).antwort is False
    e, s = A.loese_mit_hall(inst.n, kl, [K.schubfach_gruppe(h)], protokoll=True)
    assert e.antwort is False and e.stat["konflikte"] == 0 and s.hall_fehlschlaege == fehlschlaege
    assert len(s.protokoll) == fehlschlaege and all(x.klausel == () for x in s.protokoll)


def test_verteilung_leer_und_nur_abbrueche():
    assert E.verteilung([], 100)["n"] == 0
    v = E.verteilung([None, None, None], 100)
    assert v["median"] == 100 and v["max"] == 100 and v["abbrueche"] == 3
    v = E.verteilung([1, 3], 100)
    assert v["median"] == 2.0 and v["p90"] == 3                              # nächster Rang ⌈0,9·2⌉ = 2


def test_verhaeltnis_schuetzt_vor_null():
    assert E.verhaeltnis(0, 0) == 1.0 and E.verhaeltnis(6, 0) == 6.0 and E.verhaeltnis(0, 4) == 0.25


def test_zahlenformat():
    assert E.zahl(27932) == "27 932" and E.zahl(4085.5) == "4 085,5" and E.zahl(3.0) == "3" and E.zahl(0) == "0"
    assert E.konflikte_text(1) == "1 Konflikt" and E.konflikte_text(0) == "0 Konflikte" and E.konflikte_text(1004) == "1 004 Konflikte"
    assert E.faktor_text(2.84) == "2,8-fach"


def test_aufzaehlung_grenze_und_unmoegliches_optimum():
    jobs = [[(0, 1)] * 1 for _ in range(8)]
    with pytest.raises(ValueError):
        Z.jobshop_plaene(jobs, 8)
    assert Z.optimum_aufzaehlung([[(0, 9)]], H_max=5) is None


def test_rotationsplan_ein_mal_eins_und_volle_vorbelegung():
    doms, gruppen = K.rotationsplan_domaenen(1, {})
    assert doms == [[1]] and gruppen == [[0], [0]]
    kod = K.kodiere_alldifferent(doms, gruppen)
    e, _ = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen)
    assert e.antwort is True
    vor = S.rotationsplan(5, 0, 3)                                              # 0 % Lücken: alle 25 Zellen vorbelegt
    assert len(vor) == 25
    assert len(S.rotationsplan(5, 100, 3)) == 0                                 # 100 % Lücken: nichts vorbelegt
