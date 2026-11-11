"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

import time
from dataclasses import dataclass

import streamlit as st

import lcg_constants as C
from lcg_rng import SplitMix64


def _wahrheitswert(text) -> bool:
    return str(text).strip().lower() in ("1", "true", "ja")


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: object
    default: object
    lo: float | None = None
    hi: float | None = None
    options: tuple | None = None


SETTING_SPECS = {
    "experiment_radio": SettingSpec("exp", str, C.DEFAULT_EXPERIMENT, options=C.EXPERIMENTE),
    "beispiel_radio": SettingSpec("beispiel", str, C.DEFAULT_BEISPIEL, options=C.BEISPIELE),
    "h2_horizont_radio": SettingSpec("h2h", int, C.DEFAULT_H2_HORIZONT, options=C.H2_HORIZONT_OPTIONEN),
    "zu_stark_toggle": SettingSpec("zustark", _wahrheitswert, False),
    "h_slider": SettingSpec("h", int, C.DEFAULT_H, C.H_MIN, C.H_MAX),
    "reihenfolge_radio": SettingSpec("reihenfolge", str, C.DEFAULT_REIHENFOLGE, options=C.REIHENFOLGEN),
    "groesse_slider": SettingSpec("groesse", int, C.DEFAULT_GROESSE, C.GROESSE_MIN, C.GROESSE_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "budget_slider": SettingSpec("budget", int, C.DEFAULT_BUDGET, options=C.BUDGET_OPTIONEN),
}
# Regler, die nur in einem Experiment gezeichnet werden: Streamlit löscht ihren Zustand, sobald sie nicht gezeichnet werden. Der zuletzt gewählte Wert bleibt unter `_kept_<Schlüssel>` erhalten;
# Permalink und Preset schreiben nur dorthin, `seed_widget` setzt den Zustand im selben Lauf, in dem der Regler gezeichnet wird, `stash_kept_widget_state` hält ihn danach fest.
KEPT = {key: f"_kept_{key}" for key in ("beispiel_radio", "h2_horizont_radio", "zu_stark_toggle", "h_slider", "reihenfolge_radio")}
PRESET_KEYS = {
    "experiment": "experiment_radio", "beispiel": "beispiel_radio", "h2_horizont": "h2_horizont_radio", "zu_stark": "zu_stark_toggle", "h": "h_slider",
    "reihenfolge": "reihenfolge_radio", "groesse": "groesse_slider", "seed": "seed_input", "budget": "budget_slider",
}


def init_session_state_defaults():
    """Standardwerte für Widgets, die in jedem Lauf gezeichnet werden. Regler, die nur in einem Experiment gezeichnet werden (KEPT), setzen ihren Wert erst im selben Lauf, in dem sie
    gezeichnet werden (`seed_widget`): ein Wert, der in einem Lauf ohne das Widget gesetzt wurde, erscheint sonst später als Mindestwert im Regler, während die App mit dem gesetzten Wert rechnet."""
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in KEPT and state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def seed_widget(state_key):
    """Vor dem Zeichnen eines ausblendbaren Reglers: fehlt sein Zustand, kommt der zuletzt gewählte (oder der Standard-) Wert."""
    if state_key not in st.session_state:
        st.session_state[state_key] = st.session_state.get(KEPT[state_key], SETTING_SPECS[state_key].default)


def stash_kept_widget_state():
    """Nach dem Zeichnen: den Stand der gezeichneten ausblendbaren Regler festhalten (nicht gezeichnete behalten ihren alten Wert)."""
    for state_key, kept in KEPT.items():
        if state_key in st.session_state:
            st.session_state[kept] = st.session_state[state_key]


def aktueller_wert(state_key):
    """Wert eines Reglers: sein Zustand, wenn er gezeichnet ist, sonst der gemerkte, sonst der Standard."""
    spec = SETTING_SPECS[state_key]
    if state_key in KEPT:
        return st.session_state.get(state_key, st.session_state.get(KEPT[state_key], spec.default))
    return st.session_state.get(state_key, spec.default)


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _bereinige(spec, wert):
    """Wert aus der Adresszeile auf die Reglergrenzen begrenzen beziehungsweise auf erlaubte Optionen prüfen; None = verwerfen."""
    if spec.options is not None:
        return wert if wert in spec.options else None
    if spec.lo is not None:
        wert = max(spec.lo, wert)
    if spec.hi is not None:
        wert = min(spec.hi, wert)
    return wert


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                wert = _bereinige(spec, spec.caster(qp[spec.url_param]))
            except (ValueError, TypeError):
                continue
            if wert is not None:
                st.session_state[KEPT.get(state_key, state_key)] = wert
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    """Ein Preset setzt alle Regler: was es nicht nennt, bekommt den Standardwert."""
    for key, state_key in PRESET_KEYS.items():
        wert = C.PRESETS[name].get(key, SETTING_SPECS[state_key].default)
        if state_key in KEPT:
            st.session_state[KEPT[state_key]] = wert
            st.session_state.pop(state_key, None)                     # der Regler nimmt den Wert aus KEPT, sobald er gezeichnet wird
        else:
            st.session_state[state_key] = wert


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            aktueller_wert(state_key) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden (stellt auch das Experiment ein):")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    """Neuer Zufalls-Seed der Job-Shop-Instanz; der Strom kommt aus dem SplitMix64 des Repos, gespeist von der Uhr."""
    st.session_state["seed_input"] = SplitMix64(time.time_ns()).below(C.SEED_MAX + 1)
