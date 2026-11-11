"""Orakel-Tests (ORACLE-PLAYBOOK §2/§5, DEMO-PLAYBOOK §12): unabhängige Rechenwege für die Kernroutinen.

* `hall_analyse` gegen die **Aufzählung** aller AllDifferent-Lösungen: die Streichungen sind genau die Werte, die in keiner Lösung vorkommen (Bereichskonsistenz), und „fehl“ heißt genau „keine Lösung“.
* **Jede erzeugte Erklärungsklausel einzeln** (Familien: Zufalls-Domänen, Rotationsplan): gilt in allen Lösungen (Aufzählung), und CNF plus verneinte Klausel ist unerfüllbar nach dem Kern-CDCL und nach OR-Tools CP-SAT.
* Antwort und Optimum der Job-Shop-CNF gegen Aufzählung (2 × 2, 3 × 2) und gegen CP-SAT; jedes Modell, in einen Plan zurückübersetzt, besteht den eigenen Plan-Prüfer.
Die große Stichprobe (80 Zufalls-Domänen-Instanzen, 36 Rotationspläne, 12 gelernte Klauseln je Instanz) läuft im Messskript `tools/messung_messreihen.py`, hier steht die schnelle Fassung."""

import pytest
from orakel import alldiff_loesungen, cpsat_jobshop_optimum, cpsat_klausel_gueltig, erlaubte_werte, plan_ok

import lcg_algorithm as A
import lcg_aufzaehlung as Z
import lcg_evaluation as E
import lcg_kodierung as K
import lcg_scenario as S
from lcg_cdcl import solve
from lcg_jobshop import as_instance
from lcg_rng import SplitMix64


def zufalls_domaenen(rng, p=None):
    p = p or 4 + rng.below(4)                    # 4 bis 7 Variablen
    wmax = p + rng.below(2)                      # Werte 1..p oder 1..p+1
    doms = []
    for _ in range(p):
        d = {w for w in range(1, wmax + 1) if rng.below(100) < 58}
        doms.append(d or {1 + rng.below(wmax)})
    return doms


def klausel_gilt_in_allen(klausel, loesungen):
    return all(any((l[i] == w) == pos for i, w, pos in klausel) for l in loesungen)


# ------------------------------------------------------------------------------------------------------------------------------- Hall-Analyse
def test_hall_analyse_gleich_bereichskonsistenz_per_aufzaehlung():
    rng = SplitMix64(11)
    mit_fehl = mit_streichung = 0
    for _ in range(600):
        doms = zufalls_domaenen(rng)
        erlaubt = erlaubte_werte(doms)
        a = A.hall_analyse([set(d) for d in doms])
        if erlaubt is None:
            assert a[0] == "fehl"
            _, S_, V = a
            assert set(V) == set().union(*[doms[u] for u in S_]) and len(V) < len(S_)       # Hall-Verletzung
            mit_fehl += 1
            continue
        assert a[0] == "ok"
        gestrichen = {(x, w) for x, w, _, _ in a[1]}
        erwartet = {(i, w) for i in range(len(doms)) for w in doms[i] if w not in erlaubt[i]}
        assert gestrichen == erwartet, doms
        for x, w, R, V in a[1]:                                                       # jede Streichung ist eine Hall-Menge
            assert set(V) == set().union(*[doms[u] for u in R]) and len(V) == len(R) and x not in R and w in V
        mit_streichung += len(gestrichen)
    assert mit_fehl >= 30 and mit_streichung >= 200          # die Stichprobe trifft beide Zweige


def test_jede_erklaerungsklausel_gilt_in_allen_loesungen():
    """Hall-Erklärungen schneiden nie eine Lösung ab: Klauseln aus `hall_schritte` mit zufälligen Entscheidungen, gegen die Aufzählung der Lösungen der Anfangsdomänen."""
    rng = SplitMix64(5)
    klauseln = 0
    for _ in range(300):
        doms = zufalls_domaenen(rng)
        loesungen = alldiff_loesungen(doms)
        entsch = [(rng.below(len(doms)), 1 + rng.below(len(doms) + 1)) for _ in range(rng.below(3))]
        entsch = [(x, w) for x, w in entsch if w in doms[x] and len(doms[x]) > 1]
        for e in A.hall_schritte([set(d) for d in doms], entsch):
            if e["art"] in ("streichung", "fehlschlag"):
                # Die Erklärung gilt unter den Anfangsdomänen, nicht erst nach der Entscheidung: sie darf keine Lösung dieser Anfangsdomänen verletzen.
                assert klausel_gilt_in_allen(e["klausel"], loesungen), (doms, entsch, e)
                klauseln += 1
    assert klauseln >= 200


def test_zu_starke_klausel_wird_von_der_aufzaehlung_und_der_pruefung_gefangen(h1):
    loesungen = alldiff_loesungen(h1)
    stark = [(2, 1, False)]
    assert not klausel_gilt_in_allen(stark, loesungen)
    kod = K.kodiere_alldifferent(h1)
    assert A.pruefe_klausel(kod.n_var, kod.klauseln, E.klausel_literale(kod, stark)).urteil == "ungueltig"
    assert not cpsat_klausel_gueltig(kod.n_var, kod.klauseln, E.klausel_literale(kod, stark))


# ----------------------------------------------------------------------------------------------------------- CDCL mit Hall-Propagator: Einzelprüfung
def _klausel_als_tripel(kod, lits):
    inv = {v: k for k, v in kod.var.items()}
    return [(inv[abs(l)][0], inv[abs(l)][1], l > 0) for l in lits]


def test_hall_loeser_antwort_modell_und_jede_klausel_zufalls_domaenen():
    rng = SplitMix64(23)
    geprueft = unsat = sat = 0
    stichprobe = []
    for _ in range(240):
        doms = zufalls_domaenen(rng)
        kod = K.kodiere_alldifferent([sorted(d) for d in doms])
        loesungen = alldiff_loesungen(doms)
        e, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen, protokoll=True, budget=5000)
        assert e.antwort is (len(loesungen) > 0)
        if e.antwort:
            sat += 1
            belegung = tuple(next(w for (i2, w), v in kod.var.items() if i2 == i and e.modell[v]) for i in range(len(doms)))
            assert belegung in loesungen
        else:
            unsat += 1
        for x in s.protokoll:
            tripel = _klausel_als_tripel(kod, x.klausel)
            assert klausel_gilt_in_allen(tripel, loesungen)                          # Aufzählung (nur AllDifferent-Lösungen)
            geprueft += 1
            if len(stichprobe) < 40:
                stichprobe.append((kod, list(x.klausel)))
    assert geprueft >= 200 and sat >= 30 and unsat >= 10
    for kod, klausel in stichprobe:                                                  # Kern-CDCL und CP-SAT als unabhängige Entscheider
        assert A.pruefe_klausel(kod.n_var, kod.klauseln, klausel, 5000).urteil == "gueltig"
        assert cpsat_klausel_gueltig(kod.n_var, kod.klauseln, klausel)


def test_hall_loeser_rotationsplan_klauseln_gueltig():
    """Rotationsplan 8 × 8 mit 70 % Lücken: jede erzeugte Klausel (mindestens 150) nach dem Kern-CDCL gültig, eine Stichprobe von 40 zusätzlich nach CP-SAT; Modell zeilen- und spaltenweise verschieden."""
    n_kern = n_cpsat = 0
    for seed in range(6):
        vor = S.rotationsplan(8, 70, seed)
        doms, gruppen = K.rotationsplan_domaenen(8, vor)
        kod = K.kodiere_alldifferent(doms, gruppen)
        e, s = A.loese_mit_hall(kod.n_var, kod.klauseln, kod.gruppen, protokoll=True, budget=2000)
        assert e.antwort is True                                                      # nach Konstruktion erfüllbar
        for x in s.protokoll:
            assert A.pruefe_klausel(kod.n_var, kod.klauseln, list(x.klausel), 5000).urteil == "gueltig"
            n_kern += 1
        for x in list(s.protokoll)[:7]:
            assert cpsat_klausel_gueltig(kod.n_var, kod.klauseln, list(x.klausel))
            n_cpsat += 1
        wert = {i: w for (i, w), v in kod.var.items() if e.modell[v]}
        pruef = {(r, c): wert[r * 8 + c] for r in range(8) for c in range(8)}
        for r in range(8):
            assert len({pruef[(r, c)] for c in range(8)}) == 8 and len({pruef[(c, r)] for c in range(8)}) == 8     # Zeilen und Spalten verschieden
        assert all(pruef[z] == w for z, w in vor.items())                                                          # Vorbelegung eingehalten
    assert n_kern >= 150 and n_cpsat >= 40


def test_gelernte_klauseln_folgen_aus_der_cnf(h2_jobs):
    """Eigenschaft: jede vom Job-Shop-CDCL gelernte Klausel ist eine Folgerung der CNF (Kern-CDCL und CP-SAT)."""
    n = 0
    for seed in (2, 4, 5, 6):
        inst = S.jobshop_instanz(5, seed)
        opt, _ = S.optimum(inst)
        kod = K.kodiere_jobshop([list(j) for j in inst.jobs], opt - 1)
        e = A.Suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, lernen=True, proof=True).loese(conflict_budget=200)
        gelernt = [k for art, k in e.beweis if art == "a" and k][:8]
        for k in gelernt:
            assert A.pruefe_klausel(kod.n_var, kod.klauseln, k, 5000).urteil == "gueltig"
            assert cpsat_klausel_gueltig(kod.n_var, kod.klauseln, k)
            n += 1
    assert n >= 15


# ------------------------------------------------------------------------------------------------------------------------- Job Shop: Antwort und Optimum
def zufalls_jobshop(rng, nj, nm, dmax=3):
    jobs = []
    for _ in range(nj):
        maschinen = list(range(nm))
        rng.shuffle(maschinen)
        jobs.append([(m, 1 + rng.below(dmax)) for m in maschinen])
    return jobs


@pytest.mark.parametrize("nj,nm,anzahl", [(2, 2, 25), (3, 2, 12)])
def test_antwort_und_optimum_gegen_aufzaehlung(nj, nm, anzahl):
    rng = SplitMix64(100 + nj)
    for _ in range(anzahl):
        jobs = zufalls_jobshop(rng, nj, nm)
        opt = Z.optimum_aufzaehlung(jobs)
        ketten = max(sum(d for _, d in j) for j in jobs)
        for H in range(max(1, ketten - 1), opt + 2):
            plaene = Z.jobshop_plaene(jobs, H)
            for schranken in (False, True):
                kod = K.kodiere_jobshop(jobs, H, schranken=schranken)
                for lernen in (False, True):
                    for reihenfolge in ("statisch", "gewichtet"):
                        e, _ = A.suche(kod.n_var, kod.klauseln, lernen=lernen, reihenfolge=reihenfolge, entscheidungs_vars=kod.entscheidungs_vars)
                        assert e.antwort is (len(plaene) > 0), (jobs, H, schranken, lernen, reihenfolge)
                        if e.antwort:
                            plan = K.plan_aus_modell(kod, e.modell)
                            assert plan_ok(jobs, plan, H)
        assert S.optimum(as_instance(jobs))[0] == opt          # das Mini-CP (Stufe 2) findet dasselbe Optimum


@pytest.mark.parametrize("groesse,seeds", [(3, range(6)), (4, range(8)), (5, range(5))])
def test_optimum_und_antworten_gegen_cpsat(groesse, seeds):
    for seed in seeds:
        inst = S.jobshop_instanz(groesse, seed)
        jobs = [list(j) for j in inst.jobs]
        opt, bewiesen = S.optimum(inst)
        assert bewiesen and opt == cpsat_jobshop_optimum(jobs)
        for H, erwartet in ((opt, True), (opt - 1, False)):
            kod = K.kodiere_jobshop(jobs, H)
            for lernen in (False, True):
                e, _ = A.suche(kod.n_var, kod.klauseln, lernen=lernen, entscheidungs_vars=kod.entscheidungs_vars, budget=20000)
                assert e.antwort is erwartet
                if erwartet:
                    assert plan_ok(jobs, K.plan_aus_modell(kod, e.modell), H)
            assert solve(kod.n_var, [list(k) for k in kod.klauseln]).antwort is erwartet        # auch der Standard-CDCL


def test_die_vier_varianten_haben_dieselbe_antwort_und_unterscheiden_sich_in_den_konflikten():
    """Antwort unabhängig von Lernen aus/an und Reihenfolge; Zweig-Test: auf mindestens einer Instanz weicht jede Variante von ihrer Nachbarvariante ab (keine Spalte mit lauter gleichen Werten)."""
    zeilen = []
    for seed in range(12):
        inst = S.jobshop_instanz(6, seed)
        zeilen.append(E.jobshop_lauf(inst, 5000, 20000, mit_standard=False))
    for z in zeilen:
        assert set(z["antworten"].values()) == {False}
    for a, b in (("ohne_stat", "ohne_gew"), ("ohne_stat", "mit_stat"), ("ohne_gew", "mit_gew"), ("mit_stat", "mit_gew")):
        assert any(z[a] != z[b] for z in zeilen), (a, b)
    for v in E.VARIANTEN:
        assert len({z[v] for z in zeilen}) > 1
