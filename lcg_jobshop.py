# Herkunft: Kopie von disjunktiv-edge-finding-demo/dje_scenario.py (Stück 11, SHA-256 gekürzt 0d3f776c7d49ee9e, gelesen am 2026-11-11).
# Abweichungen: Importe auf lcg_ umgestellt, der Zugriff auf `dje_constants` entfällt (`DMAX_DEFAULT` steht als Zahl 9 im Kopf von `make_jobshop`).
# tests/test_copies.py setzt diese Stellen zurück und vergleicht mit dem genannten Hash.
"""Szenario: Job-Shop-Instanzen mit eigenem Zufallsgenerator (SplitMix64, `dje_rng.py`), damit jede Instanz auf jeder Plattform und in jeder Python-Version gleich ist.

Ein Job Shop hat Aufträge (Jobs); jeder Auftrag besteht aus Operationen in fester Reihenfolge, jede Operation braucht eine Maschine für eine ganzzahlige Dauer.
Eine Maschine bearbeitet höchstens eine Operation zugleich (disjunktive Ressource), und die Operationen eines Auftrags laufen nacheinander.
Operation (j, k) ist die k-te Operation von Auftrag j; in den Listen steht sie an der Stelle j-ter Auftrag mal Länge plus k (siehe `dje_algorithm.Modell`)."""

from dataclasses import dataclass

from lcg_rng import SplitMix64


@dataclass(frozen=True)
class Instance:
    """`jobs[j][k] = (Maschine, Dauer)`; Maschinen sind 0, 1, 2, ... nummeriert."""

    jobs: tuple[tuple[tuple[int, int], ...], ...]

    @property
    def n_jobs(self) -> int:
        return len(self.jobs)

    @property
    def n_machines(self) -> int:
        return 1 + max(m for job in self.jobs for m, _ in job) if self.jobs else 0

    @property
    def n_ops(self) -> int:
        return sum(len(job) for job in self.jobs)

    @property
    def total_duration(self) -> int:
        return sum(d for job in self.jobs for _, d in job)


def as_instance(jobs) -> Instance:
    """Aus verschachtelten Listen eine Instanz machen (Maschine und Dauer werden ganzzahlig, Dauer mindestens 1)."""
    out = tuple(tuple((int(m), int(d)) for m, d in job) for job in jobs)
    if any(d < 1 for job in out for _, d in job):
        raise ValueError("jede Dauer ist mindestens 1")
    return Instance(out)


# Das Handbeispiel aus der README und der App: 3 Aufträge, 3 Maschinen, optimaler Makespan 8.
HANDBEISPIEL = as_instance([
    [(2, 2), (0, 2), (1, 1)],
    [(0, 2), (2, 1), (1, 2)],
    [(2, 2), (0, 1), (1, 2)],
])


def make_jobshop(n_jobs: int, n_machines: int, seed: int, dmax: int = 9) -> Instance:
    """Zufalls-Job-Shop: jeder Auftrag besucht jede Maschine genau einmal in zufälliger Reihenfolge, Dauern gleichverteilt in 1 bis dmax.

    Ziehungsreihenfolge (festgelegt, damit der Strom reproduzierbar bleibt): je Auftrag zuerst die Maschinenreihenfolge (Fisher-Yates von hinten nach vorn),
    danach die Dauern der Operationen in dieser Reihenfolge."""
    rng = SplitMix64(seed)
    jobs = []
    for _ in range(n_jobs):
        order = list(range(n_machines))
        for i in range(n_machines - 1, 0, -1):
            j = rng.below(i + 1)
            order[i], order[j] = order[j], order[i]
        jobs.append(tuple((m, 1 + rng.below(dmax)) for m in order))
    return Instance(tuple(jobs))


def spt_plan(inst: Instance) -> tuple[int, tuple[int, ...]]:
    """Startschranke: Dispatching-Plan mit der Regel „früheste Startzeit, dann kürzeste Dauer, dann kleinere Auftragsnummer“.

    Rückgabe (Makespan, Startzeiten in der Reihenfolge der Operationen). Das ist ein zulässiger Plan und damit eine obere Schranke für das Optimum."""
    n_jobs = inst.n_jobs
    nxt = [0] * n_jobs
    job_ready = [0] * n_jobs
    mach_ready = [0] * max(inst.n_machines, 1)
    offsets = [sum(len(job) for job in inst.jobs[:j]) for j in range(n_jobs)]
    starts = [0] * inst.n_ops
    cmax = 0
    for _ in range(inst.n_ops):
        best = None
        for j in range(n_jobs):
            if nxt[j] < len(inst.jobs[j]):
                m, d = inst.jobs[j][nxt[j]]
                st = max(job_ready[j], mach_ready[m])
                key = (st, d, j)
                if best is None or key < best[0]:
                    best = (key, j, m, d, st)
        _, j, m, d, st = best
        starts[offsets[j] + nxt[j]] = st
        job_ready[j] = mach_ready[m] = st + d
        nxt[j] += 1
        cmax = max(cmax, st + d)
    return cmax, tuple(starts)
