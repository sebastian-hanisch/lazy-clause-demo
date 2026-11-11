"""Jede Zahl der README (Abschnitt „Befunde“ und „Befunde und Korrekturen“) wird hier aus `lcg_messreihen.json` beziehungsweise aus den Handbeispielen nachgerechnet,
und die Zahl muss im README-Text stehen (formatiert wie dort). Zahl → Test steht in der README-Tabelle."""

from pathlib import Path

import pytest

import lcg_constants as C
import lcg_evaluation as E

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
GR = (4, 5, 6, 7, 8)


@pytest.fixture(scope="module")
def zeilen():
    return E.groessen_zeilen(E.lade_messreihen())


@pytest.fixture(scope="module")
def daten():
    return E.lade_messreihen()


def zt(x):
    """Zahl wie in der README: Tausender mit Leerzeichen, Dezimalkomma."""
    s = f"{x:,.1f}".replace(",", " ").replace(".", ",") if isinstance(x, float) and not x.is_integer() else f"{int(x):,}".replace(",", " ")
    return s


def med(z, k):
    return z[k]["median"]


def test_claim_lernen_median_je_groesse(zeilen):
    assert [z["groesse"] for z in zeilen] == list(GR) and all(z["n"] == 12 for z in zeilen)
    ohne = [med(z, "ohne_stat") for z in zeilen]
    mit = [med(z, "mit_stat") for z in zeilen]
    assert ohne == [1, 4, 53, 198, 4085.5] and mit == [1, 3, 19, 12, 353.5]
    faktoren = [E.verhaeltnis(a, b) for a, b in zip(ohne, mit)]
    assert [round(f, 1) for f in faktoren] == [1.0, 1.3, 2.8, 16.5, 11.6]
    assert [z["ohne_stat"]["abbrueche"] for z in zeilen] == [0, 0, 0, 1, 6] and [z["mit_stat"]["abbrueche"] for z in zeilen] == [0, 0, 0, 0, 1]
    assert [f >= C.GLEICHAUF_FAKTOR for f in faktoren] == [False, False, True, True, True]
    assert sum(1 for a, b in zip(faktoren, faktoren[1:]) if b > a) == 3
    for s in ("4 → 3", "53 → 19", "198 → 12", "4 085,5 → 353,5", "1,0 / 1,3 / 2,8 / 16,5 / 11,6", "0 / 0 / 0 / 1 / 6"):
        assert s in README, s
    assert "81 → 13,5" in README and "1 350 → 75" in README and "270,5 → 48" in README         # Zahlen der Vormessung, wie in ERGEBNIS-lg.md


def test_claim_lernen_je_instanz(daten):
    besser = []
    for g in GR:
        inst = daten["jobshop"][str(g)]
        w = [(C.MESS_BUDGET if i["ohne_stat"] is None else i["ohne_stat"], C.MESS_BUDGET if i["mit_stat"] is None else i["mit_stat"]) for i in inst]
        assert all(m <= o for o, m in w)
        besser.append(sum(1 for o, m in w if m < o))
    assert besser == [2, 6, 10, 10, 11]
    assert "2 / 6 / 10 / 10 / 11 von 12" in README and "60 Instanzen" in README


def test_claim_leichte_instanzen_und_klauselzahl(daten, zeilen):
    leicht = [sum(1 for i in daten["jobshop"][str(g)] if all(i[v] is not None and i[v] <= 1 for v in E.VARIANTEN)) for g in GR]
    assert leicht == [8, 5, 1, 0, 0]
    assert [z["klauseln"] for z in zeilen] == [744.5, 1804.0, 4436.5, 7055.5, 12350.5]
    assert "8 / 5 / 1 / 0 / 0 von 12" in README and "744,5 / 1 804 / 4 436,5 / 7 055,5 / 12 350,5" in README


def test_claim_gewichtung_holt_nicht_alles_auf(zeilen):
    gew = [round(E.verhaeltnis(med(z, "ohne_stat"), med(z, "ohne_gew")), 1) for z in zeilen]
    lern = [round(E.verhaeltnis(med(z, "ohne_stat"), med(z, "mit_stat")), 1) for z in zeilen]
    assert gew == [1.0, 1.1, 1.8, 2.2, 3.5] and lern == [1.0, 1.3, 2.8, 16.5, 11.6]
    nahe = [E.verhaeltnis(med(z, "ohne_gew"), med(z, "mit_stat")) < C.GLEICHAUF_FAKTOR for z in zeilen]
    assert nahe == [True, True, False, False, False]
    assert "1,0 / 1,1 / 1,8 / 2,2 / 3,5" in README and "in 2 von 5 Größen" in README


def test_claim_lernen_gewichtet_gegen_statisch(zeilen):
    assert [med(z, "mit_gew") for z in zeilen] == [1, 3, 13, 13, 187]
    assert [med(z, "mit_stat") for z in zeilen] == [1, 3, 19, 12, 353.5]
    assert "1 / 3 / 13 / 13 / 187 gegen statisch 1 / 3 / 19 / 12 / 353,5" in README
    assert "13 gegen 19 (6 × 6), 13 gegen 12 (7 × 7) und 187 gegen 353,5 (8 × 8)" in README
    assert 0.5 < 187 / 353.5 < 0.55


def test_claim_mini_cp_gegen_lernen(zeilen):
    assert [med(z, "mini2") for z in zeilen] == [1, 1, 2, 3, 9] and [med(z, "mini1") for z in zeilen] == [1, 3, 9, 12, 64]
    kind, text = E.verdict_zugeschnitten(zeilen)
    assert "Mini-CP in 4 von 5 Größen, das Lernen in 0, gleichauf (Abstand unter dem Faktor 1,5) sind 1" in text
    assert "1 / 1 / 2 / 3 / 9" in README and "1 / 3 / 9 / 12 / 64" in README and "4 von 5 Größen" in README
    assert all(med(z, "mit_stat") >= C.GLEICHAUF_FAKTOR * med(z, "mini2") for z in zeilen[1:])


def test_claim_standard_cdcl(zeilen):
    assert [med(z, "standard") for z in zeilen] == [1, 2.5, 10.5, 11, 58.5]
    assert all(med(z, "standard") < med(z, "mit_stat") for z in zeilen[2:])
    assert "1 / 2,5 / 10,5 / 11 / 58,5" in README


def test_claim_cpsat_massstab(zeilen, daten):
    assert [med(z, "cpsat") for z in zeilen] == [0, 0, 0, 1.5, 6.5]
    assert daten["meta"]["ortools"] in README and "0 / 0 / 0 / 1,5 / 6,5" in README and "60 Instanzen, 0 Abweichungen" in README
    assert daten["meta"]["antwortfehler"] == 0 and sum(z["n"] for z in zeilen) == 60


def test_claim_schubfach(daten):
    zl = daten["schubfach"]
    ohne = [r["ohne"] for r in zl]
    assert ohne == [7, 28, 159, 1004, 4811, 27932]
    assert all(r["hall"] == 0 and r["hall_fehlschlaege"] == 1 for r in zl)
    assert [round(b / a, 1) for a, b in zip(ohne, ohne[1:])] == [4.0, 5.7, 6.3, 4.8, 5.8]
    assert "7 / 28 / 159 / 1 004 / 4 811 / 27 932" in README and "4,0 / 5,7 / 6,3 / 4,8 / 5,8" in README and "27 932 Konflikte" in README


def test_claim_pruefbilanz(daten):
    f = daten["pruefung"]
    assert [x["geprueft"] for x in f] == [216, 342, 6, 100]
    assert sum(x["geprueft"] for x in f) == 664 and sum(x["gueltig"] for x in f) == 663
    assert sum(x["ungueltig"] for x in f) == 0 and sum(x["unentschieden"] for x in f) == 1 and f[2]["unentschieden"] == 1
    assert "664 Klauseln in 4 Familien" in README and "663 gültig, 0 ungültig, 1 unentschieden" in README
    assert "Rotationsplan mit Lücken 216, Zufalls-Domänen 342, Schubfach 6" in README and "gelernte Klauseln des Job-Shop-CDCL 100" in README


def test_claim_abbrueche_8x8(zeilen):
    assert zeilen[-1]["ohne_stat"]["abbrueche"] == 6 and "6 der 12 Läufe" in README and "6 von 12 Läufen" in README


def test_claim_h1_h2_h3_zahlen_stehen_in_der_readme():
    import lcg_aufzaehlung as Z
    import lcg_kodierung as K
    import lcg_scenario as S

    assert len(Z.alldifferent_loesungen([list(d) for d in S.H1_DOMAENEN])) == 4
    jobs = [list(j) for j in S.H2_JOBS]
    assert [len(Z.jobshop_plaene(jobs, H)) for H in (2, 3, 4, 5)] == [0, 1, 7, 26]
    assert [(K.kodiere_jobshop(jobs, H, schranken=False).n_var, len(K.kodiere_jobshop(jobs, H, schranken=False).klauseln)) for H in (2, 3, 4, 5)] == [(4, 9), (8, 18), (12, 28), (16, 38)]
    for s in ("0 / 1 / 7 / 26", "4 / 8 / 12 / 16 Variablen, 9 / 18 / 28 / 38 Klauseln", "4 Lösungen", "x3 ≠ 1 ∨ x1 = 3"):
        assert s in README, s


def test_claim_h5_und_h6_reihenfolgen():
    import lcg_aufzaehlung as Z
    import lcg_scenario as S

    jobs = [list(j) for j in S.H2_JOBS]
    assert all(p[0] + 2 <= p[3] and p[2] + 2 <= p[1] for p in Z.jobshop_plaene(jobs, 5))
    assert any(p[3] + 1 <= p[0] for p in Z.jobshop_plaene(jobs, 6))
    assert "H = 5" in README and "H = 6" in README


def test_claim_readme_sagt_gleichauf_schwelle_und_messdaten(daten):
    assert "Faktor 1,5" in README and C.GLEICHAUF_FAKTOR == 1.5
    assert "Budget 5 000 Konflikte" in README and C.MESS_BUDGET == 5000 and "20 000 Knoten" in README and C.MESS_BUDGET_MINICP == 20000
    assert daten["meta"]["datum"] in README and daten["meta"]["seeds"] == list(range(12))


def test_readme_testzahl_und_pflichtabschnitte():
    for abschnitt in ("## Befunde und Korrekturen gegenüber dem Plan", "## Befunde (gemessen, keine Behauptungen)", "## Ehrliche Grenzen", "## Bewusst nicht umgesetzt", "## Verifikation"):
        assert abschnitt in README
    assert "trägt" not in README and "läuft lokal" not in README and "Saatwert" not in README
