"""Einheiten von Hand: Handbeispiele H1 (Hall-Erklärung), H2 (Mini-Job-Shop) und H3 (Order-Kodierung als CNF), jeder Sollwert ist von Hand nachgerechnet.

Handrechnung H1: x1 ∈ {1,2,3}, x2 ∈ {1,2}, x3 ∈ {1,2,3}, alle verschieden. Lösungen (x1,x2,x3): (1,2,3), (2,1,3), (3,1,2), (3,2,1), also 4. Nach der Entscheidung x1 ≠ 3 bleiben (1,2,3) und (2,1,3):
x3 = 3 immer. Der Propagator sieht {x1, x2} als Hall-Menge mit den Werten {1, 2}; 1 und 2 fallen aus x3, die Erklärung zur Streichung (x3, 1) ist „x3 ≠ 1 ∨ x1 = 3“
(Anfangsdomäne von x1 ohne {1,2} ist {3}, die von x2 ohne {1,2} ist leer).
Handrechnung H2: a(M1,2) → b(M2,1), c(M2,2) → d(M1,1). Pläne mit Makespan ≤ H: H = 2: 0, H = 3: 1 (a=0, b=2, c=0, d=2), H = 4: 7, H = 5: 26. Bei H = 4 gelten in allen 7 Plänen „a vor d“ und „c vor b“.
Fenster bei H = 4 mit Vorrang: est = (0, 2, 0, 2), lst = (1, 3, 1, 3) (lst_b = lst_d = 4 − 1 = 3, daraus lst_a = lst_c = 3 − 2 = 1)."""

import pytest
from orakel import plan_ok, zaehle_modelle

import lcg_algorithm as A
import lcg_aufzaehlung as Z
import lcg_instanzen as I
import lcg_kodierung as K
import lcg_scenario as S
from lcg_cdcl import solve


# ---------------------------------------------------------------------------------------------------------------------------------------------------- H1
def test_h1_aufzaehlung_hat_vier_loesungen(h1):
    assert Z.alldifferent_loesungen(h1) == [(1, 2, 3), (2, 1, 3), (3, 1, 2), (3, 2, 1)]
    assert [l for l in Z.alldifferent_loesungen(h1) if l[0] != 3] == [(1, 2, 3), (2, 1, 3)]


def test_h1_schritte_und_erklaerungsklauseln(h1):
    ev = A.hall_schritte(h1, [(0, 3)])
    assert [e["art"] for e in ev] == ["start", "entscheidung", "streichung", "streichung", "fixpunkt"]
    assert ev[1]["doms"] == [[1, 2], [1, 2], [1, 2, 3]]
    s1, s2 = ev[2], ev[3]
    assert (s1["var"], s1["wert"], s1["menge"], s1["werte"]) == (2, 1, [0, 1], [1, 2])
    assert (s2["var"], s2["wert"], s2["menge"], s2["werte"]) == (2, 2, [0, 1], [1, 2])
    assert s1["klausel"] == [(2, 1, False), (0, 3, True)]          # x3 ≠ 1 ∨ x1 = 3
    assert s2["klausel"] == [(2, 2, False), (0, 3, True)]          # x3 ≠ 2 ∨ x1 = 3
    assert ev[-1]["doms"] == [[1, 2], [1, 2], [3]]
    assert A.klausel_text(s1["klausel"]) == "x3 ≠ 1 ∨ x1 = 3"


def test_h1_erklaerungen_gelten_in_allen_loesungen_und_die_zu_starke_nicht(h1):
    loesungen = Z.alldifferent_loesungen(h1)
    for klausel in ([(2, 1, False), (0, 3, True)], [(2, 2, False), (0, 3, True)]):
        assert all(any((l[i] == w) == pos for i, w, pos in klausel) for l in loesungen)
    zu_stark = [(2, 1, False)]                                      # „x3 ≠ 1“: verletzt von (3, 2, 1)
    verletzt = [l for l in loesungen if not any((l[i] == w) == pos for i, w, pos in zu_stark)]
    assert verletzt == [(3, 2, 1)]


def test_h1_pruefung_mit_dem_kern_cdcl(h1):
    kod = K.kodiere_alldifferent(h1)
    ev = A.hall_schritte(h1, [(0, 3)])
    import lcg_evaluation as E

    for s in ev:
        if s["art"] == "streichung":
            p = A.pruefe_klausel(kod.n_var, kod.klauseln, E.klausel_literale(kod, s["klausel"]))
            assert p.urteil == "gueltig" and p.gegenbeispiel is None
    stark = A.pruefe_klausel(kod.n_var, kod.klauseln, E.klausel_literale(kod, [(2, 1, False)]))
    assert stark.urteil == "ungueltig"
    modell = stark.gegenbeispiel                                     # ein Modell der CNF, das x3 = 1 hat: genau (3, 2, 1)
    belegung = tuple(next(w for (i2, w), v in kod.var.items() if i2 == i and modell[v]) for i in range(3))
    assert belegung == (3, 2, 1)


def test_hall_fehlschlag_ohne_aussenwerte_gibt_die_leere_klausel():
    # x1, x2, x3 ∈ {1, 2}: drei Variablen auf zwei Werte. Matching scheitert an x3, S = alle drei, V = {1, 2}, D0(u) ∖ V ist überall leer: leere Klausel.
    a = A.hall_analyse([{1, 2}, {1, 2}, {1, 2}])
    assert a == ("fehl", [0, 1, 2], [1, 2])
    assert A.erklaerungsklausel([{1, 2}] * 3, None, None, [0, 1, 2], {1, 2}) == []
    assert A.klausel_text([]) == "(leer: Widerspruch)"


def test_hall_streichung_mit_aussenwerten_und_ohne():
    # x1, x2 ∈ {1, 2}; x3 ∈ {1, 2, 5}: Hall-Menge {x1, x2}, Streichungen (x3, 1) und (x3, 2) mit der Einheitsklausel „x3 ≠ w“ (alle Werte von x1, x2 liegen in V)
    ok, st = A.hall_analyse([{1, 2}, {1, 2}, {1, 2, 5}])
    assert ok == "ok" and [(x, w) for x, w, _, _ in st] == [(2, 1), (2, 2)]
    assert A.erklaerungsklausel([{1, 2}, {1, 2}, {1, 2, 5}], 2, 1, [0, 1], {1, 2}) == [(2, 1, False)]
    # Gruppe ohne Hall-Menge: keine Streichung, keine Klausel
    assert A.hall_analyse([{1, 2, 3}, {1, 2, 3}, {1, 2, 3}]) == ("ok", [])
    # x1 ∈ {1,3}, x2 ∈ {1,3}, x3 ∈ {1,2,3}, x4 ∈ {2,3,4}: genau (x3,1), (x3,3), (x4,2), (x4,3) fallen (die Lösungen haben x3 = 2, x4 = 4)
    ok, st = A.hall_analyse([{1, 3}, {1, 3}, {1, 2, 3}, {2, 3, 4}])
    assert ok == "ok" and sorted((x, w) for x, w, _, _ in st) == [(2, 1), (2, 3), (3, 2), (3, 3)]
    assert Z.alldifferent_loesungen([[1, 3], [1, 3], [1, 2, 3], [2, 3, 4]]) == [(1, 3, 2, 4), (3, 1, 2, 4)]


# ---------------------------------------------------------------------------------------------------------------------------------------------------- H2
@pytest.mark.parametrize("H,anzahl", [(2, 0), (3, 1), (4, 7), (5, 26)])
def test_h2_aufzaehlung(h2_jobs, H, anzahl):
    assert len(Z.jobshop_plaene(h2_jobs, H)) == anzahl


def test_h2_optimum_plan_und_reihenfolgen(h2_jobs):
    assert Z.jobshop_plaene(h2_jobs, 3) == [(0, 2, 0, 2)]
    assert Z.optimum_aufzaehlung(h2_jobs) == 3
    plaene = Z.jobshop_plaene(h2_jobs, 4)
    assert all(p[0] + 2 <= p[3] for p in plaene)                     # a vor d
    assert all(p[2] + 2 <= p[1] for p in plaene)                     # c vor b
    assert all(plan_ok(h2_jobs, p, 4) for p in plaene)
    # Auch bei H = 5 gelten beide Reihenfolgen in allen 26 Plänen (d vor a bräuchte s_a ≥ 3, also s_b ≥ 5 und Ende 6 > 5; b vor c bräuchte s_c ≥ 3, s_d ≥ 5, Ende 6 > 5),
    # erst bei H = 6 gibt es Pläne mit „d vor a“.
    fuenf = Z.jobshop_plaene(h2_jobs, 5)
    assert all(p[0] + 2 <= p[3] and p[2] + 2 <= p[1] for p in fuenf)
    sechs = Z.jobshop_plaene(h2_jobs, 6)
    assert any(p[3] + 1 <= p[0] for p in sechs)


def test_h2_fenster_bei_horizont_4(h2_jobs):
    est, lst, d, mc, ketten = K.fenster(h2_jobs, 4, True)
    assert est == [0, 2, 0, 2] and lst == [1, 3, 1, 3] and d == [2, 1, 2, 1] and mc == [0, 1, 1, 0] and ketten == [(0, 1), (2, 3)]
    # Handargument: „d vor a“ ⇒ est_a ≥ est_d + d_d = 3 > lst_a = 1 (Fenster leer); „b vor c“ ⇒ est_c ≥ est_b + d_b = 3 > lst_c = 1.
    # Ohne den Schwanz des Auftrags (lst_b = 3) wie im Handbeispiel: est_a ≥ 3 ⇒ est_b ≥ 3 + 2 = 5 > 3, und est_c ≥ 3 ⇒ est_d ≥ 3 + 2 = 5 > 3.
    assert est[3] + d[3] > lst[0] and est[1] + d[1] > lst[2]
    assert est[3] + d[3] + d[0] > lst[1] and est[1] + d[1] + d[2] > lst[3]


# ---------------------------------------------------------------------------------------------------------------------------------------------------- H3
@pytest.mark.parametrize("H,nv,ncl,modelle", [(2, 4, 9, 0), (3, 8, 18, 1), (4, 12, 28, 7), (5, 16, 38, 26)])
def test_h3_order_kodierung_zahlen_und_modelle(h2_jobs, H, nv, ncl, modelle):
    kod = K.kodiere_jobshop(h2_jobs, H, schranken=False)
    assert (kod.n_var, len(kod.klauseln)) == (nv, ncl)
    assert zaehle_modelle(kod.n_var, kod.klauseln) == modelle == len(Z.jobshop_plaene(h2_jobs, H))


def test_h3_modelle_sind_genau_die_plaene(h2_jobs):
    kod = K.kodiere_jobshop(h2_jobs, 4, schranken=False)
    plaene = set()
    from itertools import product

    for bits in product([False, True], repeat=kod.n_var):
        if all(any((bits[abs(l) - 1] if l > 0 else not bits[abs(l) - 1]) for l in c) for c in kod.klauseln):
            plaene.add(tuple(K.plan_aus_modell(kod, {v + 1: b for v, b in enumerate(bits)})))
    assert plaene == set(Z.jobshop_plaene(h2_jobs, 4))


@pytest.mark.parametrize("H", [2, 3, 4, 5])
def test_kodierung_mit_schranken_hat_dieselben_modelle(h2_jobs, H):
    kod = K.kodiere_jobshop(h2_jobs, H, schranken=True)
    assert (0 if kod.leer else zaehle_modelle(kod.n_var, kod.klauseln)) == len(Z.jobshop_plaene(h2_jobs, H))


def test_kodierung_mit_schranken_ist_kleiner_und_legt_die_wurzel_fest(h2_jobs):
    voll = K.kodiere_jobshop(h2_jobs, 4, schranken=False)
    eng = K.kodiere_jobshop(h2_jobs, 4, schranken=True)
    assert (eng.n_var, len(eng.klauseln)) == (6, 8) and eng.n_var < voll.n_var and len(eng.klauseln) < len(voll.klauseln)
    # Von Hand: Pflicht „a vor d“ (y_ad = 5 wahr) und „c vor b“ (y_bc = 6 falsch) schon an der Wurzel
    import lcg_evaluation as E

    assert eng.paar == {(0, 3): 5, (1, 2): 6}
    assert set(E.wurzel_literale(eng.n_var, eng.klauseln)) == {5, -6}


def test_kodierung_namen(h2_jobs):
    kod = K.kodiere_jobshop(h2_jobs, 4, schranken=False)
    nm = S.op_name_h2
    assert kod.name(kod.paar[(0, 3)], nm) == "a vor d" and kod.literal_text(-kod.paar[(0, 3)], nm) == "d vor a"
    assert kod.name(kod.var[(1, 2)], nm) == "[s_b ≤ 2]" and kod.literal_text(-kod.var[(1, 2)], nm) == "nicht [s_b ≤ 2]"


# ------------------------------------------------------------------------------------------------------------------------------------------ Suche und Hall
@pytest.mark.parametrize("h,konflikte", [(3, 7), (4, 28), (5, 159), (6, 1004)])
def test_schubfach_kern_cdcl_und_hall(h, konflikte):
    """Kern-Handwerte aus kern/README.md (Schubfach h = 4 / 5 / 6: 28 / 159 / 1 004; h = 3: 7); mit Hall-Erklärung 0 Konflikte der Suche und ein Fehlschlag des Propagators."""
    inst = I.pigeonhole(h)
    kl = [list(k) for k in inst.klauseln]
    assert solve(inst.n, kl).stat["konflikte"] == konflikte
    e, s = A.loese_mit_hall(inst.n, kl, [K.schubfach_gruppe(h)], protokoll=True)
    assert e.antwort is False and e.stat["konflikte"] == 0 and s.hall_fehlschlaege == 1 and s.hall_streichungen == 0
    assert len(s.protokoll) == 1 and s.protokoll[0].klausel == () and s.protokoll[0].art == "fehlschlag" and len(s.protokoll[0].menge) == h + 1


def test_hall_loeser_findet_das_modell_einer_erfuellbaren_gruppe(h1):
    kod = K.kodiere_alldifferent(h1)
    e, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen)
    assert e.antwort is True
    belegung = tuple(next(w for (i2, w), v in kod.var.items() if i2 == i and e.modell[v]) for i in range(3))
    assert belegung in Z.alldifferent_loesungen(h1)


def test_hall_loeser_entscheidung_x1_ungleich_3_legt_x3_fest(h1):
    kod = K.kodiere_alldifferent(h1)
    e, s = A.loese_mit_hall(kod.n_var, kod.klauseln + [[-kod.var[(0, 3)]]], kod.gruppen, protokoll=True)
    assert e.antwort is True
    assert e.modell[kod.var[(2, 3)]] is True
    assert s.hall_streichungen >= 2 and {(x.variable, x.wert) for x in s.protokoll if x.art == "streichung"} >= {(2, 1), (2, 2)}


def test_suche_alle_vier_varianten_geben_dieselbe_antwort(h2_jobs):
    kod = K.kodiere_jobshop(h2_jobs, 2, schranken=False)
    assert kod.leer
    for lernen in (False, True):
        for reihenfolge in ("statisch", "gewichtet"):
            e, _ = A.suche(kod.n_var, kod.klauseln, lernen=lernen, reihenfolge=reihenfolge, entscheidungs_vars=kod.entscheidungs_vars)
            assert e.antwort is False and e.stat["konflikte"] == 0
    kod = K.kodiere_jobshop(h2_jobs, 3, schranken=False)
    for lernen in (False, True):
        e, _ = A.suche(kod.n_var, kod.klauseln, lernen=lernen, entscheidungs_vars=kod.entscheidungs_vars)
        assert e.antwort is True and K.plan_aus_modell(kod, e.modell) == [0, 2, 0, 2]


def test_suche_nur_entscheidungsvariablen_werden_entschieden(h2_jobs):
    # Bei H = 4 und 5 legt die Wurzel beide Reihenfolgen fest; erst bei H = 6 sind die Paarvariablen offen und werden zuerst entschieden.
    kod = K.kodiere_jobshop(h2_jobs, 6, schranken=False)
    s = A.Suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, trace=True)
    e = s.loese()
    assert e.antwort is True
    erste = [ev for ev in e.spur if ev[0] == "entscheide"]
    assert erste and abs(erste[0][1]) in set(kod.entscheidungs_vars)
    assert plan_ok(h2_jobs, K.plan_aus_modell(kod, e.modell), 6)


def test_suche_ungueltige_reihenfolge_wird_abgelehnt():
    with pytest.raises(ValueError):
        A.Suche(2, [[1, 2]], reihenfolge="zufall")


def test_pruefe_klausel_budget_und_urteile():
    kl = [[1, 2], [-1, 2], [1, -2], [-1, -2]]                         # unerfüllbar: jede Klausel folgt
    assert A.pruefe_klausel(2, kl, [1]).urteil == "gueltig"
    kl2 = [[1, 2]]
    p = A.pruefe_klausel(2, kl2, [1])                                 # nicht gefolgert: x1 = falsch, x2 = wahr erfüllt die CNF
    assert p.urteil == "ungueltig" and p.gegenbeispiel == {1: False, 2: True}
    inst = I.pigeonhole(7)
    q = A.pruefe_klausel(inst.n, [list(k) for k in inst.klauseln], [], budget=5)            # die leere Klausel folgt (unerfüllbar), aber nicht in 5 Konflikten
    assert q.urteil == "unentschieden" and q.budget == 5
