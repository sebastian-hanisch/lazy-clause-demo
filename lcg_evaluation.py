"""Läufe, Kennzahlen und Verdikte (reine Funktionen). Aufwand wird in Konflikten (CNF) beziehungsweise Knoten (Mini-CP) gezählt, nie in Sekunden.

Verdikte sind reine Funktionen `verdict_*(…) -> (Art, Text)`: die App ruft `getattr(st, Art)(Text)`; jede Zahl im Text stammt aus den übergebenen Messwerten,
die Schwellen stehen als Konstanten in `lcg_constants.py` und sind in `tests/test_verdicts.py` geprüft."""

import json
import math
from pathlib import Path

import lcg_algorithm as A
import lcg_constants as C
import lcg_kodierung as K
import lcg_minicp as M
import lcg_scenario as S
from lcg_cdcl import solve

HIER = Path(__file__).resolve().parent

# Die vier Varianten der Gegenüberstellung (gleiche CNF, gleiche Propagation, gleiche Wertregel): Lernen × Reihenfolge
VARIANTEN = ("ohne_stat", "ohne_gew", "mit_stat", "mit_gew")
VARIANTEN_NAMEN = {
    "ohne_stat": "ohne Lernen, statisch",
    "ohne_gew": "ohne Lernen, gewichtet",
    "mit_stat": "mit Lernen, statisch",
    "mit_gew": "mit Lernen, gewichtet",
}
VARIANTEN_FARBEN = {"ohne_stat": C.COLOR_OHNE, "ohne_gew": "#c9a227", "mit_stat": C.COLOR_MIT, "mit_gew": C.COLOR_GEW}
_VARIANTEN_KW = {
    "ohne_stat": dict(lernen=False, reihenfolge="statisch"),
    "ohne_gew": dict(lernen=False, reihenfolge="gewichtet"),
    "mit_stat": dict(lernen=True, reihenfolge="statisch"),
    "mit_gew": dict(lernen=True, reihenfolge="gewichtet"),
}


def zahl(x) -> str:
    """Ganze Zahl mit geschütztem Leerzeichen als Tausendertrenner („27 932“); Dezimalzahlen mit Komma."""
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.1f}".replace(",", " ").replace(".", ",")
    return f"{int(x):,}".replace(",", " ")


def konflikte_text(n) -> str:
    """„1 Konflikt“ oder „n Konflikte“ (n ganzzahlig, mit Tausendertrenner)."""
    return f"{zahl(n)} Konflikt" + ("" if n == 1 else "e")


def dezimal(x: float) -> str:
    """Eine Nachkommastelle mit Komma."""
    return f"{x:.1f}".replace(".", ",")


def faktor_text(f: float) -> str:
    return dezimal(f) + "-fach"


def _gl() -> str:
    """Schwelle „gleichauf“ als Text mit Komma."""
    return f"{C.GLEICHAUF_FAKTOR:g}".replace(".", ",")


# ------------------------------------------------------------------------------------------------------------------------------------------- Läufe
def jobshop_lauf(inst, budget: int = C.MESS_BUDGET, mini_budget: int = C.MESS_BUDGET_MINICP, mit_standard: bool = True) -> dict:
    """Eine Instanz, Entscheidung „Makespan ≤ Optimum − 1“ (unerfüllbar): Konflikte der vier Varianten (Abbruch am Budget: `None`), des Standard-CDCL (VSIDS, Luby, Phasenspeicher, alle Variablen)
    und Knoten des Mini-CP (Stufe 1 und 2, `None` bei Abbruch). Das Optimum liefert das Mini-CP (Stufe 2)."""
    opt, bewiesen = S.optimum(inst)
    kod = K.kodiere_jobshop([list(j) for j in inst.jobs], opt - 1)
    row = {"opt": opt, "optimum_bewiesen": bewiesen, "variablen": kod.n_var, "klauseln": len(kod.klauseln), "wurzel_leer": kod.leer, "antworten": {}}
    for name in VARIANTEN:
        e, _ = A.suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, budget=budget, **_VARIANTEN_KW[name])
        row[name] = None if e.antwort is None else e.stat["konflikte"]
        row["antworten"][name] = e.antwort
    if mit_standard:
        e = solve(kod.n_var, [list(k) for k in kod.klauseln], conflict_budget=budget)
        row["standard"] = None if e.antwort is None else e.stat["konflikte"]
        row["antworten"]["standard"] = e.antwort
    for stufe in (1, 2):
        d = M.entscheide(inst, opt - 1, stufe, budget=mini_budget)
        row[f"mini{stufe}"] = None if d.abgebrochen else d.z.knoten
        row["antworten"][f"mini{stufe}"] = None if d.abgebrochen else d.gefunden
    return row


def schubfach_lauf(h: int, budget_ohne=None) -> dict:
    """Schubfach h + 1 Tauben auf h Löcher: Konflikte des Kern-CDCL (Standardoptionen) und des CDCL mit Hall-Erklärung (Konflikte der Suche; Fehlschläge des Propagators extra)."""
    import lcg_instanzen as I

    inst = I.pigeonhole(h)
    klauseln = [list(k) for k in inst.klauseln]
    e = solve(inst.n, klauseln, conflict_budget=budget_ohne)
    r, s = A.loese_mit_hall(inst.n, klauseln, [K.schubfach_gruppe(h)], protokoll=True)
    return {"h": h, "variablen": inst.n, "klauseln": len(klauseln),
            "ohne": e.stat["konflikte"], "ohne_abgebrochen": e.antwort is None, "ohne_budget": budget_ohne, "ohne_antwort": e.antwort,
            "hall": r.stat["konflikte"], "hall_antwort": r.antwort, "hall_fehlschlaege": s.hall_fehlschlaege, "hall_streichungen": s.hall_streichungen}


# --------------------------------------------------------------------------------------------------------------------------------------- Statistik
def verteilung(werte, budget: int) -> dict:
    """Median, 90-Prozent-Rang (nächster Rang ⌈0,9·n⌉), Maximum und Zahl der Abbrüche; ein Abbruch (`None`) zählt mit dem Budget."""
    ys = sorted(budget if w is None else w for w in werte)
    n = len(ys)
    if n == 0:
        return {"n": 0, "median": 0.0, "p90": 0, "max": 0, "abbrueche": 0}
    median = ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2
    return {"n": n, "median": float(median), "p90": ys[math.ceil(0.9 * n) - 1], "max": ys[-1], "abbrueche": sum(1 for w in werte if w is None)}


def verhaeltnis(a: float, b: float) -> float:
    """a / b mit Schutz gegen 0 (ein Median von 0 zählt als 1, ein Konflikt ist die kleinste Zähleinheit der Aufgabe)."""
    return max(a, 1.0) / max(b, 1.0)


# ------------------------------------------------------------------------------------------------------------------------------------ Messreihen
def lade_messreihen(pfad=None) -> dict:
    return json.loads(Path(pfad or HIER / C.MESSREIHEN_DATEI).read_text(encoding="utf-8"))


def zeile_aus_laeufen(groesse: int, laeufe: list, budget: int, mini_budget: int) -> dict:
    """Eine Zeile (Verteilungen aller Verfahren) aus den Läufen einer Größe: `laeufe` = Liste von Ergebnissen von `jobshop_lauf` (bei der Messreihe zusätzlich mit `cpsat`)."""
    z = {"groesse": groesse, "n": len(laeufe), "optimum_unbewiesen": sum(1 for i in laeufe if not i["optimum_bewiesen"]),
         "wurzel": sum(1 for i in laeufe if i["wurzel_leer"]), "klauseln": verteilung([i["klauseln"] for i in laeufe], 0)["median"]}
    for v in VARIANTEN + ("standard",):
        z[v] = verteilung([i[v] for i in laeufe], budget)
    for v in ("mini1", "mini2"):
        z[v] = verteilung([i[v] for i in laeufe], mini_budget)
    if all("cpsat" in i for i in laeufe):
        z["cpsat"] = verteilung([i["cpsat"] for i in laeufe], 10 ** 9)
    return z


def groessen_zeilen(daten: dict, groessen=None) -> list:
    """Je Größe eine Zeile mit den Verteilungen aller Verfahren (Konflikte der CNF-Varianten, Knoten des Mini-CP, Konflikte von CP-SAT) aus der vorgerechneten Messreihe."""
    return [zeile_aus_laeufen(g, daten["jobshop"][str(g)], daten["meta"]["budget_cnf"], daten["meta"]["budget_minicp"])
            for g in (groessen or sorted(int(k) for k in daten["jobshop"]))]


# ------------------------------------------------------------------------------------------------------------------------------ Handbeispiele (Analysen)
def wurzel_literale(n, klauseln):
    """Literale, die die Einheitspropagation an der Wurzel (Stufe 0) festlegt; `None`, wenn die CNF dort schon unerfüllbar ist."""
    s = A.Suche(n, klauseln)
    if not s.ok:
        return None
    s.springe_zurueck(0)
    if s.propagiere() is not None:
        return None
    return list(s.spur_lit)


def h1_analyse() -> dict:
    """Handbeispiel H1: Aufzählung aller Lösungen, Lösungen nach der Entscheidung x1 ≠ 3, Schritte des Propagators, die CNF der direkten Kodierung."""
    from lcg_aufzaehlung import alldifferent_loesungen

    doms = [list(d) for d in S.H1_DOMAENEN]
    x, w = S.H1_ENTSCHEIDUNG
    alle = alldifferent_loesungen(doms)
    rest = [l for l in alle if l[x] != w]
    kod = K.kodiere_alldifferent(doms)
    return {"doms": doms, "alle": alle, "nach_entscheidung": rest, "schritte": A.hall_schritte(doms, [S.H1_ENTSCHEIDUNG]), "kod": kod}


def klausel_literale(kod, klausel) -> list:
    """Erklärungsklausel (Literale (Variable, Wert, Vorzeichen)) als Literale der direkten Kodierung."""
    return [(kod.var[(i, w)] if pos else -kod.var[(i, w)]) for i, w, pos in klausel]


def zu_starke_klausel(klausel) -> list:
    """Die Klausel ohne ihre Bedingungen: nur das erste Literal (die Streichung selbst). Das ist ein ungültiger Schluss, den die Prüfung fangen muss."""
    return list(klausel[:1])


def h2_analyse(H: int) -> dict:
    """Handbeispiel H2 (Mini-Job-Shop 2 × 2) bei Horizont H: Aufzählung der Pläne, die CNF der Order-Kodierung (ohne Schranken, wie in der Planung), ihre Wurzelbelegung
    und je Maschinenpaar, ob die Aufzählung eine Reihenfolge in allen Plänen findet."""
    from lcg_aufzaehlung import jobshop_plaene

    jobs = [list(j) for j in S.H2_JOBS]
    plaene = jobshop_plaene(jobs, H)
    kod = K.kodiere_jobshop(jobs, H, schranken=False)
    wurzel = None if kod.leer else wurzel_literale(kod.n_var, kod.klauseln)
    paare = {}
    for (a, b) in kod.paar:
        if plaene:
            vor = [p[a] + kod.d[a] <= p[b] for p in plaene]
            paare[(a, b)] = True if all(vor) else (False if not any(vor) else None)
        else:
            paare[(a, b)] = None
    wurzel_paare = {}
    if wurzel is not None:
        for (a, b), y in kod.paar.items():
            if y in wurzel:
                wurzel_paare[(a, b)] = True
            elif -y in wurzel:
                wurzel_paare[(a, b)] = False
    return {"H": H, "plaene": plaene, "kod": kod, "wurzel": wurzel, "paare_aufzaehlung": paare, "paare_wurzel": wurzel_paare}


def paar_klausel(kod, a: int, b: int, a_vor_b: bool) -> list:
    """Einheitsklausel „a vor b“ beziehungsweise „b vor a“ als Literalliste."""
    y = kod.paar[(a, b)]
    return [y] if a_vor_b else [-y]


def lernspur(kod, lernen=True, reihenfolge="statisch", budget=2000, grenze=40) -> dict:
    """Ein Lauf mit Spur: Konflikte, Länge jeder gelernten Klausel und die ersten `grenze` gelernten Klauseln (Literale, Rücksprungstufe, LBD)."""
    s = A.Suche(kod.n_var, kod.klauseln, entscheidungs_vars=kod.entscheidungs_vars, reihenfolge=reihenfolge, lernen=lernen, trace=True)
    e = s.loese(conflict_budget=budget)
    gelernt = [(list(ev[1]), ev[2], ev[3]) for ev in e.spur if ev[0] == "lerne"]
    return {"antwort": e.antwort, "konflikte": e.stat["konflikte"], "laengen": [len(g[0]) for g in gelernt], "gelernt": gelernt[:grenze],
            "gekuerzt": e.spur_gekuerzt, "entscheidungen": e.stat["entscheidungen"]}


# ---------------------------------------------------------------------------------------------------------------------------------------- Verdikte
def _gr(g: int) -> str:
    return f"{g} × {g}"


def verdict_lernen(zeilen, reihenfolge: str) -> tuple[str, str]:
    """Lernen aus gegen an bei gleicher CNF, Propagation, Wertregel und gleicher Reihenfolge (`reihenfolge` = „statisch“ oder „gewichtet“), Median je Größe aus den Messreihen."""
    k_ohne, k_mit = ("ohne_stat", "mit_stat") if reihenfolge == "statisch" else ("ohne_gew", "mit_gew")
    teile, faktoren = [], []
    for z in zeilen:
        f = verhaeltnis(z[k_ohne]["median"], z[k_mit]["median"])
        faktoren.append(f)
        teile.append(f"{_gr(z['groesse'])}: {zahl(z[k_ohne]['median'])} → {zahl(z[k_mit]['median'])} ({faktor_text(f)})")
    unter = [_gr(z["groesse"]) for z, f in zip(zeilen, faktoren) if f < C.GLEICHAUF_FAKTOR]
    schritte = sum(1 for a, b in zip(faktoren, faktoren[1:]) if b > a)
    abbr_ohne = sum(z[k_ohne]["abbrueche"] for z in zeilen)
    abbr_mit = sum(z[k_mit]["abbrueche"] for z in zeilen)
    n_inst = sum(z["n"] for z in zeilen)
    text = (f"Median der Konflikte ohne → mit Lernen ({reihenfolge}e Reihenfolge, {len(zeilen)} Größen): " + "; ".join(teile) + ". "
            f"Abbrüche am Budget: {abbr_ohne} ohne, {abbr_mit} mit Lernen (von je {n_inst} Läufen). ")
    if not unter:
        text += (f"In allen {len(zeilen)} Größen liegt der Faktor bei mindestens {faktor_text(min(faktoren))}; er wächst von einer Größe zur nächsten in {schritte} von {len(zeilen) - 1} Schritten.")
        return "success", text
    if len(unter) == len(zeilen):
        text += f"In keiner Größe erreicht der Abstand den Faktor {_gl()}: Lernen und Nichtlernen sind hier gleichauf."
        return "warning", text
    text += (f"Den Faktor {_gl()} erreicht der Abstand nicht bei {', '.join(unter)}; in den übrigen Größen liegt er bei mindestens "
             f"{faktor_text(min(f for f in faktoren if f >= C.GLEICHAUF_FAKTOR))}. Von einer Größe zur nächsten wächst er in {schritte} von {len(zeilen) - 1} Schritten.")
    return "info", text


def verdict_gewichtung(zeilen) -> tuple[str, str]:
    """Konfliktgewichtung ohne Lernen gegen festes Lernen: holt sie auf?"""
    teile = []
    erreicht = 0
    for z in zeilen:
        f_gew = verhaeltnis(z["ohne_stat"]["median"], z["ohne_gew"]["median"])
        f_lern = verhaeltnis(z["ohne_stat"]["median"], z["mit_stat"]["median"])
        if verhaeltnis(z["ohne_gew"]["median"], z["mit_stat"]["median"]) < C.GLEICHAUF_FAKTOR:
            erreicht += 1
        teile.append(f"{_gr(z['groesse'])}: Gewichtung {faktor_text(f_gew)}, Lernen {faktor_text(f_lern)}")
    text = ("Median der Konflikte ohne Lernen, statisch, geteilt durch den Median der Variante: " + "; ".join(teile) + ". "
            f"Die gewichtete Suche ohne Lernen kommt dem Lernen (statisch) bis auf den Faktor {_gl()} nahe in {erreicht} von {len(zeilen)} Größen.")
    return ("info" if erreicht < len(zeilen) else "warning"), text


def verdict_zugeschnitten(zeilen) -> tuple[str, str]:
    """Mini-CP (Stufe 2, Knoten) gegen die CNF mit Lernen (statisch, Konflikte): verschiedene Einheiten, nur die Größenordnung zählt; Schwelle `GLEICHAUF_FAKTOR`."""
    teile = []
    klar_mini = klar_lernen = gleich = 0
    for z in zeilen:
        mini, lern = z["mini2"]["median"], z["mit_stat"]["median"]
        if lern >= C.GLEICHAUF_FAKTOR * mini and lern > mini:
            klar_mini += 1
            urteil = "Mini-CP weniger"
        elif mini >= C.GLEICHAUF_FAKTOR * lern and mini > lern:
            klar_lernen += 1
            urteil = "Lernen weniger"
        else:
            gleich += 1
            urteil = "gleichauf"
        teile.append(f"{_gr(z['groesse'])}: {zahl(mini)} Knoten gegen {konflikte_text(lern)} ({urteil})")
    text = ("Mini-CP mit Schlupf-Heuristik und Disjunktiv-Propagation (Stufe 2, Median der Knoten) gegen dieselbe Aufgabe als CNF mit Lernen (statisch, Median der Konflikte): " + "; ".join(teile) + ". "
            f"Weniger Zähleinheiten hat das Mini-CP in {klar_mini} von {len(zeilen)} Größen, das Lernen in {klar_lernen}, gleichauf (Abstand unter dem Faktor {_gl()}) sind {gleich}. "
            "Knoten und Konflikte sind verschiedene Einheiten: nur die Größenordnung zählt.")
    return ("success" if klar_lernen == len(zeilen) else "info"), text


def verdict_instanz(row: dict, budget: int) -> tuple[str, str]:
    """Verdikt zu einer einzelnen Instanz („Makespan ≤ Optimum − 1“, unerfüllbar) aus `jobshop_lauf`."""
    def feld(k):
        return f"≥ {zahl(budget)} (Budget)" if row[k] is None else zahl(row[k])

    if row["wurzel_leer"]:
        return "warning", (f"Das Optimum {row['opt']} ist hier schon die längste Kette: Der Horizont {row['opt'] - 1} lässt einer Operation keinen Platz, die CNF enthält eine leere Klausel "
                           "und jede Variante beweist die Unerfüllbarkeit ohne Suche. An dieser Instanz gibt es nichts zu lernen.")
    werte = [row[v] for v in VARIANTEN]
    if all(w is not None and w <= 1 for w in werte):
        return "warning", (f"Die Einheitspropagation beweist „Makespan ≤ {row['opt'] - 1}“ hier schon mit höchstens einem Konflikt in jeder Variante: An dieser Instanz zeigt sich kein Unterschied zwischen "
                           "Lernen und Nichtlernen. Einen anderen Zufalls-Seed oder eine größere Aufgabe wählen.")
    text = (f"Optimum {row['opt']}, Aufgabe „Makespan ≤ {row['opt'] - 1}“ (unerfüllbar), {zahl(row['klauseln'])} Klauseln. Konflikte ohne Lernen: {feld('ohne_stat')} (statisch), {feld('ohne_gew')} (gewichtet); "
            f"mit Lernen: {feld('mit_stat')} (statisch), {feld('mit_gew')} (gewichtet). Standard-CDCL (VSIDS, Neustarts): {feld('standard')}. Mini-CP: {feld('mini1')} Knoten (Stufe 1), {feld('mini2')} (Stufe 2).")
    return "info", text


def verdict_schubfach(zeilen, h: int) -> tuple[str, str]:
    """Schubfach: Kern-CDCL ohne Erklärung gegen CDCL mit Hall-Erklärung bei h, mit dem Hinweis, dass die Aufgabe eine einzige Hall-Verletzung ist."""
    z = next(r for r in zeilen if r["h"] == h)
    ohne_text = f"≥ {zahl(z['ohne_budget'])} (Budget)" if z.get("ohne_abgebrochen") else zahl(z["ohne"])
    echte = [r for r in zeilen if r["h"] <= h and not r.get("ohne_abgebrochen") and r["ohne"]]
    faktoren = [b["ohne"] / a["ohne"] for a, b in zip(echte, echte[1:])]
    wachs = ""
    if faktoren:
        wachs = f" Je zusätzlichem Loch wächst die Zahl um den Faktor {dezimal(min(faktoren))} bis {dezimal(max(faktoren))} (h = {echte[0]['h']} bis {echte[-1]['h']})."
    return "info", (f"Schubfach h = {h} ({h + 1} Tauben auf {h} Löcher): Der Kern-CDCL braucht {ohne_text} Konflikte, mit der Hall-Erklärung braucht die Suche {zahl(z['hall'])} "
                    f"(der Propagator meldet {z['hall_fehlschlaege']} Fehlschlag an der Wurzel, seine erklärte Klausel ist leer).{wachs} Das ist trivial im Sinn der Konstruktion: Das Schubfach ist eine einzige "
                    "Hall-Verletzung, die erklärte Klausel schließt sie an der Wurzel. Es zeigt, dass der Kern-CDCL hier mit jedem Loch mehr Konflikte braucht und die Hall-Erklärung keine, nicht, dass Lazy Clause Generation allgemein schneller wäre.")


def verdict_klausel(p, klausel_text: str, zu_stark: bool = False) -> tuple[str, str]:
    """Verdikt der Einzelprüfung einer Klausel (`lcg_algorithm.Pruefung`)."""
    vor = "Die absichtlich zu starke Klausel " if zu_stark else "Die Klausel "
    if p.urteil == "gueltig":
        return "success", f"{vor}„{klausel_text}“ ist **gültig**: CNF plus ihre Verneinung ist unerfüllbar (Kern-CDCL, {konflikte_text(p.konflikte)}, Budget {zahl(p.budget)})."
    if p.urteil == "ungueltig":
        return "error", (f"{vor}„{klausel_text}“ ist **ungültig**: Die CNF hat ein Modell, das sie verletzt (Gegenbeispiel unten; Kern-CDCL, {konflikte_text(p.konflikte)}). "
                         "Ein Propagator, der so einen Schluss erklärt, würde Lösungen abschneiden.")
    return "warning", f"{vor}„{klausel_text}“: **unentschieden**, das Budget von {zahl(p.budget)} Konflikten reichte nicht für die Prüfung."


def _menge(namen, idx) -> str:
    n = [namen[i] for i in idx]
    return n[0] if len(n) == 1 else ", ".join(n[:-1]) + " und " + n[-1]


def _werte(ws) -> str:
    return "{" + ", ".join(str(w) for w in ws) + "}"


def h1_schritt_text(e: dict, namen=S.H1_NAMEN) -> str:
    """Satz zu einem Ereignis von `hall_schritte` (Handbeispiel H1)."""
    art = e["art"]
    if art == "start":
        zeilen = "; ".join(f"{namen[i]} ∈ {_werte(d)}" for i, d in enumerate(e["doms"]))
        return f"Ausgangszustand: {zeilen}. Alle drei Werte müssen verschieden sein."
    if art == "entscheidung":
        return f"Entscheidung: {namen[e['var']]} ≠ {e['wert']} (der Wert {e['wert']} fällt aus {namen[e['var']]})."
    if art == "streichung":
        mehr = [(i, w) for i, w, pos in e["klausel"] if pos]
        sonst = " oder ".join(f"{namen[i]} = {w}" for i, w in mehr) or "(gar nicht)"
        return (f"{_menge(namen, e['menge'])} teilen sich die Werte {_werte(e['werte'])} (so viele Werte wie Variablen), also fällt {e['wert']} aus {namen[e['var']]}. "
                f"Sonst müsste eine dieser Variablen einen Wert außerhalb von {_werte(e['werte'])} haben, das heißt: {sonst}.")
    if art == "fixpunkt":
        fest = [f"{namen[i]} = {d[0]}" for i, d in enumerate(e["doms"]) if len(d) == 1]
        return "Fixpunkt: Der Propagator findet nichts mehr zu streichen." + (f" Festgelegt: {', '.join(fest)}." if fest else "")
    return "Fehlschlag: Keine vollständige Zuordnung der Werte mehr möglich."


def verdict_h1(a: dict, namen=S.H1_NAMEN) -> tuple[str, str]:
    """Verdikt des Handbeispiels H1: Aufzählung gegen Propagator (alles aus der Aufzählung und den Schritten abgeleitet)."""
    x, w = S.H1_ENTSCHEIDUNG
    rest = a["nach_entscheidung"]
    fest = a["schritte"][-1]["doms"]
    festgelegt = [i for i, d in enumerate(fest) if len(d) == 1 and len({l[i] for l in rest}) == 1]
    gleich = [f"{namen[i]} = {fest[i][0]}" for i in festgelegt]
    nr = sum(1 for s in a["schritte"] if s["art"] == "streichung")
    text = (f"Die Aufzählung findet {len(a['alle'])} Lösungen, nach {namen[x]} ≠ {w} bleiben {len(rest)}. Der Propagator zieht {nr} Schlüsse und legt fest: {', '.join(gleich) if gleich else 'nichts'}; "
            "die Aufzählung bestätigt jeden dieser Werte in allen verbleibenden Lösungen. Der Propagator braucht dazu keine Aufzählung, er argumentiert mit der Hall-Menge.")
    ok = all(fest[i][0] == l[i] for l in rest for i in festgelegt)
    return ("success" if ok and gleich else "warning"), text


def verdict_h2(a: dict) -> tuple[str, str]:
    """Verdikt des Handbeispiels H2 bei Horizont `a["H"]`: Aufzählung der Pläne, Reihenfolgen, die in allen Plänen gelten, und was die Wurzelpropagation der CNF davon findet."""
    kod, H, n = a["kod"], a["H"], len(a["plaene"])
    nm = S.op_name_h2
    if n == 0:
        warum = "die CNF enthält schon beim Bau eine leere Klausel" if kod.leer else "die Einheitspropagation der CNF endet an der Wurzel im Widerspruch" if a["wurzel"] is None else "die CNF ist unerfüllbar"
        return "warning", f"Bei Horizont {H} gibt es keinen Plan (Aufzählung: 0 Pläne); {warum}."
    fest = [(p, v) for p, v in a["paare_aufzaehlung"].items() if v is not None]
    saetze = [f"{nm(p[0]) if v else nm(p[1])} vor {nm(p[1]) if v else nm(p[0])}" for p, v in fest]
    gefunden = sum(1 for p, v in fest if a["paare_wurzel"].get(p) == v)
    plaene = "1 Plan" if n == 1 else f"{n} Pläne"
    if not fest:
        return "info", f"Bei Horizont {H} gibt es {plaene}; in keinem der beiden Maschinenpaare gilt eine Reihenfolge in allen Plänen, die Wurzel der CNF legt nichts fest."
    gilt = "Im einzigen Plan" if n == 1 else f"In allen {n}"
    return "info", (f"Bei Horizont {H} gibt es {plaene} (Aufzählung). {gilt} gilt: {' und '.join(saetze)}. "
                    f"Die Einheitspropagation der CNF legt davon {gefunden} von {len(fest)} schon an der Wurzel fest (Stufe 0, ohne Suche).")


def verdict_pruefbilanz(familien) -> tuple[str, str]:
    """Bilanz der Einzelprüfungen aus der Messreihe: Zahl geprüft, gültig, ungültig, unentschieden."""
    g = sum(f["geprueft"] for f in familien)
    ok = sum(f["gueltig"] for f in familien)
    bad = sum(f["ungueltig"] for f in familien)
    offen = sum(f["unentschieden"] for f in familien)
    text = f"Einzeln gegen die CNF geprüft: {zahl(g)} Klauseln in {len(familien)} Familien, davon {zahl(ok)} gültig, {zahl(bad)} ungültig, {zahl(offen)} unentschieden."
    return ("error" if bad else "success"), text
