"""Layout (DEMO-PLAYBOOK §2): fester Kopf, Schnellstart oben in der Seitenleiste, aktives Preset hervorgehoben.

Die Hervorhebung ist zustandslos (`aktives_preset` vergleicht jeden Regler aus SETTING_SPECS mit dem Preset). Der Test unten stellt
sicher, dass wirklich JEDER Regler dort steht: sonst bliebe das Preset trotz Änderung markiert. Regler, die nur in einem Experiment gezeichnet werden (KEPT),
werden mit dem Preset geprüft, in dem sie sichtbar sind."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import lcg_constants as C
import lcg_presets as P

APP = str(Path(__file__).resolve().parent.parent / "app.py")
REGLER_ARTEN = ("slider", "number_input", "select_slider", "selectbox", "radio", "toggle", "checkbox", "text_input")
# Preset, in dessen Experiment der Regler gezeichnet ist
SICHTBAR_IM_PRESET = {
    "beispiel_radio": "Handbeispiel H1: Hall-Erklärung", "zu_stark_toggle": "Handbeispiel H1: Hall-Erklärung", "h2_horizont_radio": "Handbeispiel H2: Mini-Job-Shop 2 × 2",
    "h_slider": "Schubfach h = 5", "reihenfolge_radio": "Job Shop 6 × 6",
}


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _typen(at) -> dict:
    """Button-Typ je Preset-Name (die Preset-Buttons der Seitenleiste)."""
    return {b.label: b.proto.type for b in at.sidebar.button if b.label in C.PRESETS}


def _regler(at, key):
    """Regler in der Seitenleiste oder im Hauptbereich (die experimentbezogenen Regler stehen im Hauptbereich)."""
    for art in REGLER_ARTEN:
        try:
            return getattr(at, art)(key=key)
        except KeyError:
            continue
    raise AssertionError(f"Regler {key} steht weder in der Seitenleiste noch im Hauptbereich")


def _anderer_wert(spec, aktuell):
    if spec.options is not None:
        return next(o for o in spec.options if o != aktuell)
    if spec.default is False:
        return not aktuell
    return spec.hi if aktuell != spec.hi else spec.lo


def test_presets_stehen_in_der_seitenleiste_und_nicht_im_hauptbereich():
    at = _app()
    assert [b.label for b in at.sidebar.button][: len(C.PRESETS)] == list(C.PRESETS)  # die ersten Buttons der Seitenleiste
    assert not [b for b in at.main.button if b.label in C.PRESETS]


def test_titel_steht_im_festen_kopf():
    at = _app()
    assert "st-key-kopf" in " ".join(h.proto.body for h in at.get("html"))  # das Stylesheet setzt an der Klasse des Containers an
    assert at.title[0].value


def test_beim_start_ist_genau_das_standard_preset_hervorgehoben():
    typen = _typen(_app())
    assert [name for name, typ in typen.items() if typ == "primary"] == [next(iter(C.PRESETS))]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_angeklicktes_preset_ist_hervorgehoben_und_bleibt_es_im_naechsten_lauf(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert not at.exception
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]
    at.run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_schaltet_das_experiment_um(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert at.radio(key="experiment_radio").value == C.PRESETS[name].get("experiment", C.DEFAULT_EXPERIMENT)


def test_jeder_regler_der_seitenleiste_steht_in_setting_specs():
    at = _app()
    schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.sidebar, art) if w.key}
    fehlt = schluessel - set(P.SETTING_SPECS)
    assert not fehlt, f"Regler {sorted(fehlt)} fehlen in SETTING_SPECS: ihre Änderung hebt das aktive Preset nicht auf"


def test_jeder_regler_im_hauptbereich_steht_in_setting_specs():
    for name in C.PRESETS:
        at = _app()
        at.sidebar.button(key=f"preset_{name}").click().run()
        schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.main, art) if w.key}
        schluessel = {k for k in schluessel if not k.startswith(("schritt", "klausel_", "gelernt_"))}   # Schritt- und Klausel-Auswahl gehören nicht zu den Einstellungen des Presets
        assert not (schluessel - set(P.SETTING_SPECS)), (name, schluessel - set(P.SETTING_SPECS))


@pytest.mark.parametrize("state_key", list(P.SETTING_SPECS))
def test_jede_aenderung_eines_reglers_hebt_die_hervorhebung_auf(state_key):
    at = _app()
    name = SICHTBAR_IM_PRESET.get(state_key, next(iter(C.PRESETS)))
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert _typen(at)[name] == "primary"
    spec = P.SETTING_SPECS[state_key]
    regler = _regler(at, state_key)
    regler.set_value(_anderer_wert(spec, regler.value)).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert _typen(at)[name] != "primary", state_key                   # das geänderte Preset ist nicht mehr hervorgehoben (ein anderes darf es sein: gleiche Werte)
    # erneutes Anklicken markiert wieder
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert _typen(at)[name] == "primary"
