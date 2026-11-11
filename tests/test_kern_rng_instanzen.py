"""Regressionstests der kopierten Module `lcg_rng` und `lcg_instanzen` (Werte aus sat-cp-planung/kern/tests; die Referenzwerte der Formel stammen aus
`random_formula` in reduktionskette-demo/red_scenario.py, deren Strom der Kern wörtlich übernimmt)."""

import pytest

import lcg_instanzen as I
from lcg_cdcl import solve
from lcg_rng import SplitMix64


def test_splitmix_bekannte_werte():
    # Veröffentlichte Referenzwerte der SplitMix64-Konvention für Seed 0 (Vigna) und Seed 12345
    g = SplitMix64(0)
    assert [g.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]
    assert [SplitMix64(12345).next() for _ in range(1)] == [2454886589211414944]
    h = SplitMix64(12345)
    assert [h.next() for _ in range(3)] == [2454886589211414944, 3778200017661327597, 2205171434679333405]


def test_hilfsmethoden():
    g = SplitMix64(5)
    xs = [g.random() for _ in range(1000)]
    assert all(0 <= x < 1 for x in xs) and 0.45 < sum(xs) / 1000 < 0.55
    liste = list(range(20))
    SplitMix64(3).shuffle(liste)
    assert sorted(liste) == list(range(20)) and liste != list(range(20))
    probe = SplitMix64(3).sample(range(50), 7)
    assert len(set(probe)) == 7
    assert SplitMix64(3).sample(range(50), 7) == probe          # deterministisch
    assert SplitMix64(1).randrange(10) == SplitMix64(1).below(10)


def test_rand3_referenzwert_und_praefix():
    assert I.rand3(5, 3, 7).klauseln == [(3, -2, -1), (-4, -1, 5), (1, 2, -3)]
    kurz, lang = I.rand3(20, 30, 1).klauseln, I.rand3(20, 40, 1).klauseln
    assert lang[:30] == kurz                                      # wächst m, bleiben die früheren Klauseln
    assert all(len({abs(l) for l in c}) == 3 for c in lang)


def test_schubfach_handwerte():
    inst = I.pigeonhole(2)                      # 3 Tauben, 2 Löcher
    assert inst.n == 6
    assert len(inst.klauseln) == 3 + 2 * 3     # 3 Taubenklauseln, je Loch 3 Paare
    assert (1, 2) in inst.klauseln and (-1, -3) in inst.klauseln
    assert solve(inst.n, inst.klauseln).antwort is False


def test_faerbung_dreieck():
    dreieck = I.faerbung(3, [(0, 1), (1, 2), (0, 2)], 2)
    assert solve(dreieck.n, dreieck.klauseln).antwort is False
    drei = I.faerbung(3, [(0, 1), (1, 2), (0, 2)], 3)
    erg = solve(drei.n, drei.klauseln)
    assert erg.antwort is True
    assert len(set(I.faerbung_aus_modell(drei, erg.modell))) == 3


def test_flat_graph_und_rampen_deterministisch():
    a, b = I.flat_graph(40, 4.0, 3), I.flat_graph(40, 4.0, 3)
    assert a.klauseln == b.klauseln and len(a.meta["kanten"]) == 80
    assert a.klauseln != I.flat_graph(40, 4.0, 4).klauseln
    r = I.rampen_instanz(30, 3.0, 2, 4)
    assert r.meta["einkleidung"] == "rampen" and r.meta["rampen"] == 4
    with pytest.raises(ValueError):
        I.zufallskanten(4, 7, 0)


def test_pruefe_modell():
    assert I.pruefe_modell([(1, 2), (-1, 2)], {1: True, 2: True})
    assert not I.pruefe_modell([(1, 2), (-1, -2)], {1: True, 2: True})
