"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import lcg_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.22), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_matrix(namen, doms0, vorher, nachher):
    """Domänen-Matrix: Zeile je Variable, Spalte je Wert. Grau = Wert nie in der Anfangsdomäne, hellgrün = in der Domäne, rot ✗ = in diesem Schritt gestrichen,
    dunkelgrün ✓ = Variable festgelegt. `vorher`/`nachher`: Domänen vor und nach dem betrachteten Schritt."""
    werte = sorted({w for d in doms0 for w in d})
    z, text = [], []
    for i in range(len(doms0)):
        zeile, tzeile = [], []
        for w in werte:
            if w not in doms0[i]:
                code, t = 0, ""
            elif w in nachher[i]:
                code, t = (3, "✓") if len(nachher[i]) == 1 else (1, "")
            elif w in vorher[i]:
                code, t = 2, "✗"
            else:
                code, t = 0, ""
            zeile.append(code)
            tzeile.append(t)
        z.append(zeile)
        text.append(tzeile)
    farben = [(0.0, C.COLOR_OUT), (0.25, C.COLOR_OUT), (0.25, C.COLOR_IN), (0.5, C.COLOR_IN), (0.5, C.COLOR_GONE), (0.75, C.COLOR_GONE), (0.75, C.COLOR_FIXED), (1.0, C.COLOR_FIXED)]
    fig = go.Figure(go.Heatmap(z=z, x=[str(w) for w in werte], y=list(namen), text=text, texttemplate="%{text}", colorscale=farben, zmin=0, zmax=3,
                               showscale=False, xgap=2, ygap=2, hovertemplate="%{y}, Wert %{x}<extra></extra>"))
    fig.update_xaxes(title_text="Wert", type="category", side="top")
    fig.update_yaxes(autorange="reversed", type="category")
    return _base(fig, height=max(220, 46 * len(doms0) + 80))


def build_fenster(namen, est, lst, d, horizont, maschinen):
    """Zeitfenster der Operationen bei Horizont H: hell = möglicher Bereich [est, lst + d), dunkel = Pflichtteil [lst, est + d), der in jedem Plan belegt ist; rote Linie = Horizont.
    Zeile je Operation, nach Maschine beschriftet."""
    fig = go.Figure()
    n = len(namen)
    y = [f"{namen[o]} (M{maschinen[o] + 1})" for o in range(n)]
    fig.add_trace(go.Bar(y=y, x=[lst[o] + d[o] - est[o] for o in range(n)], base=[est[o] for o in range(n)], orientation="h", marker=dict(color=C.COLOR_FENSTER, line=dict(color=C.COLOR_FENSTER_LINIE, width=1)),
                         name="möglicher Bereich", hovertemplate="%{y}: von %{base} bis %{x}<extra></extra>"))
    pflicht = [(lst[o], est[o] + d[o]) for o in range(n)]
    fig.add_trace(go.Bar(y=y, x=[max(0, b - a) for a, b in pflicht], base=[a for a, _ in pflicht], orientation="h", marker=dict(color=C.COLOR_FIXED), name="Pflichtteil"))
    fig.add_vline(x=horizont, line_color="#c0392b", line_dash="dash", annotation_text=f"H = {horizont}", annotation_position="top")
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Zeit", range=[0, horizont + 0.5], dtick=1)
    fig.update_yaxes(autorange="reversed", type="category")
    return _base(fig, height=max(240, 44 * n + 90))


def build_schubfach(zeilen):
    """Konflikte je h ohne und mit Hall-Erklärung (logarithmische Achse). 0 Konflikte sind nicht darstellbar: sie stehen als Punkt am unteren Rand (Wert 0,5) mit der Beschriftung „0“.
    Hohle Marken: Lauf am Budget abgebrochen (Untergrenze)."""
    hs = [z["h"] for z in zeilen]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hs, y=[z["ohne"] for z in zeilen], mode="lines+markers", name="Kern-CDCL ohne Erklärung", line=dict(color=C.COLOR_OHNE, width=3),
                             marker=dict(size=10, color=[("white" if z.get("ohne_abgebrochen") else C.COLOR_OHNE) for z in zeilen], line=dict(color=C.COLOR_OHNE, width=2)),
                             hovertemplate="h = %{x}: %{y} Konflikte<extra></extra>"))
    fig.add_trace(go.Scatter(x=hs, y=[max(z["hall"], 0.5) for z in zeilen], mode="lines+markers+text", text=[str(z["hall"]) for z in zeilen], textposition="top center",
                             name="mit Hall-Erklärung", line=dict(color=C.COLOR_MIT, width=3), marker=dict(size=10, color=C.COLOR_MIT),
                             hovertemplate="h = %{x}: %{text} Konflikte der Suche<extra></extra>"))
    fig.update_xaxes(title_text="h (h + 1 Tauben auf h Löcher)", dtick=1)
    fig.update_yaxes(title_text="Konflikte (logarithmisch)", type="log")
    return _base(fig)


def build_kasten(daten_je_groesse, titel_y="Konflikte (logarithmisch; Abbruch zählt mit dem Budget)"):
    """Kastendiagramm je Größe: `daten_je_groesse` = {Größe: {Name der Variante: [Werte]}}; eine Spur je Variante, gruppiert nach Größe."""
    namen = []
    for g in daten_je_groesse.values():
        for k in g:
            if k not in namen:
                namen.append(k)
    farben = {"ohne": C.COLOR_OHNE, "mit": C.COLOR_MIT, "Mini-CP Stufe 2 (Knoten)": C.COLOR_MINI}
    fig = go.Figure()
    for name in namen:
        xs, ys = [], []
        for g, varianten in daten_je_groesse.items():
            for w in varianten.get(name, []):
                xs.append(f"{g} × {g}")
                ys.append(max(w, 0.5))
        fig.add_trace(go.Box(x=xs, y=ys, name=name, boxpoints="all", jitter=0.4, pointpos=0, marker=dict(color=farben.get(name, "#888"), size=4), line=dict(color=farben.get(name, "#888"))))
    fig.update_layout(boxmode="group")
    fig.update_yaxes(title_text=titel_y, type="log")
    fig.update_xaxes(title_text="Größe (Aufträge × Maschinen)")
    return _base(fig, height=400)


def build_balken(werte: dict, titel: str, farben: dict | None = None, abgebrochen=()):
    """Ein Balken je Verfahren (logarithmische Achse; 0 steht als 0,5 am unteren Rand mit Beschriftung). `werte`: {Name: Wert}."""
    namen = list(werte)
    fig = go.Figure(go.Bar(x=namen, y=[max(werte[n], 0.5) for n in namen], marker_color=[(farben or {}).get(n, C.COLOR_MIT) for n in namen],
                           text=[(f"≥ {werte[n]}" if n in abgebrochen else str(werte[n])) for n in namen], textposition="outside", hoverinfo="skip"))
    fig.update_yaxes(title_text=titel, type="log")
    return _base(fig, height=320)


def build_laenge(laengen):
    """Länge der gelernten Klausel je Konflikt (Reihenfolge der Konflikte von links nach rechts)."""
    fig = go.Figure(go.Scatter(x=list(range(1, len(laengen) + 1)), y=laengen, mode="lines+markers", line=dict(color=C.COLOR_MIT, width=2), marker=dict(size=5),
                               hovertemplate="Konflikt %{x}: %{y} Literale<extra></extra>"))
    fig.update_xaxes(title_text="Konflikt")
    fig.update_yaxes(title_text="Literale der gelernten Klausel", rangemode="tozero")
    return _base(fig, height=280)
