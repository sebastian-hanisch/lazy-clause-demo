"""Inhalt der App je Experiment und Preset (AppTest): die erwarteten Verdikt-Zeilen, die Prüfknöpfe und die Zahlen in den Hilfetexten (DEMO-PLAYBOOK §11a Punkt 7)."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import lcg_aufzaehlung as Z
import lcg_constants as C
import lcg_evaluation as E
import lcg_scenario as S

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texte(at) -> str:
    teile = [m.value for m in at.markdown] + [m.value for m in at.success] + [m.value for m in at.info] + [m.value for m in at.warning] + [m.value for m in at.error] + [m.value for m in at.caption]
    return "\n".join(teile)


def _preset(at, name):
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_kernfrage_nennt_die_gemessenen_zahlen_der_messreihe():
    at = _app()
    t = _texte(at)
    zeilen = E.groessen_zeilen(E.lade_messreihen())
    letzte = zeilen[-1]
    assert E.verdict_lernen(zeilen, "statisch")[1] in t
    metriken = {m.label: m.value for m in at.metric}
    assert metriken["ohne Lernen, 8 × 8 (Median Konflikte)"] == E.zahl(letzte["ohne_stat"]["median"])
    assert metriken["mit Lernen (Median Konflikte)"] == E.zahl(letzte["mit_stat"]["median"])
    assert metriken["Mini-CP Stufe 2 (Median Knoten)"] == E.zahl(letzte["mini2"]["median"])


def test_h1_verdikt_schritte_und_pruefknopf():
    at = _app()
    a = E.h1_analyse()
    assert E.verdict_h1(a)[1] in _texte(at)
    assert "x3 ≠ 1 ∨ x1 = 3" in _texte(at)
    at.slider(key="schritt_h1").set_value(2).run(timeout=TIMEOUT)
    assert "teilen sich die Werte {1, 2}" in _texte(at) and "fällt 1 aus x3" in _texte(at)
    at.button(key="pruefe_h1").click().run(timeout=TIMEOUT)
    assert any("ist **gültig**" in s.value and "x3 ≠ 1 ∨ x1 = 3" in s.value for s in at.success)
    assert "gilt in allen 4 Lösungen" in _texte(at)


def test_h1_zu_starke_klausel_wird_gefangen_mit_gegenbeispiel():
    at = _app()
    at.toggle(key="zu_stark_toggle").set_value(True).run(timeout=TIMEOUT)
    at.button(key="pruefe_h1").click().run(timeout=TIMEOUT)
    assert any("ist **ungültig**" in e.value and "„x3 ≠ 1“" in e.value for e in at.error)
    assert "(x1, x2, x3) = (3, 2, 1)" in _texte(at)
    assert "gilt in nicht allen 4 Lösungen; verletzt in 1 von 4" in _texte(at)


@pytest.mark.parametrize("H,teil", [(3, "Im einzigen Plan gilt: a vor d und c vor b"), (4, "In allen 7 gilt: a vor d und c vor b"), (5, "In allen 26 gilt: a vor d und c vor b")])
def test_h2_je_horizont_verdikt_und_pruefung(H, teil):
    at = _preset(_app(), "Handbeispiel H2: Mini-Job-Shop 2 × 2")
    at.radio(key="h2_horizont_radio").set_value(H).run(timeout=TIMEOUT)
    assert not at.exception and teil in _texte(at)
    at.button(key="pruefe_h2").click().run(timeout=TIMEOUT)
    assert any("ist **gültig**" in s.value for s in at.success)
    at.toggle(key="zu_stark_toggle").set_value(True).run(timeout=TIMEOUT)
    at.button(key="pruefe_h2").click().run(timeout=TIMEOUT)
    assert any("ist **ungültig**" in e.value for e in at.error) and "Startzeiten (a, b, c, d) =" in _texte(at)


def test_preset_h2_bei_horizont_4_nennt_sieben_plaene_und_beide_reihenfolgen():
    at = _preset(_app(), "Handbeispiel H2: Mini-Job-Shop 2 × 2")
    assert [m.value for m in at.metric if m.label == "Pläne (Aufzählung)"] == ["7"]
    assert "In allen 7 gilt: a vor d und c vor b" in _texte(at) and "2 von 2 schon an der Wurzel fest" in _texte(at)


@pytest.mark.parametrize("h,ohne", [(3, "7"), (5, "159"), (6, "1 004"), (7, "4 811")])
def test_schubfach_preset_und_regler(h, ohne):
    at = _preset(_app(), "Schubfach h = 5")
    at.slider(key="h_slider").set_value(h).run(timeout=TIMEOUT)
    t = _texte(at)
    assert f"h = {h} ({h + 1} Tauben auf {h} Löcher)" in t and f"braucht {ohne} Konflikte" in t and "mit der Hall-Erklärung braucht die Suche 0" in t
    assert "trivial im Sinn der Konstruktion" in t


def test_schubfach_h8_ist_vorgerechnet_und_so_gekennzeichnet():
    at = _preset(_app(), "Schubfach h = 5")
    at.slider(key="h_slider").set_value(8).run(timeout=TIMEOUT)
    t = _texte(at)
    assert "braucht 27 932 Konflikte" in t and "vorgerechnet" in t and not at.exception


def test_preset_job_shop_6x6_zeigt_die_vier_varianten_der_einzelinstanz():
    at = _preset(_app(), "Job Shop 6 × 6")
    row = E.jobshop_lauf(S.jobshop_instanz(6, C.DEFAULT_SEED), C.DEFAULT_BUDGET, C.MESS_BUDGET_MINICP)
    assert E.verdict_instanz(row, C.DEFAULT_BUDGET)[1] in _texte(at)
    werte = {m.label: m.value for m in at.metric}
    for v in E.VARIANTEN:
        assert werte[E.VARIANTEN_NAMEN[v]] == E.zahl(row[v])
    at.radio(key="reihenfolge_radio").set_value("gewichtet").run(timeout=TIMEOUT)
    assert E.verdict_lernen(E.groessen_zeilen(E.lade_messreihen()), "gewichtet")[1] in _texte(at)


def test_job_shop_klausel_pruefen_in_der_lernspur():
    at = _preset(_app(), "Job Shop 6 × 6")
    at.button(key="pruefe_lern").click().run(timeout=TIMEOUT)
    assert not at.exception and any("ist **gültig**" in s.value and "gelernte Klausel" in s.value for s in at.success)


def test_live_messreihe_auf_knopfdruck_und_grenze_der_groesse():
    at = _preset(_app(), "Job Shop 6 × 6")
    at.button(key="live_reihe").click().run(timeout=TIMEOUT)
    assert not at.exception and "Live gerechnet in" in _texte(at) and "Median der Konflikte ohne → mit Lernen (statische Reihenfolge, 1 Größen): 6 × 6:" in _texte(at)
    at.slider(key="groesse_slider").set_value(7).run(timeout=TIMEOUT)
    assert not at.exception and "rechnet bis Größe 6 × 6" in _texte(at) and not [b for b in at.button if b.key == "live_reihe"]


def test_experiment_vier_nennt_cpsat_als_eingefroren_und_die_verdikte():
    at = _app()
    at.radio(key="experiment_radio").set_value(C.EXPERIMENTE[3]).run(timeout=TIMEOUT)
    assert not at.exception
    t = _texte(at)
    zeilen = E.groessen_zeilen(E.lade_messreihen())
    assert E.verdict_zugeschnitten(zeilen)[1] in t and E.verdict_gewichtung(zeilen)[1] in t
    assert "vorgerechnet und eingefroren" in t and "0 Abweichungen" in t and "verschiedene Einheiten" in t


def test_experiment_eins_pruefbilanz_aus_der_messreihe():
    at = _app()
    bilanz = E.lade_messreihen()["pruefung"]
    assert E.verdict_pruefbilanz(bilanz)[1] in _texte(at)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_hilfetexte_der_presets_nennen_nur_belegte_zahlen(name):
    h = C.PRESET_HELP[name]
    if name == "Schubfach h = 5":
        assert "159 Konflikte" in h and "0 Konflikte" in h
    if name == "Job Shop 6 × 6":
        assert "12 feste Zufalls-Seeds" in h and len(C.MESS_SEEDS) == 12 and "6 Aufträgen auf 6 Maschinen" in h
    if name.startswith("Handbeispiel H2"):
        assert "sieben Pläne" in h and len(Z.jobshop_plaene([list(j) for j in S.H2_JOBS], 4)) == 7
