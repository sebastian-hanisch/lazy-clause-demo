"""Die kopierten Module sind unverändert gegenüber ihrer Herkunft, die im Modulkopf steht.

* `lcg_rng.py`, `lcg_instanzen.py`, `lcg_cdcl.py`: Kopien aus `sat-cp-planung/kern/` (Kern-Version = SHA-256 der Datei, auf 16 Zeichen gekürzt, Zeilenenden egal), nur die Importe sind auf `lcg_` umgestellt.
* `lcg_jobshop.py` (aus `dje_scenario.py`) und `lcg_minicp.py` (aus `dje_algorithm.py`) stammen aus Stück 11 (`disjunktiv-edge-finding-demo`) mit je einer dokumentierten Abweichung (siehe deren Kopf).
Der Test setzt die Abweichungen zurück und vergleicht dann mit dem im Kopf genannten Hash."""

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Zurücksetzen der Abweichungen
STUFE3 = ("        elif stufe >= 3:\n"
          "            from dje_baum import edge_finding_baum  # Erweiterung 11b\n"
          "\n"
          "            r = edge_finding_baum(M, est, lst, z, prot)\n"
          "            if r is None:\n"
          "                return \"edge\"\n"
          "            veraendert = veraendert or r\n")
ANKER_STUFE2 = "            veraendert = veraendert or r\n        if not veraendert:\n"


def _text(name: str) -> str:
    return (ROOT / f"lcg_{name}.py").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _ohne_kopf(text: str) -> str:
    zeilen = text.split("\n")
    i = 0
    while zeilen[i].startswith("#"):
        i += 1
    return "\n".join(zeilen[i:])


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@pytest.mark.parametrize("modul", ["rng", "instanzen", "cdcl"])
def test_kern_kopie_gleicht_der_kern_version(modul):
    text = _text(modul)
    version = re.match(r"# Herkunft: Kopie von sat-cp-planung/kern/\w+\.py \(Kern-Version ([0-9a-f]{16})", text).group(1)
    original = _ohne_kopf(text).replace("from lcg_rng import", "from rng import")
    assert _hash(original) == version


def test_jobshop_kopie_gleicht_stueck_11():
    text = _text("jobshop")
    version = re.match(r"# Herkunft: Kopie von disjunktiv-edge-finding-demo/dje_scenario\.py \(Stück 11, SHA-256 gekürzt ([0-9a-f]{16})", text).group(1)
    original = _ohne_kopf(text)
    original = original.replace("from lcg_rng import SplitMix64", "import dje_constants as C\nfrom dje_rng import SplitMix64")
    assert "dmax: int = 9" in original
    original = original.replace("dmax: int = 9", "dmax: int = C.DMAX_DEFAULT")
    assert _hash(original) == version


def test_minicp_kopie_gleicht_stueck_11():
    text = _text("minicp")
    version = re.match(r"# Herkunft: Kopie von disjunktiv-edge-finding-demo/dje_algorithm\.py \(Stück 11, SHA-256 gekürzt ([0-9a-f]{16})", text).group(1)
    original = _ohne_kopf(text).replace("from lcg_jobshop import Instance, spt_plan", "from dje_scenario import Instance, spt_plan")
    assert ANKER_STUFE2 in original and "stufe >= 3" not in original
    original = original.replace(ANKER_STUFE2, ANKER_STUFE2.replace("        if not veraendert:\n", STUFE3 + "        if not veraendert:\n"))
    assert _hash(original) == version


ERLAUBT_STDLIB = {"heapq", "itertools", "dataclasses", "typing", "math", "json", "pathlib", "time", "datetime", "hashlib", "re"}


def test_module_importieren_nichts_aus_anderen_demos_oder_dem_kern():
    """Jeder Import in `lcg_*.py` ist Standardbibliothek, ein Laufzeitpaket (numpy, scipy, pandas, plotly, streamlit, fpdf2) oder ein anderes `lcg_`-Modul."""
    for datei in sorted(ROOT.glob("lcg_*.py")):
        for zeile in datei.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:from|import)\s+([A-Za-z_][\w]*)", zeile)
            if m and not zeile.startswith("#"):
                name = m.group(1)
                assert name.startswith("lcg_") or name in ERLAUBT_STDLIB | {"numpy", "scipy", "pandas", "plotly", "streamlit", "fpdf"}, (datei.name, zeile)
