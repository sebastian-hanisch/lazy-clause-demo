"""Lazy Clause Generation – ein Propagator erklärt seinen Schluss - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Ein CDCL-Löser (Konfliktlernen aus Stück 1 der Reihe) mit einem Constraint-Propagator, der zu jedem Schluss eine Klausel liefert, vier Experimente.
Aufwand wird in Konflikten (CNF) beziehungsweise Knoten (Mini-CP) gezählt, nie in Sekunden. Quelle des Verfahrens: nur Abstract gelesen (siehe 📐).

Lauffähig mit: streamlit run app.py
"""

import time

import pandas as pd
import streamlit as st

import lcg_algorithm as A
import lcg_constants as C
import lcg_evaluation as E
import lcg_kodierung as K
import lcg_scenario as S
import lcg_visualization as V
from lcg_minicp import entscheide
from lcg_layout import dunkles_design, kopf_css
from lcg_presets import (
    SETTING_SPECS,
    bounds,
    aktueller_wert,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sidebar_presets,
    stash_kept_widget_state,
    sync_query_params,
)

st.set_page_config(page_title="Lazy Clause Generation – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _messreihen():
    return E.lade_messreihen()


@st.cache_data(show_spinner=False)
def _h1():
    return E.h1_analyse()


@st.cache_data(show_spinner=False)
def _h2(horizont):
    return E.h2_analyse(horizont)


@st.cache_data(show_spinner=False)
def _schubfach_live(h_max):
    t0 = time.perf_counter()
    return [E.schubfach_lauf(h) for h in range(C.H_MIN, h_max + 1)], time.perf_counter() - t0


@st.cache_data(show_spinner=False)
def _jobshop(groesse, seed, budget):
    t0 = time.perf_counter()
    inst = S.jobshop_instanz(groesse, seed)
    return E.jobshop_lauf(inst, budget, C.MESS_BUDGET_MINICP), time.perf_counter() - t0


@st.cache_data(show_spinner=False)
def _spur(groesse, seed, reihenfolge, budget):
    inst = S.jobshop_instanz(groesse, seed)
    opt, _ = S.optimum(inst)
    kod = K.kodiere_jobshop([list(j) for j in inst.jobs], opt - 1)
    return kod, E.lernspur(kod, True, reihenfolge, budget)


@st.cache_data(show_spinner=False)
def _live_reihe(groesse, budget):
    t0 = time.perf_counter()
    laeufe = [E.jobshop_lauf(S.jobshop_instanz(groesse, seed), budget, C.MESS_BUDGET_MINICP, mit_standard=True) for seed in C.MESS_SEEDS]
    return laeufe, time.perf_counter() - t0


def _tabelle(daten, spalten):
    st.dataframe(pd.DataFrame(daten, columns=spalten), hide_index=True, width="stretch")


def _bereich(wert, budget):
    return f"≥ {E.zahl(budget)}" if wert is None else E.zahl(wert)


def _verteilung_text(v):
    """Median (Maximum, Abbrüche) einer Verteilung aus `E.verteilung`."""
    text = f"{E.zahl(v['median'])} (Max {E.zahl(v['max'])}"
    return text + (f", {v['abbrueche']} Abbr." if v["abbrueche"] else "") + ")"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in lcg_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🧠 Lazy Clause Generation – ein Propagator erklärt seinen Schluss")
st.markdown(
    """
**Ein Constraint-Propagator, der zu jedem Schluss eine Klausel mitliefert („warum gilt das?“), kann aus dem Suchbaum eine Lernmaschine machen:** Aus einem Fehlschlag lässt sich dann eine Regel ableiten, die spätere Äste sperrt.
Die Demo setzt den Konfliktlern-Mechanismus aus Stück 1 der Reihe mit den **Propagatoren** aus Stück 10 (AllDifferent) und Stück 11 (Job Shop) zusammen und prüft, was das Lernen dabei bringt (gemessen wird das Klausellernen in der Order-Kodierung des Job Shops, dort ohne erklärenden Propagator):
Der Gewinn des Lernens ist hier gegen eine **gleich schwache Suche** gemessen, **nicht** gegen eine auf das Problem **zugeschnittene** Suche. Aufwand zählt in **Konflikten** (CNF) beziehungsweise **Knoten** (Mini-CP), nie in Sekunden.
Die Quelle des Verfahrens (Ohrimenko, Stuckey, Codish 2009) ist nur im Abstract gelesen: Die Demo beschreibt den Mechanismus und ihre eigene Messung, nicht die Arbeit.

Weiter unten: vier Experimente (Auswahl), **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert Lazy Clause Generation", expanded=True):
    st.markdown(
        """
1. **Der Löser sucht und lernt.** Ein CDCL-Löser belegt Variablen, schließt per Einheitspropagation und lernt aus jedem Konflikt eine Klausel (Stück 1).
2. **Ein Propagator ist ein Stück Constraint-Wissen.** Er sieht Domänen (hier: AllDifferent über Variablen mit Wertemengen) und streicht Werte, die in keiner Lösung vorkommen können.
3. **Er erklärt seinen Schluss als Klausel.** Zu jeder Streichung gehört eine Klausel, die aus den Anfangsdomänen folgt: „x3 ≠ 1 ∨ x1 = 3“. Sie wird **erst beim Gebrauch** erzeugt („lazy“), nicht vorab für alle Möglichkeiten.
4. **Warum das funktioniert:** Die Klausel macht den Schluss für den Löser zu gewöhnlichem Wissen: Konfliktanalyse und Rücksprung arbeiten wie bisher, und das Gelernte gilt in allen späteren Ästen.

Im Job Shop gibt es keinen Propagator mit Erklärung in dieser Demo: Dort steckt die Struktur in der **Order-Kodierung** (Variable „Operation o beginnt spätestens zur Zeit t“), und die CNF wird vorab vollständig gebaut. Das Experiment 3 trennt deshalb nur das **Lernen** (an oder aus) bei sonst gleicher Suche.
        """
    )

load_permalink_settings()
init_session_state_defaults()
st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Job-Shop-Instanz** (Experimente 3 und 4)")
    groesse = st.slider("Größe (Aufträge = Maschinen)", *bounds("groesse_slider"), key="groesse_slider",
                        help="Quadratischer Job Shop mit Dauern 1 bis 9. Gilt in den Experimenten 3 und 4; die Messreihen darunter zeigen immer alle gemessenen Größen.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1,
                           help="Bestimmt die Instanz (SplitMix64). Gilt in den Experimenten 3 und 4.")
    st.button("🎲 Neuer Zufalls-Seed", width="stretch", on_click=randomize_seed)
    st.markdown("**Rechenbudget**")
    budget = st.select_slider("Konfliktbudget der Live-Läufe", options=C.BUDGET_OPTIONEN, key="budget_slider",
                              help="Nach so vielen Konflikten bricht ein Lauf ab; das Ergebnis heißt dann „mindestens“ so viele Konflikte. Gilt in den Experimenten 3 und 4.")

daten = _messreihen()
zeilen = E.groessen_zeilen(daten)
meta = daten["meta"]

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Was bringt das Lernen, und gegen welche Suche?")
letzte = zeilen[-1]
m1, m2, m3 = st.columns(3)
m1.metric(f"ohne Lernen, {letzte['groesse']} × {letzte['groesse']} (Median Konflikte)", E.zahl(letzte["ohne_stat"]["median"]), delta="Referenz", delta_color="off")
f_lern = E.verhaeltnis(letzte["ohne_stat"]["median"], letzte["mit_stat"]["median"])
m2.metric("mit Lernen (Median Konflikte)", E.zahl(letzte["mit_stat"]["median"]), delta=f"{E.faktor_text(f_lern)} weniger", delta_color="off")
m3.metric("Mini-CP Stufe 2 (Median Knoten)", E.zahl(letzte["mini2"]["median"]), delta="andere Einheit", delta_color="off")
kind, text = E.verdict_lernen(zeilen, "statisch")
getattr(st, kind)(text)
st.caption(f"Vorgerechnet mit `{meta['skript']}` am {meta['datum']} (nicht live): je Größe die Zufalls-Seeds {meta['seeds'][0]} bis {meta['seeds'][-1]}, Entscheidung „Makespan ≤ Optimum − 1“ (unerfüllbar), "
           f"Budget {E.zahl(meta['budget_cnf'])} Konflikte. Zu den Zählern: Kern-CDCL ohne Neustarts und ohne VSIDS, gleiche Wertregel („wahr“ zuerst), nur Lernen und Reihenfolge variieren.")

st.markdown("---")

experiment = st.radio("Experiment", C.EXPERIMENTE, key="experiment_radio", horizontal=True)

# =============================================================================================================================================
# Experiment 1
# =============================================================================================================================================
if experiment == C.EXPERIMENTE[0]:
    st.subheader("🔬 Eine Erklärung von Hand")
    st.caption("Zu jedem Schluss eines Propagators gehört eine Klausel. Der Knopf „Klausel prüfen“ fragt den Kern-CDCL: Ist CNF plus verneinte Klausel unerfüllbar? Dann folgt die Klausel aus der CNF.")
    seed_widget("beispiel_radio")
    beispiel = st.radio("Beispiel", C.BEISPIELE, key="beispiel_radio", horizontal=True)
    seed_widget("zu_stark_toggle")
    zu_stark = st.toggle("Ungültige Klausel einschleusen (Demonstration)", key="zu_stark_toggle",
                         help="Ersetzt die erklärte Klausel durch eine zu starke: bei H1 ohne ihre Bedingung, bei H2 mit umgekehrter Reihenfolge. Die Prüfung muss sie fangen.")

    if beispiel == C.BEISPIELE[0]:
        a = _h1()
        kod = a["kod"]
        ereignisse = a["schritte"]
        kind, text = E.verdict_h1(a)
        getattr(st, kind)(text)
        st.markdown("**Aufgabe H1:** x1 ∈ {1, 2, 3}, x2 ∈ {1, 2}, x3 ∈ {1, 2, 3}, alle drei verschieden; die Entscheidung heißt x1 ≠ 3.")
        schritt = st.slider("Schritt", 0, len(ereignisse) - 1, 0, key="schritt_h1", help="0 = Ausgangszustand; jeder Schritt wendet das nächste Ereignis an.")
        e = ereignisse[schritt]
        vor = ereignisse[max(0, schritt - 1)]["doms"]
        links, rechts = st.columns([3, 2])
        with links:
            st.plotly_chart(V.build_matrix(S.H1_NAMEN, [set(d) for d in S.H1_DOMAENEN], [set(d) for d in vor], [set(d) for d in e["doms"]]), width="stretch", key="matrix_h1")
            st.caption("Hellgrün: Wert in der Domäne. Rot ✗: in diesem Schritt gestrichen. Dunkelgrün ✓: Variable festgelegt. Grau: Wert nie in der Anfangsdomäne.")
        with rechts:
            st.markdown(f"**Schritt {schritt}:** " + E.h1_schritt_text(e))
            if e["art"] == "streichung":
                st.markdown("**Erklärungsklausel:** `" + A.klausel_text(e["klausel"]) + "`")
        with st.expander("Alle Schlüsse mit Erklärungsklausel"):
            for i, ev in enumerate(ereignisse):
                if ev["art"] == "streichung":
                    st.markdown(f"{i}. {E.h1_schritt_text(ev)} Klausel: `{A.klausel_text(ev['klausel'])}`")
        with st.expander("Aufzählung der Lösungen (unabhängige Probe)"):
            _tabelle([[f"({', '.join(map(str, l))})", "ja" if l[S.H1_ENTSCHEIDUNG[0]] != S.H1_ENTSCHEIDUNG[1] else "nein"] for l in a["alle"]],
                     ["Lösung (x1, x2, x3)", f"erfüllt die Entscheidung x1 ≠ {S.H1_ENTSCHEIDUNG[1]}"])

        streichungen = [ev for ev in ereignisse if ev["art"] == "streichung"]
        st.markdown("**Klausel prüfen**")
        wahl = st.selectbox("Welche Klausel?", range(len(streichungen)), key="klausel_h1",
                            format_func=lambda i: A.klausel_text(streichungen[i]["klausel"]), help="Die Erklärungsklauseln der Schlüsse oben.")
        klausel = streichungen[wahl]["klausel"]
        geprueft = [(i, w, pos) for i, w, pos in (A.erklaerungsklausel([set(d) for d in S.H1_DOMAENEN], streichungen[wahl]["var"], streichungen[wahl]["wert"], streichungen[wahl]["menge"], set(streichungen[wahl]["werte"])))]
        if zu_stark:
            geprueft = [(i, w, pos) for i, w, pos in geprueft[:1]]
        text_klausel = A.klausel_text(geprueft)
        schluessel = ("h1", tuple(geprueft))
        if st.button("🔍 Klausel prüfen", key="pruefe_h1"):
            st.session_state["pruefung"] = (schluessel, A.pruefe_klausel(kod.n_var, kod.klauseln, E.klausel_literale(kod, geprueft), C.KLAUSEL_PRUEF_BUDGET))
        erg = st.session_state.get("pruefung")
        if erg is None or erg[0] != schluessel:
            st.info(f"Zu prüfen: `{text_klausel}`. Mit „Klausel prüfen“ starten.")
        else:
            kind, text = E.verdict_klausel(erg[1], text_klausel, zu_stark)
            getattr(st, kind)(text)
            if erg[1].urteil == "ungueltig":
                belegung = tuple(next(w for (i2, w), v in kod.var.items() if i2 == i and erg[1].gegenbeispiel[v]) for i in range(len(S.H1_DOMAENEN)))
                st.markdown(f"Gegenbeispiel (eine Lösung der CNF, die die Klausel verletzt): (x1, x2, x3) = {belegung}.")
        loes = [l for l in a["alle"]]
        gilt = all(any((l[i] == w) == pos for i, w, pos in geprueft) for l in loes)
        st.caption(f"Unabhängige Probe durch Aufzählung: Die Klausel `{text_klausel}` gilt in {'allen' if gilt else 'nicht allen'} {len(loes)} Lösungen"
                   + ("." if gilt else f"; verletzt in {sum(1 for l in loes if not any((l[i] == w) == pos for i, w, pos in geprueft))} von {len(loes)}."))
    else:
        seed_widget("h2_horizont_radio")
        horizont = st.radio("Horizont H (Makespan ≤ H)", C.H2_HORIZONT_OPTIONEN, key="h2_horizont_radio", horizontal=True)
        a = _h2(horizont)
        kod = a["kod"]
        st.markdown("**Aufgabe H2:** Auftrag 1: a (Maschine 1, Dauer 2), dann b (Maschine 2, Dauer 1). Auftrag 2: c (Maschine 2, Dauer 2), dann d (Maschine 1, Dauer 1). Gesucht: ein Plan mit Makespan ≤ H.")
        kind, text = E.verdict_h2(a)
        getattr(st, kind)(text)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pläne (Aufzählung)", len(a["plaene"]))
        c2.metric("CNF: Variablen", kod.n_var)
        c3.metric("CNF: Klauseln", len(kod.klauseln))
        est, lst, d, mc, _ = K.fenster([list(j) for j in S.H2_JOBS], horizont, True)
        if all(lst[o] >= est[o] for o in range(len(d))):
            st.plotly_chart(V.build_fenster(S.H2_NAMEN, est, lst, d, horizont, mc), width="stretch", key="fenster_h2")
            st.caption("Fenster aus Kopf- und Schwanzdauern (nur Vorrang im Auftrag): hell der mögliche Bereich einer Operation, dunkel ihr Pflichtteil.")
        else:
            st.warning(f"Bei Horizont {horizont} passt der Auftrag nicht in den Horizont: ein Fenster ist leer, die CNF enthält eine leere Klausel.")
        if a["plaene"]:
            with st.expander(f"Alle {len(a['plaene'])} Pläne (Startzeiten von a, b, c, d)"):
                _tabelle([list(p) for p in a["plaene"]], list(S.H2_NAMEN))
        with st.expander("Handargument des Mini-CP (Stück 11, Stufe 1)"):
            ent = entscheide(S.H2_INSTANZ, horizont, 1, protokoll=True)
            if ent.protokoll is not None:
                for ev in ent.protokoll.ereignisse[:12]:
                    st.markdown(f"- {ev.text}")
            st.caption("Die Einträge sind Namen des Mini-CP: Operation (j,k) heißt dort Auftrag j, k-te Operation, von null gezählt: (0,0) = a, (0,1) = b, (1,0) = c, (1,1) = d.")
        if a["paare_wurzel"] or a["paare_aufzaehlung"]:
            st.markdown("**Klausel prüfen**")
            paare = [p for p, v in a["paare_aufzaehlung"].items() if v is not None] or list(a["paare_aufzaehlung"])
            wahl = st.selectbox("Welche Reihenfolge?", range(len(paare)), key="klausel_h2",
                                format_func=lambda i: f"{S.H2_NAMEN[paare[i][0]]} vor {S.H2_NAMEN[paare[i][1]]}" if a["paare_aufzaehlung"][paare[i]] is not False else f"{S.H2_NAMEN[paare[i][1]]} vor {S.H2_NAMEN[paare[i][0]]}",
                                help="Die Reihenfolgen, die in allen Plänen gelten (bei keinem festen Paar: beide Maschinenpaare).")
            p = paare[wahl]
            richtung = a["paare_aufzaehlung"][p] if a["paare_aufzaehlung"][p] is not None else True
            if zu_stark:
                richtung = not richtung
            klausel = E.paar_klausel(kod, p[0], p[1], richtung)
            text_klausel = kod.literal_text(klausel[0], S.op_name_h2)
            schluessel = ("h2", horizont, tuple(klausel))
            if st.button("🔍 Klausel prüfen", key="pruefe_h2"):
                st.session_state["pruefung"] = (schluessel, A.pruefe_klausel(kod.n_var, kod.klauseln, klausel, C.KLAUSEL_PRUEF_BUDGET))
            erg = st.session_state.get("pruefung")
            if erg is None or erg[0] != schluessel:
                st.info(f"Zu prüfen: Einheitsklausel `{text_klausel}`. Mit „Klausel prüfen“ starten.")
            else:
                kind, text = E.verdict_klausel(erg[1], text_klausel, zu_stark)
                getattr(st, kind)(text)
                if erg[1].urteil == "ungueltig":
                    plan = K.plan_aus_modell(kod, erg[1].gegenbeispiel)
                    st.markdown(f"Gegenbeispiel (ein Plan der CNF, der die Klausel verletzt): Startzeiten (a, b, c, d) = {tuple(plan)}.")
            gilt = all((pl[p[0]] + kod.d[p[0]] <= pl[p[1]]) == richtung for pl in a["plaene"])
            st.caption(f"Unabhängige Probe durch Aufzählung: `{text_klausel}` gilt in {'allen' if gilt else 'nicht allen'} {len(a['plaene'])} Plänen.")
        st.caption("Hinweis: Die Planung nahm an, der Löser lerne die beiden Einheitsklauseln aus Konflikten. Gemessen steht es anders: Die Einheitspropagation der CNF legt sie an der Wurzel schon fest, ohne Konflikt; "
                   "die Klauseln „a vor d“ und „c vor b“ sind dort Folgerungen der Kodierung.")

    bilanz = daten["pruefung"]
    with st.expander("Wie verlässlich sind die Erklärungen? Vorgerechnete Einzelprüfung (nicht live)"):
        kind, text = E.verdict_pruefbilanz(bilanz)
        getattr(st, kind)(text)
        _tabelle([[f["familie"], f["instanzen"], f["geprueft"], f["gueltig"], f["ungueltig"], f["unentschieden"]] for f in bilanz],
                 ["Familie", "Instanzen", "geprüft", "gültig", "ungültig", "unentschieden"])
        st.caption(f"Jede Klausel einzeln: CNF plus verneinte Klausel mit dem Kern-CDCL, Budget {E.zahl(C.KLAUSEL_PRUEF_BUDGET)} Konflikte (`{meta['skript']}`, {meta['datum']}). "
                   "Nur Hall-Erklärungen für AllDifferent und gelernte Klauseln des Job-Shop-CDCL sind geprüft; für Disjunktiv- oder Kumulativ-Propagatoren mit Erklärung gibt es in dieser Demo keinen Nachbau, also keine Prüfung.")

# =============================================================================================================================================
# Experiment 2
# =============================================================================================================================================
elif experiment == C.EXPERIMENTE[1]:
    st.subheader("🔬 Schubfach mit und ohne Erklärung")
    st.caption("h + 1 Tauben auf h Löcher, jede Taube in genau einem Loch, jedes Loch höchstens eine Taube: unerfüllbar. Der Kern-CDCL braucht dafür mit jedem Loch mehr Konflikte; "
               "mit dem Hall-Propagator (er erklärt seinen Schluss als Klausel) steht die Unerfüllbarkeit an der Wurzel.")
    seed_widget("h_slider")
    h = st.slider("h (Zahl der Löcher)", *bounds("h_slider"), key="h_slider", help=f"Die Tabelle zeigt alle h von {C.H_MIN} bis zu diesem Wert; ab h = {C.LIVE_H_MAX + 1} ist der Lauf ohne Erklärung vorgerechnet.")
    bis = min(h, C.LIVE_H_MAX)
    with st.spinner(f"Rechne h = {C.H_MIN} bis {bis} …"):
        live, sek = _schubfach_live(bis)
    zeilen_s = [dict(r, herkunft="live") for r in live]
    if h > C.LIVE_H_MAX:
        zeilen_s += [dict(r, herkunft="vorgerechnet") for r in daten["schubfach"] if C.LIVE_H_MAX < r["h"] <= h]
    kind, text = E.verdict_schubfach(zeilen_s, h)
    getattr(st, kind)(text)
    _tabelle([[r["h"], r["variablen"], r["klauseln"], E.zahl(r["ohne"]) if not r.get("ohne_abgebrochen") else f"≥ {E.zahl(r['ohne'])}", E.zahl(r["hall"]), r["hall_fehlschlaege"], r["herkunft"]] for r in zeilen_s],
             ["h", "Variablen", "Klauseln", "Konflikte Kern-CDCL", "Konflikte mit Hall-Erklärung", "Fehlschläge des Propagators", "Herkunft"])
    st.plotly_chart(V.build_schubfach(zeilen_s), width="stretch", key="schubfach_chart")
    st.caption("0 Konflikte stehen auf der logarithmischen Achse als Punkt am unteren Rand. Zeile „vorgerechnet“: "
               f"`{meta['skript']}`, {meta['datum']}, nicht live. Die Konflikte der Suche zählen nur Konflikte der Schleife; den Fehlschlag, den der Propagator an der Wurzel selbst meldet, zeigt die Spalte daneben.")
    with st.expander("Die erklärte Klausel"):
        st.markdown(f"Der Propagator ordnet die {h + 1} Tauben den {h} Löchern zu (Matching): Es gelingt höchstens {h}. Die nicht zuordenbare Taube und alles, was von ihr aus erreichbar ist, bilden die Menge S "
                    f"(alle {h + 1} Tauben), die Vereinigung ihrer Domänen V sind die {h} Löcher. Die erklärte Klausel verlangt, dass mindestens eine Taube aus S ein Loch **außerhalb** von V hat: "
                    "Das gibt es nicht, die Klausel ist leer, und eine leere Klausel ist ein Beweis der Unerfüllbarkeit.")
    st.warning("**Das ist trivial im Sinn der Konstruktion:** Das Schubfach ist eine einzige Hall-Verletzung, die erklärte Klausel schließt sie an der Wurzel. Das zeigt, dass der Kern-CDCL auf dem Schubfach mit jedem Loch mehr Konflikte braucht (Faktor 4,0 bis 6,3 je Loch in der Messreihe), die Hall-Erklärung dagegen keine; "
               "es ist kein Maß dafür, wie viel Lazy Clause Generation auf anderen Aufgaben bringt (Experiment 3 und 4).")

# =============================================================================================================================================
# Experiment 3
# =============================================================================================================================================
elif experiment == C.EXPERIMENTE[2]:
    st.subheader("🔬 Job Shop: Lernen aus oder an")
    st.caption("Dieselbe CNF (Order-Kodierung), dieselbe Einheitspropagation, dieselbe Wertregel, Entscheidungen nur auf den Reihenfolgevariablen; "
               "variiert werden nur das Lernen (aus = chronologisches Zurückspringen, an = 1-UIP mit Rücksprung) und die Reihenfolge. Größe, Zufalls-Seed und Budget stehen in der Seitenleiste.")
    seed_widget("reihenfolge_radio")
    reihenfolge = st.radio("Reihenfolge für Verdikt, Kastendiagramm und Lernspur", C.REIHENFOLGEN, key="reihenfolge_radio", horizontal=True,
                           help="statisch: kleinste Variablennummer zuerst. gewichtet: jede Entscheidungsvariable in der Gründe-Wolke eines Konflikts bekommt +1 (Konfliktgewicht, nicht dom/wdeg).")
    st.markdown(f"**Einzelinstanz: {groesse} × {groesse}, Zufalls-Seed {int(seed)}** (live gerechnet)")
    with st.spinner(f"Rechne die Varianten (bis zu {E.zahl(budget)} Konflikte je Lauf) …"):
        row, sek = _jobshop(groesse, int(seed), budget)
    cols = st.columns(4)
    for col, v in zip(cols, E.VARIANTEN):
        col.metric(E.VARIANTEN_NAMEN[v], _bereich(row[v], budget), delta="Referenz" if v == "ohne_stat" else None, delta_color="off")
    kind, text = E.verdict_instanz(row, budget)
    getattr(st, kind)(text)
    werte = {E.VARIANTEN_NAMEN[v]: (budget if row[v] is None else row[v]) for v in E.VARIANTEN}
    st.plotly_chart(V.build_balken(werte, "Konflikte (logarithmisch)", {E.VARIANTEN_NAMEN[v]: E.VARIANTEN_FARBEN[v] for v in E.VARIANTEN}, [E.VARIANTEN_NAMEN[v] for v in E.VARIANTEN if row[v] is None]),
                    width="stretch", key="balken_instanz")
    st.caption(f"Rechenzeit der Einzelinstanz: {sek:.1f} s (nur Anzeige, kein Befund). Optimum nach dem Mini-CP{'' if row['optimum_bewiesen'] else ' (nicht bewiesen, obere Schranke)'}.")

    if not row["wurzel_leer"]:
        kod, spur = _spur(groesse, int(seed), reihenfolge, budget)
        ops = S.op_name_allgemein(S.jobshop_instanz(groesse, int(seed)))
        if spur["laengen"]:
            with st.expander(f"Lernspur: die gelernten Klauseln (mit Lernen, {reihenfolge})"):
                st.plotly_chart(V.build_laenge(spur["laengen"]), width="stretch", key="laenge_spur")
                st.caption(f"{E.zahl(len(spur['laengen']))} gelernte Klauseln in {E.zahl(spur['konflikte'])} Konflikten" + (" (Spur auf die ersten Ereignisse gekürzt)." if spur["gekuerzt"] else "."))
                n_z = len(spur["gelernt"])
                wahl = st.selectbox("Gelernte Klausel", range(n_z), key="gelernt_select", format_func=lambda i: f"{i + 1}. Klausel ({len(spur['gelernt'][i][0])} Literale)")
                lits, rueck, lbd = spur["gelernt"][wahl]
                st.markdown("`" + " ∨ ".join(kod.literal_text(l, ops) for l in lits) + f"` (Rücksprung auf Stufe {rueck}, {lbd} Entscheidungsstufen in der Klausel)")
                schluessel = ("jobshop", groesse, int(seed), reihenfolge, budget, wahl)
                if st.button("🔍 Klausel prüfen", key="pruefe_lern"):
                    st.session_state["pruefung_lern"] = (schluessel, A.pruefe_klausel(kod.n_var, kod.klauseln, lits, C.KLAUSEL_PRUEF_BUDGET))
                erg = st.session_state.get("pruefung_lern")
                if erg is not None and erg[0] == schluessel:
                    kind, text = E.verdict_klausel(erg[1], "gelernte Klausel")
                    getattr(st, kind)(text)

    st.markdown("**Messreihe (vorgerechnet, nicht live)**")
    kind, text = E.verdict_lernen(zeilen, reihenfolge)
    getattr(st, kind)(text)
    k_ohne, k_mit = ("ohne_stat", "mit_stat") if reihenfolge == "statisch" else ("ohne_gew", "mit_gew")
    kasten = {g: {"ohne": [(meta["budget_cnf"] if i[k_ohne] is None else i[k_ohne]) for i in daten["jobshop"][str(g)]],
                  "mit": [(meta["budget_cnf"] if i[k_mit] is None else i[k_mit]) for i in daten["jobshop"][str(g)]]} for g in sorted(int(x) for x in daten["jobshop"])}
    st.plotly_chart(V.build_kasten(kasten), width="stretch", key="kasten_lernen")
    st.caption(f"Je Größe {len(meta['seeds'])} feste Zufalls-Seeds ({meta['seeds'][0]} bis {meta['seeds'][-1]}), Abbrüche am Budget von {E.zahl(meta['budget_cnf'])} Konflikten liegen am oberen Rand. "
               "Median, Kasten (Viertelwerte) und alle Einzelwerte; 0 Konflikte stehen als 0,5.")
    _tabelle([[f"{z['groesse']} × {z['groesse']}", z["n"], _verteilung_text(z["ohne_stat"]), _verteilung_text(z["ohne_gew"]), _verteilung_text(z["mit_stat"]), _verteilung_text(z["mit_gew"]), _verteilung_text(z["standard"]),
               E.zahl(z["wurzel"])] for z in zeilen],
             ["Größe", "Instanzen", "ohne Lernen, statisch", "ohne Lernen, gewichtet", "mit Lernen, statisch", "mit Lernen, gewichtet", "Standard-CDCL", "Instanzen mit leerer Klausel (kein Suchen)"])
    st.caption("Median der Konflikte (Maximum, Zahl der Abbrüche am Budget). Standard-CDCL: VSIDS, Luby-Neustarts, Phasenspeicher, Entscheidungen auf allen Variablen (ein zusätzlicher Hebel, kein Teil der Gegenüberstellung).")

    with st.expander("Die vier Varianten"):
        st.markdown(
            """
| Variante | Lernen | Reihenfolge der Entscheidungen |
|---|---|---|
| ohne Lernen, statisch | chronologisches Zurückspringen: die letzte Entscheidung umdrehen, keine Klauseln | kleinste Variablennummer zuerst |
| ohne Lernen, gewichtet | wie oben | größtes Konfliktgewicht zuerst (+1 für jede Entscheidungsvariable in der Gründe-Wolke eines Konflikts) |
| mit Lernen, statisch | 1-UIP-Klausel, Rücksprung, keine Neustarts, kein VSIDS | kleinste Variablennummer zuerst |
| mit Lernen, gewichtet | wie oben | wie die gewichtete Reihenfolge oben |

Alle vier: dieselbe CNF, dieselbe Einheitspropagation, immer zuerst „wahr“, Entscheidungen nur auf den Reihenfolgevariablen „a vor b“.
            """
        )

    st.markdown("**Messreihe live nachrechnen**")
    if groesse > C.LIVE_MESS_GROESSE_MAX:
        st.caption(f"Die Live-Messreihe rechnet bis Größe {C.LIVE_MESS_GROESSE_MAX} × {C.LIVE_MESS_GROESSE_MAX}; bei größeren Instanzen sind nur die vorgerechneten Werte oben verfügbar.")
    else:
        st.caption(f"Rechnet die {len(C.MESS_SEEDS)} festen Zufalls-Seeds der Größe {groesse} × {groesse} mit dem Konfliktbudget der Seitenleiste (je Instanz vier Varianten, Standard-CDCL und Mini-CP).")
        if st.button("▶ Messreihe rechnen", key="live_reihe"):
            with st.spinner(f"Rechne {len(C.MESS_SEEDS)} Instanzen der Größe {groesse} × {groesse} …"):
                st.session_state["live_ergebnis"] = ((groesse, budget), *_live_reihe(groesse, budget))
        erg = st.session_state.get("live_ergebnis")
        if erg is not None and erg[0] == (groesse, budget):
            z_live = E.zeile_aus_laeufen(groesse, erg[1], budget, C.MESS_BUDGET_MINICP)
            kind, text = E.verdict_lernen([z_live], reihenfolge)
            getattr(st, kind)(text)
            st.caption(f"Live gerechnet in {erg[2]:.1f} s (nur Anzeige, kein Befund); Budget {E.zahl(budget)} Konflikte.")

# =============================================================================================================================================
# Experiment 4
# =============================================================================================================================================
else:
    st.subheader("🔬 Gegen die zugeschnittene Suche")
    st.caption("Dieselbe Aufgabe im Mini-CP aus Stück 11 (Zeitfenster, Paar-Test, Edge-Finding, Verzweigung auf das Paar mit dem kleinsten Spielraum) und in der CNF mit Lernen. "
               "Das Mini-CP kennt die Struktur (Paare, Fenster); die CNF muss sie aus Klauseln herleiten. Knoten und Konflikte sind verschiedene Einheiten: nur die Größenordnung zählt.")
    st.markdown(f"**Einzelinstanz: {groesse} × {groesse}, Zufalls-Seed {int(seed)}** (live gerechnet)")
    with st.spinner(f"Rechne die Verfahren (bis zu {E.zahl(budget)} Konflikte je Lauf) …"):
        row, sek = _jobshop(groesse, int(seed), budget)
    werte = {"Mini-CP Stufe 1 (Knoten)": row["mini1"], "Mini-CP Stufe 2 (Knoten)": row["mini2"], "CNF mit Lernen, statisch": row["mit_stat"], "CNF mit Lernen, gewichtet": row["mit_gew"],
             "CNF ohne Lernen, gewichtet": row["ohne_gew"], "Standard-CDCL": row["standard"]}
    abgebr = [n for n, w in werte.items() if w is None]
    zahlen = {n: (C.MESS_BUDGET_MINICP if n.startswith("Mini") else budget) if w is None else w for n, w in werte.items()}
    cols = st.columns(3)
    cols[0].metric("Mini-CP Stufe 2 (Knoten)", _bereich(row["mini2"], C.MESS_BUDGET_MINICP), delta="andere Einheit", delta_color="off")
    cols[1].metric("CNF mit Lernen, statisch (Konflikte)", _bereich(row["mit_stat"], budget), delta="Konflikte", delta_color="off")
    cols[2].metric("CNF ohne Lernen, gewichtet (Konflikte)", _bereich(row["ohne_gew"], budget), delta="Konflikte", delta_color="off")
    kind, text = E.verdict_instanz(row, budget)
    getattr(st, kind)(text)
    farben = {"Mini-CP Stufe 1 (Knoten)": C.COLOR_MINI, "Mini-CP Stufe 2 (Knoten)": C.COLOR_MINI, "CNF mit Lernen, statisch": C.COLOR_MIT, "CNF mit Lernen, gewichtet": C.COLOR_GEW,
              "CNF ohne Lernen, gewichtet": "#c9a227", "Standard-CDCL": C.COLOR_OHNE}
    st.plotly_chart(V.build_balken(zahlen, "Knoten beziehungsweise Konflikte (logarithmisch)", farben, abgebr), width="stretch", key="balken_zugeschnitten")
    st.caption(f"Rechenzeit der Einzelinstanz: {sek:.1f} s (nur Anzeige, kein Befund). Die Balken haben verschiedene Einheiten: Knoten (blau) gegen Konflikte (übrige).")

    st.markdown("**Messreihe (vorgerechnet, nicht live)**")
    kind, text = E.verdict_zugeschnitten(zeilen)
    getattr(st, kind)(text)
    kind, text = E.verdict_gewichtung(zeilen)
    getattr(st, kind)(text)
    _tabelle([[f"{z['groesse']} × {z['groesse']}", z["n"], _verteilung_text(z["mini1"]), _verteilung_text(z["mini2"]), _verteilung_text(z["mit_stat"]), _verteilung_text(z["ohne_gew"]),
               _verteilung_text(z["standard"]), _verteilung_text(z["cpsat"])] for z in zeilen],
             ["Größe", "Instanzen", "Mini-CP Stufe 1 (Knoten)", "Mini-CP Stufe 2 (Knoten)", "CNF mit Lernen, statisch", "CNF ohne Lernen, gewichtet", "Standard-CDCL", "CP-SAT (Konflikte, eingefroren)"])
    st.caption(f"Median (Maximum, Abbrüche). Mini-CP: Knotenbudget {E.zahl(meta['budget_minicp'])}. **CP-SAT** (OR-Tools {meta['ortools']}, ein Arbeiter) ist nur ein Maßstab, vorgerechnet und eingefroren ({meta['datum']}, `{meta['skript']}`), nicht live; "
               "die Demo behauptet nichts über CP-SAT-Interna. Antworten und Optima aller Instanzen sind gegen CP-SAT geprüft "
               f"({meta['antwortfehler']} Abweichungen).")

stash_kept_widget_state()
sync_query_params({k: aktueller_wert(k) for k in SETTING_SPECS})

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist |
|---|---|
| **Gleich schwache Suche als Vergleich** | Das Lernen schlägt hier die Suche ohne Gedächtnis, nicht die zugeschnittene: Das Mini-CP mit Disjunktiv-Propagation braucht im Messbereich im Median nicht mehr Zähleinheiten als die CNF mit Lernen; wie viel davon an Verzweigung und wie viel an Propagation liegt, ist nicht getrennt gemessen (Experiment 4). |
| **Ein Problem, ein Erzeuger** | Der Befund gilt für den Job Shop in der Order-Kodierung mit Dauern 1 bis 9 und diese Zufalls-Seeds; Rotationspläne mit Zählbedingungen waren zu leicht (Median ein Konflikt), kumulative Ressourcen sind nicht gemessen. |
| **Erklärungen nur für Hall (AllDifferent)** | Nur Stichproben dieser Klauseln sind einzeln gegen die CNF geprüft; für Disjunktiv- oder Kumulativ-Propagatoren mit Erklärung gibt es keinen Nachbau und keine Prüfung. |
| **Das Schubfach ist ein Sonderfall** | Es ist eine einzige Hall-Verletzung: 0 Konflikte sind dort kein Maß für andere Aufgaben. |
| **Eager statt lazy im Job Shop** | Die Order-Kodierung wird vorab vollständig gebaut; ein Lazy-Propagator mit Erklärung für Disjunktiv ist nicht nachgebaut. |
| **Die Quelle ist nur im Abstract gelesen** | Die Demo beschreibt den Mechanismus und ihre Messung, nicht die Arbeit von Ohrimenko, Stuckey und Codish. |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Gegeben und gesucht.** Eine Formel in konjunktiver Normalform (CNF) über Variablen, die Aussagen über ganzzahlige Größen codieren, und ein Propagator für eine Bedingung auf diesen Größen. Gesucht: ein Modell der CNF oder der Beweis, dass es keines gibt.

| Symbol | Bedeutung |
|---|---|
| $x_i$, $D_0(i)$ | Variable $i$ und ihre Anfangsdomäne |
| $[x_i = v]$ | Boolesche Variable „$x_i$ hat den Wert $v$“ (direkte Kodierung) |
| $[s_o \le t]$ | Boolesche Variable „Operation $o$ beginnt spätestens zur Zeit $t$“ (Order-Kodierung) |
| $R$, $V$ | Variablenmenge und die Werte, die sich ihre Domänen teilen |
| $d_o$ | Dauer der Operation $o$ |

**Order-Kodierung des Job Shops** (Entscheidung „Makespan $\le H$“; $y_{ab}$ = „$a$ vor $b$“ auf einer Maschine):

$$[s_o \le t] \;\rightarrow\; [s_o \le t+1]$$

$$[s_p \le t] \;\rightarrow\; [s_o \le t - d_o] \quad \text{($p$ folgt $o$ im Auftrag)}$$

$$y_{ab} \wedge [s_b \le t] \;\rightarrow\; [s_a \le t - d_a], \qquad \neg y_{ab} \wedge [s_a \le t] \;\rightarrow\; [s_b \le t - d_b].$$

Konstante Literale (für $t$ unterhalb des frühesten oder oberhalb des spätesten Starts) werden beim Bau herausgekürzt.

**Erklärungsklausel der Hall-Menge.** Eine Hall-Menge $R$ ist eine Menge von Variablen mit $\bigl|\bigcup_{u \in R} D(u)\bigr| = |R|$ ($D$ = aktuelle Domäne): ihre Variablen belegen alle Werte aus $V = \bigcup_{u \in R} D(u)$. Fällt ein Wert $w \in V$ aus der Domäne einer Variablen $x \notin R$, so gilt die Klausel

$$\neg[x = w] \;\vee\; \bigvee_{u \in R}\; \bigvee_{w' \in D_0(u) \setminus V} [u = w'],$$

denn hätte jede Variable aus $R$ einen Wert in $V$, wären alle $|V| = |R|$ Werte vergeben. Bei einer Hall-Verletzung ($|V| < |S|$ für eine Menge $S$) entfällt der erste Term: Die Klausel besagt, dass nicht alle Variablen aus $S$ ihre Werte in $V$ haben können.

**„Lazy“ in zwei Sätzen.** Die Klausel wird nicht vorab für alle möglichen Domänenzustände erzeugt, sondern erst, wenn der Propagator in einem konkreten Zustand einen Schluss zieht. In der Vormessung der Planung lösten an drei Instanzen nur 4 bis 30 % der vorab gebauten Klauseln je einen Schluss aus, das spricht für diese Arbeitsweise (in dieser Demo nicht gemessen).

**Aufwand.** Ein *Konflikt* ist eine verletzte Klausel im CDCL-Löser, ein *Knoten* ein Zustand der Suche im Mini-CP nach der Propagation (Wurzel eingeschlossen); beide Einheiten werden nie addiert.

**Literatur.** M. Ohrimenko, P. J. Stuckey, M. Codish: Propagation via lazy clause generation. Constraints 14(3), 2009, S. 357–391 (**nur Abstract gelesen**; die Demo beschreibt den Mechanismus und ihre eigene Messung, nicht die Arbeit). L. Perron, F. Didier, S. Gay: The CP-SAT-LP Solver. CP 2023 (Abstract gelesen: CP-SAT ist ein ganzzahliger CP-Löser auf einem SAT-Löser mit Lazy Clause Generation). J. P. Marques-Silva, K. A. Sakallah: GRASP. IEEE Trans. Computers 48(5), 1999 (Konfliktanalyse, Rücksprung; Volltext gelesen). Die Order-Kodierung ist eine eigene Darstellung des Messgeräts, keine Aussage über CP-SAT.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [SAT und CP: Konfliktlernen bis Wahl](https://sebastianhanisch.net/konzepte-sat-constraint-programming.html)."
)
