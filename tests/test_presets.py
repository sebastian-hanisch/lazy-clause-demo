"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen, Permalink-Bereinigung."""

import lcg_constants as C
import lcg_presets as P


def test_every_preset_has_help_and_only_known_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) <= set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_bounds_or_options():
    for name, preset in C.PRESETS.items():
        for key, value in preset.items():
            spec = P.SETTING_SPECS[P.PRESET_KEYS[key]]
            if spec.options is not None:
                assert value in spec.options, (name, key)
            elif spec.lo is not None:
                assert spec.lo <= value <= spec.hi, (name, key)


def test_default_preset_equals_the_default_settings():
    """Das erste Preset nennt nur Werte, die dem Standard entsprechen (die Voreinstellung der App ist Handbeispiel H1)."""
    erstes = C.PRESETS[next(iter(C.PRESETS))]
    for key, value in erstes.items():
        assert value == P.SETTING_SPECS[P.PRESET_KEYS[key]].default, key


def test_every_preset_differs_from_every_other():
    namen = list(C.PRESETS)
    vollstaendig = [{k: C.PRESETS[n].get(k, P.SETTING_SPECS[v].default) for k, v in P.PRESET_KEYS.items()} for n in namen]
    for i, a in enumerate(vollstaendig):
        for b in vollstaendig[i + 1:]:
            assert a != b


def test_setting_specs_cover_every_preset_key_and_url_params_are_unique():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)
    params = [s.url_param for s in P.SETTING_SPECS.values()]
    assert len(params) == len(set(params))
    assert set(P.KEPT) <= set(P.SETTING_SPECS)


def test_permalink_bereinigung_begrenzt_und_verwirft_ungueltiges():
    assert P._bereinige(P.SETTING_SPECS["h_slider"], 99) == C.H_MAX
    assert P._bereinige(P.SETTING_SPECS["h_slider"], -5) == C.H_MIN
    assert P._bereinige(P.SETTING_SPECS["groesse_slider"], 2) == C.GROESSE_MIN
    assert P._bereinige(P.SETTING_SPECS["budget_slider"], 2000) == 2000
    assert P._bereinige(P.SETTING_SPECS["budget_slider"], 12345) is None
    assert P._bereinige(P.SETTING_SPECS["experiment_radio"], "5 · gibt es nicht") is None
    assert P._wahrheitswert("True") is True and P._wahrheitswert("0") is False and P._wahrheitswert("ja") is True


def test_standardwerte_liegen_in_den_grenzen():
    assert C.H_MIN <= C.DEFAULT_H <= C.H_MAX and C.GROESSE_MIN <= C.DEFAULT_GROESSE <= C.GROESSE_MAX
    assert C.DEFAULT_BUDGET in C.BUDGET_OPTIONEN and C.DEFAULT_H2_HORIZONT in C.H2_HORIZONT_OPTIONEN
    assert C.DEFAULT_EXPERIMENT in C.EXPERIMENTE and C.DEFAULT_BEISPIEL in C.BEISPIELE and C.DEFAULT_REIHENFOLGE in C.REIHENFOLGEN
    assert C.LIVE_H_MAX < C.H_MAX                      # h = 8 ist vorgerechnet, nie live
    assert C.LIVE_MESS_GROESSE_MAX <= C.GROESSE_MAX
