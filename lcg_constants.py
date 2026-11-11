"""Konstanten: Regler-Grenzen, feste Annahmen, Farben und Presets."""

# --- Seitenleiste (allgemeine Einstellungen)
SEED_MAX, DEFAULT_SEED = 999999, 4
GROESSE_MIN, GROESSE_MAX, DEFAULT_GROESSE = 3, 7, 5          # Job Shop groesse × groesse (Experimente 3 und 4)
BUDGET_OPTIONEN = (500, 1000, 2000, 5000)                     # Konfliktbudget der Live-Läufe
DEFAULT_BUDGET = 2000

# --- Experimentregler im Hauptbereich
EXPERIMENTE = (
    "1 · Eine Erklärung von Hand",
    "2 · Schubfach mit und ohne Erklärung",
    "3 · Job Shop: Lernen aus oder an",
    "4 · Gegen die zugeschnittene Suche",
)
DEFAULT_EXPERIMENT = EXPERIMENTE[0]
BEISPIELE = ("H1 · Hall-Erklärung (AllDifferent)", "H2 · Mini-Job-Shop 2 × 2")
DEFAULT_BEISPIEL = BEISPIELE[0]
H2_HORIZONT_OPTIONEN = (3, 4, 5)
DEFAULT_H2_HORIZONT = 4
H_MIN, H_MAX, DEFAULT_H = 3, 8, 5                              # Schubfach: h + 1 Tauben auf h Löcher
LIVE_H_MAX = 7                                                 # darüber ist der Lauf ohne Erklärung eingefroren (zu lang für eine Live-Rechnung)
REIHENFOLGEN = ("statisch", "gewichtet")
DEFAULT_REIHENFOLGE = "statisch"
KLAUSEL_PRUEF_BUDGET = 20000                                   # Konfliktbudget der Einzelprüfung einer Klausel

# --- Messreihen (vorgerechnet in lcg_messreihen.json, Messskript tools/messung_messreihen.py)
MESS_GROESSEN = (4, 5, 6, 7, 8)
MESS_SEEDS = tuple(range(12))
MESS_BUDGET = 5000                                            # Konfliktbudget der CNF-Läufe (Abbruch zählt mit Budget)
MESS_BUDGET_MINICP = 20000                                    # Knotenbudget des Mini-CP
LIVE_MESS_GROESSE_MAX = 6                                     # die Live-Messreihe rechnet bis zu dieser Größe auf Knopfdruck
MESSREIHEN_DATEI = "lcg_messreihen.json"
MESS_SKRIPT = "tools/messung_messreihen.py"

# --- Verdikt-Schwellen (vor dem Bau festgelegt, Test in tests/test_verdicts.py)
GLEICHAUF_FAKTOR = 1.5      # unter diesem Verhältnis der Mediane gelten zwei Verfahren als gleichauf

# --- Farben
COLOR_OHNE = "#9a9a9a"
COLOR_MIT = "#2F6B65"
COLOR_GEW = "#b07aa1"
COLOR_MINI = "#4c78a8"
COLOR_IN = "#cfe8d5"
COLOR_GONE = "#e57373"
COLOR_FIXED = "#2F6B65"
COLOR_OUT = "#eeeeee"
COLOR_FENSTER = "rgba(76,120,168,0.28)"
COLOR_FENSTER_LINIE = "#4c78a8"

# Presets: stellen Experiment, Beispiel und Regler ein (die Experimente stehen in einer Auswahl, die ein Preset umschalten kann)
PRESETS = {
    "Handbeispiel H1: Hall-Erklärung": {"experiment": DEFAULT_EXPERIMENT, "beispiel": BEISPIELE[0]},
    "Handbeispiel H2: Mini-Job-Shop 2 × 2": {"experiment": EXPERIMENTE[0], "beispiel": BEISPIELE[1]},
    "Job Shop 6 × 6": {"experiment": EXPERIMENTE[2], "groesse": 6},
    "Schubfach h = 5": {"experiment": EXPERIMENTE[1], "h": 5},
}
PRESET_HELP = {
    "Handbeispiel H1: Hall-Erklärung": "Drei Variablen, alle verschieden: Nach der Entscheidung x1 ≠ 3 teilen sich x1 und x2 die Werte 1 und 2, also fallen sie aus x3. Zu jedem Schluss steht seine Klausel da, und ein Knopf prüft sie gegen die CNF.",
    "Handbeispiel H2: Mini-Job-Shop 2 × 2": "Vier Operationen auf zwei Maschinen mit Horizont 4: Von allen sieben Plänen gilt „a vor d“ und „c vor b“. Die CNF in der Order-Kodierung kennt beides schon an der Wurzel; die Klauseln lassen sich prüfen.",
    "Job Shop 6 × 6": "Zufalls-Job-Shop mit 6 Aufträgen auf 6 Maschinen: dieselbe CNF mit Lernen aus und an. Die vier Varianten stehen nebeneinander, darunter die vorgerechnete Messreihe über 12 feste Zufalls-Seeds.",
    "Schubfach h = 5": "6 Tauben auf 5 Löcher: Der Kern-CDCL braucht 159 Konflikte, mit der Hall-Erklärung steht die Unerfüllbarkeit an der Wurzel (0 Konflikte der Suche).",
}
