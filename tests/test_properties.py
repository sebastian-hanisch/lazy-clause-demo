"""Eigenschaftstests: Invarianzen und Monotonie, die für jede Instanz gelten müssen."""

import pytest
from orakel import plan_ok

import lcg_algorithm as A
import lcg_instanzen as I
import lcg_kodierung as K
import lcg_scenario as S
from lcg_cdcl import solve
from lcg_jobshop import as_instance


@pytest.mark.parametrize("h", [3, 4, 5, 6])
def test_mit_erklaerung_hoechstens_so_viele_konflikte_wie_ohne(h):
    inst = I.pigeonhole(h)
    kl = [list(k) for k in inst.klauseln]
    ohne = solve(inst.n, kl).stat["konflikte"]
    e, _ = A.loese_mit_hall(inst.n, kl, [K.schubfach_gruppe(h)])
    assert e.antwort is False and e.stat["konflikte"] <= ohne and ohne > 0


def _antwort(jobs, H):
    kod = K.kodiere_jobshop(jobs, H)
    e, _ = A.suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, budget=20000)
    assert e.antwort is not None
    return e.antwort


@pytest.mark.parametrize("seed", range(5))
def test_dauern_mal_zwei_aendert_die_antworten_nicht(seed):
    """Alle Dauern mit demselben Faktor 2 malnehmen und den Horizont mit: das Optimum verdoppelt sich, und die Antwort bei „Optimum“ und „Optimum − 1“ bleibt dieselbe."""
    inst = S.jobshop_instanz(4, seed)
    jobs = [list(j) for j in inst.jobs]
    doppelt = [[(m, 2 * d) for m, d in j] for j in jobs]
    opt, _ = S.optimum(inst)
    opt2, _ = S.optimum(as_instance(doppelt))
    assert opt2 == 2 * opt
    assert _antwort(jobs, opt) is True and _antwort(doppelt, 2 * opt) is True
    assert _antwort(jobs, opt - 1) is False and _antwort(doppelt, 2 * opt - 1) is False


@pytest.mark.parametrize("seed", [1, 2, 4])
def test_antwort_ist_monoton_im_horizont(seed):
    inst = S.jobshop_instanz(5, seed)
    jobs = [list(j) for j in inst.jobs]
    opt, _ = S.optimum(inst)
    antworten = [_antwort(jobs, H) for H in range(opt - 3, opt + 3)]
    assert antworten == [False, False, False, True, True, True]


def test_reihenfolge_der_auftraege_aendert_das_optimum_nicht():
    for seed in range(6):
        inst = S.jobshop_instanz(5, seed)
        umgekehrt = as_instance(list(reversed(inst.jobs)))
        assert S.optimum(inst)[0] == S.optimum(umgekehrt)[0]


def test_dieselbe_eingabe_dieselben_konflikte():
    inst = S.jobshop_instanz(6, 4)
    kod = K.kodiere_jobshop([list(j) for j in inst.jobs], S.optimum(inst)[0] - 1)
    laeufe = [A.suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, reihenfolge="gewichtet", lernen=l)[0].stat["konflikte"] for l in (False, True, False, True)]
    assert laeufe[0] == laeufe[2] and laeufe[1] == laeufe[3]


def test_modell_jeder_erfuellbaren_instanz_ist_ein_gueltiger_plan():
    for seed in range(8):
        inst = S.jobshop_instanz(5, seed)
        jobs = [list(j) for j in inst.jobs]
        opt, _ = S.optimum(inst)
        for H in (opt, opt + 2):
            kod = K.kodiere_jobshop(jobs, H)
            e, _ = A.suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars)
            assert e.antwort is True and plan_ok(jobs, K.plan_aus_modell(kod, e.modell), H)


def test_kodierung_ist_deterministisch_und_ohne_doppelte_klauseln():
    inst = S.jobshop_instanz(5, 3)
    jobs = [list(j) for j in inst.jobs]
    a = K.kodiere_jobshop(jobs, 60)
    b = K.kodiere_jobshop(jobs, 60)
    assert a.klauseln == b.klauseln and a.n_var == b.n_var
    assert len({tuple(k) for k in a.klauseln}) == len(a.klauseln)
    assert all(len(set(abs(l) for l in k)) == len(k) for k in a.klauseln)          # keine Variable doppelt in einer Klausel
