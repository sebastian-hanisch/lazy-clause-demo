"""Die vorgerechnete Messreihe `lcg_messreihen.json` (Skript `tools/messung_messreihen.py`): Aufbau, innere Konsistenz und Stichproben-Nachrechnung.

Die Zähler sind ganzzahlig und deterministisch (SplitMix64-Instanzen, Kern-CDCL ohne Zufall): eine Stichprobe der Instanzen muss sich exakt reproduzieren."""

import pytest

import lcg_constants as C
import lcg_evaluation as E
import lcg_scenario as S


@pytest.fixture(scope="module")
def daten():
    return E.lade_messreihen()


def test_meta_nennt_skript_datum_budget_und_keine_abweichung_gegen_cpsat(daten):
    m = daten["meta"]
    assert m["skript"] == C.MESS_SKRIPT and m["budget_cnf"] == C.MESS_BUDGET and m["budget_minicp"] == C.MESS_BUDGET_MINICP
    assert m["seeds"] == list(C.MESS_SEEDS) and m["groessen"] == list(C.MESS_GROESSEN) and m["datum"] and m["ortools"]
    assert m["antwortfehler"] == 0 and m["fehler"] == []
    assert "vorgerechnet" in m["hinweis"] and "nicht live" in m["hinweis"]


def test_aufbau_je_groesse_zwoelf_instanzen_alle_felder(daten):
    assert sorted(int(g) for g in daten["jobshop"]) == list(C.MESS_GROESSEN)
    felder = set(E.VARIANTEN) | {"standard", "mini1", "mini2", "cpsat", "opt", "optimum_bewiesen", "variablen", "klauseln", "wurzel_leer", "seed"}
    for g, zeilen in daten["jobshop"].items():
        assert [z["seed"] for z in zeilen] == list(C.MESS_SEEDS)
        for z in zeilen:
            assert felder <= set(z), (g, z["seed"])
            assert z["optimum_bewiesen"] is True
            for v in E.VARIANTEN + ("standard",):
                assert z[v] is None or 0 <= z[v] <= C.MESS_BUDGET                  # None = Abbruch am Budget
            for v in ("mini1", "mini2"):
                assert z[v] is None or 0 <= z[v] <= C.MESS_BUDGET_MINICP


def test_ein_abbruch_hat_das_budget_als_wert_in_der_verteilung(daten):
    zeilen = E.groessen_zeilen(daten)
    acht = zeilen[-1]
    assert acht["groesse"] == 8 and acht["ohne_stat"]["abbrueche"] >= 1 and acht["ohne_stat"]["max"] == C.MESS_BUDGET


def test_lernen_ist_nie_schlechter_als_nichtlernen_je_instanz(daten):
    """Gleiche Wertregel und Reihenfolge: auf keiner der 60 Instanzen braucht „mit Lernen, statisch“ mehr Konflikte als „ohne“ (Abbruch zählt mit dem Budget)."""
    for g, zeilen in daten["jobshop"].items():
        for z in zeilen:
            ohne = C.MESS_BUDGET if z["ohne_stat"] is None else z["ohne_stat"]
            mit = C.MESS_BUDGET if z["mit_stat"] is None else z["mit_stat"]
            assert mit <= ohne, (g, z["seed"])


def test_stichprobe_laesst_sich_exakt_nachrechnen(daten):
    for g, seeds in ((4, range(12)), (5, range(12)), (6, range(5))):
        for seed in seeds:
            z = daten["jobshop"][str(g)][seed]
            neu = E.jobshop_lauf(S.jobshop_instanz(g, seed), C.MESS_BUDGET, C.MESS_BUDGET_MINICP)
            for k in ("opt", "klauseln", "variablen", "wurzel_leer") + E.VARIANTEN + ("standard", "mini1", "mini2"):
                assert neu[k] == z[k], (g, seed, k)


def test_schubfach_zeilen_stimmen_mit_den_bekannten_werten(daten):
    """Konflikte des Kern-CDCL auf dem Schubfach: 7 / 28 / 159 / 1 004 (Kern-Handwerte) und 4 811 / 27 932 (Phase 0, `out_v1a.txt` der Planung); mit Hall-Erklärung nie ein Konflikt der Suche."""
    zeilen = {r["h"]: r for r in daten["schubfach"]}
    assert sorted(zeilen) == [3, 4, 5, 6, 7, 8]
    assert [zeilen[h]["ohne"] for h in range(3, 9)] == [7, 28, 159, 1004, 4811, 27932]
    for r in zeilen.values():
        assert r["hall"] == 0 and r["hall_fehlschlaege"] == 1 and r["hall_antwort"] is False and r["ohne_antwort"] is False
        assert r["ohne_abgebrochen"] is False and r["variablen"] == r["h"] * (r["h"] + 1)


def test_pruefbilanz_keine_ungueltige_klausel_und_mindestens_200_je_hauptfamilie(daten):
    fam = {f["familie"].split(" (")[0]: f for f in daten["pruefung"]}
    assert set(fam) == {"Rotationsplan mit Lücken", "Zufalls-Domänen", "Schubfach h = 3 bis 8", "Gelernte Klauseln des Job-Shop-CDCL"}
    for f in daten["pruefung"]:
        assert f["ungueltig"] == 0 and f["geprueft"] == f["gueltig"] + f["ungueltig"] + f["unentschieden"], f["familie"]
    assert fam["Rotationsplan mit Lücken"]["geprueft"] >= 200 and fam["Zufalls-Domänen"]["geprueft"] >= 200
    assert sum(f["unentschieden"] for f in daten["pruefung"]) <= 1                                 # nur Schubfach h = 8 (Gegenprobe selbst über dem Budget)


def test_groessen_zeilen_median_von_hand():
    laeufe = [{"optimum_bewiesen": True, "wurzel_leer": False, "klauseln": 10 * (i + 1), "ohne_stat": w, "ohne_gew": w, "mit_stat": 1, "mit_gew": 1, "standard": 1, "mini1": 1, "mini2": 1, "cpsat": 0}
              for i, w in enumerate([3, None, 1, 5])]
    z = E.zeile_aus_laeufen(4, laeufe, 100, 1000)
    assert z["ohne_stat"] == {"n": 4, "median": 4.0, "p90": 100, "max": 100, "abbrueche": 1}        # sortiert 1, 3, 5, 100: Median (3 + 5) / 2
    assert z["klauseln"] == 25.0 and z["n"] == 4 and z["wurzel"] == 0
