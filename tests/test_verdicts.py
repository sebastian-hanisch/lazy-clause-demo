"""Verdikte (reine Funktionen in lcg_evaluation.py) an handgesetzten Werten: Schwellen und jede Zahl im Text."""

import pytest

import lcg_algorithm as A
import lcg_constants as C
import lcg_evaluation as E


def vt(median, maximum=None, abbrueche=0, n=12):
    return {"n": n, "median": float(median), "p90": maximum or median, "max": maximum or median, "abbrueche": abbrueche}


def zeile(g, ohne_stat, mit_stat, mini2=1, ohne_gew=None, mit_gew=None, ab_ohne=0, ab_mit=0):
    return {"groesse": g, "n": 12, "ohne_stat": vt(ohne_stat, abbrueche=ab_ohne), "mit_stat": vt(mit_stat, abbrueche=ab_mit), "ohne_gew": vt(ohne_gew or ohne_stat), "mit_gew": vt(mit_gew or mit_stat),
            "mini2": vt(mini2), "mini1": vt(mini2)}


def test_schwelle_gleichauf_steht_vor_dem_bau_fest():
    assert C.GLEICHAUF_FAKTOR == 1.5


def test_lernen_alle_groessen_ueber_der_schwelle_ist_success_mit_den_zahlen_im_text():
    z = [zeile(4, 30, 10), zeile(5, 100, 20), zeile(6, 400, 20)]
    kind, text = E.verdict_lernen(z, "statisch")
    assert kind == "success"
    assert "4 × 4: 30 → 10 (3,0-fach)" in text and "5 × 5: 100 → 20 (5,0-fach)" in text and "6 × 6: 400 → 20 (20,0-fach)" in text
    assert "mindestens 3,0-fach" in text and "in 2 von 2 Schritten" in text and "3 Größen" in text


def test_lernen_schwelle_genau_1_5_zaehlt_als_abstand_darunter_nicht():
    assert E.verdict_lernen([zeile(4, 15, 10)], "statisch")[0] == "success"               # genau 1,5
    kind, text = E.verdict_lernen([zeile(4, 14, 10)], "statisch")                        # 1,4
    assert kind == "warning" and "gleichauf" in text and "1,5" in text


def test_lernen_gemischt_nennt_die_ausnahme_im_selben_satz():
    z = [zeile(4, 12, 10), zeile(5, 100, 20)]
    kind, text = E.verdict_lernen(z, "statisch")
    assert kind == "info" and "nicht bei 4 × 4" in text and "mindestens 5,0-fach" in text and "in 1 von 1 Schritten" in text


def test_lernen_zaehlt_abbrueche_und_waehlt_die_reihenfolge():
    z = [zeile(7, 100, 10, ohne_gew=50, mit_gew=5, ab_ohne=2, ab_mit=1)]
    kind, text = E.verdict_lernen(z, "statisch")
    assert "Abbrüche am Budget: 2 ohne, 1 mit Lernen (von je 12 Läufen)" in text and "100 → 10" in text
    kind, text = E.verdict_lernen(z, "gewichtet")
    assert "50 → 5 (10,0-fach)" in text and "gewichtete Reihenfolge" in text


def test_lernen_ein_median_null_wird_als_eins_gerechnet():
    kind, text = E.verdict_lernen([zeile(4, 0, 0)], "statisch")
    assert kind == "warning" and "(1,0-fach)" in text


def test_gewichtung_holt_auf_oder_nicht():
    z = [zeile(6, 100, 10, ohne_gew=50), zeile(7, 100, 10, ohne_gew=12)]
    kind, text = E.verdict_gewichtung(z)
    assert "6 × 6: Gewichtung 2,0-fach, Lernen 10,0-fach" in text and "7 × 7: Gewichtung 8,3-fach, Lernen 10,0-fach" in text
    assert "in 1 von 2 Größen" in text and kind == "info"                    # 12 / 10 = 1,2 < 1,5: nur die zweite Größe
    assert E.verdict_gewichtung([zeile(6, 100, 10, ohne_gew=10)])[0] == "warning"


@pytest.mark.parametrize("mini,lern,wort", [(2, 20, "Mini-CP weniger"), (20, 2, "Lernen weniger"), (3, 4, "gleichauf"), (4, 3, "gleichauf"), (3, 2, "Lernen weniger"), (2, 3, "Mini-CP weniger"), (7, 7, "gleichauf")])
def test_zugeschnitten_urteil_je_groesse(mini, lern, wort):
    kind, text = E.verdict_zugeschnitten([zeile(6, 100, lern, mini2=mini)])
    assert f"{mini} Knoten gegen {lern} Konflikte ({wort})" in text
    assert "verschiedene Einheiten" in text


def test_zugeschnitten_zaehlt_und_kind():
    z = [zeile(5, 10, 3, mini2=1), zeile(6, 10, 19, mini2=2), zeile(7, 10, 12, mini2=12)]
    kind, text = E.verdict_zugeschnitten(z)
    assert "das Mini-CP in 2 von 3 Größen, das Lernen in 0, gleichauf (Abstand unter dem Faktor 1,5) sind 1" in text and kind == "info"
    assert E.verdict_zugeschnitten([zeile(6, 100, 2, mini2=30)])[0] == "success"          # nur wenn das Lernen überall weniger braucht


def row(**kw):
    r = {"opt": 53, "klauseln": 4909, "wurzel_leer": False, "ohne_stat": 806, "ohne_gew": 266, "mit_stat": 60, "mit_gew": 62, "standard": 20, "mini1": 9, "mini2": 7}
    r.update(kw)
    return r


def test_instanz_normal_nennt_alle_zahlen():
    kind, text = E.verdict_instanz(row(), 2000)
    assert kind == "info"
    for s in ("Optimum 53", "„Makespan ≤ 52“", "4 909 Klauseln", "806 (statisch), 266 (gewichtet)", "60 (statisch), 62 (gewichtet)", "Standard-CDCL (VSIDS, Neustarts): 20", "9 Knoten (Stufe 1), 7 (Stufe 2)"):
        assert s in text, s


def test_instanz_abbruch_wird_als_untergrenze_gezeigt():
    kind, text = E.verdict_instanz(row(ohne_stat=None), 2000)
    assert "≥ 2 000 (Budget) (statisch)" in text


def test_instanz_ohne_effekt_meldet_keinen_effekt():
    kind, text = E.verdict_instanz(row(ohne_stat=1, ohne_gew=1, mit_stat=0, mit_gew=1), 2000)
    assert kind == "warning" and "höchstens einem Konflikt" in text and "52" in text
    kind, text = E.verdict_instanz(row(wurzel_leer=True), 2000)
    assert kind == "warning" and "leere Klausel" in text and "Horizont 52" in text


def schub(h, ohne, ab=False):
    return {"h": h, "ohne": ohne, "ohne_abgebrochen": ab, "ohne_budget": 100 if ab else None, "hall": 0, "hall_fehlschlaege": 1}


def test_schubfach_verdikt_mit_wachstumsfaktor_und_hinweis():
    z = [schub(3, 7), schub(4, 28), schub(5, 159), schub(6, 1004)]
    kind, text = E.verdict_schubfach(z, 6)
    assert "h = 6 (7 Tauben auf 6 Löcher)" in text and "1 004 Konflikte" in text and "mit der Hall-Erklärung braucht die Suche 0" in text
    assert "Faktor 4,0 bis 6,3 (h = 3 bis 6)" in text and "1 Fehlschlag an der Wurzel" in text
    assert "trivial im Sinn der Konstruktion" in text and "nicht, dass Lazy Clause Generation allgemein schneller wäre" in text
    kind, text = E.verdict_schubfach(z, 3)
    assert "Faktor" not in text and "7 Konflikte" in text


def test_schubfach_abbruch_steht_als_untergrenze_da():
    kind, text = E.verdict_schubfach([schub(3, 7), schub(4, 100, ab=True)], 4)
    assert "≥ 100 (Budget) Konflikte" in text and "Faktor" not in text


def test_klausel_verdikte():
    gut = A.Pruefung("gueltig", None, 1, 20000)
    kind, text = E.verdict_klausel(gut, "x3 ≠ 1 ∨ x1 = 3")
    assert kind == "success" and "„x3 ≠ 1 ∨ x1 = 3“" in text and "1 Konflikt," in text and "Budget 20 000" in text
    kind, text = E.verdict_klausel(A.Pruefung("ungueltig", {1: True}, 0, 20000), "x3 ≠ 1", zu_stark=True)
    assert kind == "error" and text.startswith("Die absichtlich zu starke Klausel") and "0 Konflikte" in text
    kind, text = E.verdict_klausel(A.Pruefung("unentschieden", None, 5, 5), "leer")
    assert kind == "warning" and "Budget von 5 Konflikten" in text


def test_pruefbilanz():
    f = [{"geprueft": 216, "gueltig": 216, "ungueltig": 0, "unentschieden": 0}, {"geprueft": 6, "gueltig": 5, "ungueltig": 0, "unentschieden": 1}]
    kind, text = E.verdict_pruefbilanz(f)
    assert kind == "success" and "222 Klauseln in 2 Familien, davon 221 gültig, 0 ungültig, 1 unentschieden" in text
    f[0]["ungueltig"] = 1
    assert E.verdict_pruefbilanz(f)[0] == "error"


def test_h1_verdikt_aus_der_aufzaehlung():
    kind, text = E.verdict_h1(E.h1_analyse())
    assert kind == "success"
    assert "4 Lösungen" in text and "nach x1 ≠ 3 bleiben 2" in text and "zieht 2 Schlüsse" in text and "x3 = 3" in text


@pytest.mark.parametrize("H,anzahl,teil", [(3, 1, "Bei Horizont 3 gibt es 1 Plan (Aufzählung). Im einzigen Plan gilt: a vor d und c vor b"), (4, 7, "In allen 7 gilt: a vor d und c vor b"), (5, 26, "In allen 26 gilt: a vor d und c vor b")])
def test_h2_verdikt(H, anzahl, teil):
    kind, text = E.verdict_h2(E.h2_analyse(H))
    assert kind == "info" and teil in text and (f"{anzahl} Pläne" in text or anzahl == 1)


def test_h2_verdikt_ohne_plan():
    kind, text = E.verdict_h2(E.h2_analyse(2))
    assert kind == "warning" and "keinen Plan (Aufzählung: 0 Pläne)" in text and "leere Klausel" in text


def test_h1_schritt_texte():
    ev = A.hall_schritte([[1, 2, 3], [1, 2], [1, 2, 3]], [(0, 3)])
    assert "x1 ∈ {1, 2, 3}; x2 ∈ {1, 2}; x3 ∈ {1, 2, 3}" in E.h1_schritt_text(ev[0])
    assert E.h1_schritt_text(ev[1]) == "Entscheidung: x1 ≠ 3 (der Wert 3 fällt aus x1)."
    t = E.h1_schritt_text(ev[2])
    assert t.startswith("x1 und x2 teilen sich die Werte {1, 2}") and "fällt 1 aus x3" in t and "das heißt: x1 = 3" in t
    assert "Festgelegt: x3 = 3" in E.h1_schritt_text(ev[-1])
