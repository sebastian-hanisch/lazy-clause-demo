"""Gemeinsame Fixtures: die Handbeispiele, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lcg_scenario as S  # noqa: E402


@pytest.fixture
def h1():
    """H1: x1 in {1,2,3}, x2 in {1,2}, x3 in {1,2,3}, alle verschieden (4 Lösungen von Hand, siehe tests/test_algorithm.py)."""
    return [list(d) for d in S.H1_DOMAENEN]


@pytest.fixture
def h2_jobs():
    """H2: a(M1,2) -> b(M2,1) und c(M2,2) -> d(M1,1); Aufzählung: 0 / 1 / 7 / 26 Pläne bei H = 2 / 3 / 4 / 5 (von Hand, siehe tests/test_algorithm.py)."""
    return [list(j) for j in S.H2_JOBS]
