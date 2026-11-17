"""
Was macht diese Datei?
----------------------
Sie baut alle Diagramme der App mit Plotly.

Jede Funktion bekommt fertig berechnete Daten (aus indicators.py) und gibt eine
Plotly-"Figure" zurück. Die Seiten zeigen sie dann mit dcc.Graph an (siehe components.graph).
Plotly-Diagramme sind interaktiv: Zoomen, Werte per Mauszeiger ablesen, Linien ein-/ausblenden.
"""

import pandas as pd  # pandas: Datentypen für die Eingaben
import plotly.express as px  # plotly.express: schnelle Standard-Diagramme (hier: Heatmap, Linien)
import plotly.graph_objects as go  # plotly.graph_objects: Diagramme Linie für Linie selbst zusammenbauen

CHART_HEIGHT = 380  # Einheitliche Höhe für die großen Diagramme (in Pixeln)
SMALL_CHART_HEIGHT = 260  # Höhe für RSI und MACD


def _base_layout(fig: go.Figure, height: int, y_title: str) -> go.Figure:
    """Setzt einheitliche Layout-Einstellungen für alle Diagramme.

    Args:
        fig: Das Diagramm.
        height: Höhe in Pixeln.
        y_title: Beschriftung der y-Achse.

    Returns:
        Dasselbe Diagramm mit angepasstem Layout.
    """
    fig.update_layout(  # Mehrere Layout-Einstellungen auf einmal setzen
        height=height,  # Höhe
        margin=dict(l=10, r=10, t=30, b=10),  # Schmale Ränder, damit mehr Platz fürs Diagramm bleibt
        hovermode="x unified",  # Beim Darüberfahren alle Werte des Tages in einem Kästchen zeigen
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),  # Legende waagerecht über dem Diagramm
        yaxis_title=y_title,  # Beschriftung der y-Achse
        separators=",.",  # Deutsche Zahlen: Komma als Dezimal-, Punkt als Tausendertrennzeichen
        xaxis_tickformat="%d.%m.%y",  # Datum auf der x-Achse deutsch, z. B. 16.11.26 (statt "Nov 16")
        xaxis_hoverformat="%d.%m.%Y",  # Datum im Info-Kästchen beim Darüberfahren, z. B. 16.11.2026
        xaxis_title=None,  # Keine Beschriftung unter der x-Achse (Datum ist selbsterklärend)
    )
    return fig  # Angepasstes Diagramm zurückgeben


def price_chart(prices: pd.Series, sma20: pd.Series, sma50: pd.Series,
                bands: pd.DataFrame, currency: str) -> go.Figure:
    """Kursdiagramm mit SMA 20, SMA 50 und Bollinger-Bändern.

    Args:
        prices: Tageskurse.
        sma20: Gleitender Durchschnitt über 20 Tage.
        sma50: Gleitender Durchschnitt über 50 Tage.
        bands: Bollinger-Bänder (Spalten "upper", "lower").
        currency: "EUR" oder "USD" für die Achsenbeschriftung.

    Returns:
        Plotly-Diagramm.
    """
    fig = go.Figure()  # Leeres Diagramm anlegen
    fig.add_trace(go.Scatter(  # Oberes Bollinger-Band (dünn, grau)
        x=bands.index, y=bands["upper"], name="Bollinger oben",
        line=dict(color="rgba(150,150,150,0.6)", width=1),
    ))
    fig.add_trace(go.Scatter(  # Unteres Bollinger-Band; Fläche bis zum oberen Band einfärben
        x=bands.index, y=bands["lower"], name="Bollinger unten",
        line=dict(color="rgba(150,150,150,0.6)", width=1),
        fill="tonexty", fillcolor="rgba(150,150,150,0.12)",  # "tonexty" = bis zur vorherigen Linie füllen
    ))
    fig.add_trace(go.Scatter(  # Der eigentliche Kurs (kräftige Linie)
        x=prices.index, y=prices, name="Kurs", line=dict(color="#2563eb", width=2),
    ))
    fig.add_trace(go.Scatter(  # SMA 20 (orange)
        x=sma20.index, y=sma20, name="SMA 20", line=dict(color="#f59e0b", width=1.5),
    ))
    fig.add_trace(go.Scatter(  # SMA 50 (violett)
        x=sma50.index, y=sma50, name="SMA 50", line=dict(color="#8b5cf6", width=1.5),
    ))
    return _base_layout(fig, CHART_HEIGHT, f"Preis in {currency}")  # Einheitliches Layout anwenden


def rsi_chart(rsi_values: pd.Series) -> go.Figure:
    """RSI-Diagramm mit Markierungen bei 30 (überverkauft) und 70 (überkauft).

    Args:
        rsi_values: RSI-Werte (0–100).

    Returns:
        Plotly-Diagramm.
    """
    fig = go.Figure()  # Leeres Diagramm
    fig.add_trace(go.Scatter(  # RSI-Linie
        x=rsi_values.index, y=rsi_values, name="RSI 14", line=dict(color="#2563eb", width=2),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="#dc2626",  # Rote gestrichelte Linie bei 70
                  annotation_text="70 – überkauft", annotation_position="top left")
    fig.add_hline(y=30, line_dash="dash", line_color="#16a34a",  # Grüne gestrichelte Linie bei 30
                  annotation_text="30 – überverkauft", annotation_position="bottom left")
    fig.update_yaxes(range=[0, 100])  # y-Achse immer von 0 bis 100
    return _base_layout(fig, SMALL_CHART_HEIGHT, "RSI")  # Einheitliches Layout


def macd_chart(macd_values: pd.DataFrame) -> go.Figure:
    """MACD-Diagramm: MACD-Linie, Signallinie und Histogramm als Balken.

    Args:
        macd_values: DataFrame mit Spalten "macd", "signal", "histogram".

    Returns:
        Plotly-Diagramm.
    """
    colors = ["#16a34a" if value >= 0 else "#dc2626" for value in macd_values["histogram"]]  # Grün bei ≥ 0, sonst rot
    fig = go.Figure()  # Leeres Diagramm
    fig.add_trace(go.Bar(  # Histogramm als Balken
        x=macd_values.index, y=macd_values["histogram"], name="Histogramm", marker_color=colors,
    ))
    fig.add_trace(go.Scatter(  # MACD-Linie
        x=macd_values.index, y=macd_values["macd"], name="MACD", line=dict(color="#2563eb", width=2),
    ))
    fig.add_trace(go.Scatter(  # Signallinie
        x=macd_values.index, y=macd_values["signal"], name="Signal", line=dict(color="#f59e0b", width=1.5),
    ))
    return _base_layout(fig, SMALL_CHART_HEIGHT, "MACD")  # Einheitliches Layout


def normalized_chart(normalized: pd.DataFrame) -> go.Figure:
    """Liniendiagramm mehrerer Coins, alle auf 100 normiert.

    Args:
        normalized: Tabelle mit einer Spalte pro Coin (Startwert 100).

    Returns:
        Plotly-Diagramm.
    """
    fig = px.line(normalized)  # Für jede Spalte automatisch eine Linie zeichnen
    fig.add_hline(y=100, line_dash="dot", line_color="gray")  # Startniveau 100 als Orientierung
    fig.update_layout(legend_title_text="Coin")  # Überschrift der Legende setzen
    return _base_layout(fig, CHART_HEIGHT, "Wert (Start = 100)")  # Einheitliches Layout


def forecast_chart(history: pd.Series, path: pd.DataFrame, currency: str) -> go.Figure:
    """Kursverlauf der Vergangenheit plus Prognose mit 95-%-Band.

    Args:
        history: Bisherige Tageskurse (z. B. die letzten 120 Tage).
        path: Prognose-Verlauf mit Spalten "expected", "lower", "upper" (aus forecast.py).
        currency: "EUR" oder "USD" für die Achsenbeschriftung.

    Returns:
        Plotly-Diagramm.
    """
    start = pd.DataFrame(  # Startpunkt der Prognose = letzter echter Kurs (damit die Linien verbunden sind)
        {"expected": [history.iloc[-1]], "lower": [history.iloc[-1]], "upper": [history.iloc[-1]]},
        index=[history.index[-1]],
    )
    full_path = pd.concat([start, path])  # Startpunkt vor die Prognose hängen
    fig = go.Figure()  # Leeres Diagramm
    fig.add_trace(go.Scatter(  # Bisheriger Kurs
        x=history.index, y=history, name="Kurs (Vergangenheit)", line=dict(color="#2563eb", width=2),
    ))
    fig.add_trace(go.Scatter(  # Obere Grenze des Bands (dünne Linie, dient als Rand)
        x=full_path.index, y=full_path["upper"], name="95-%-Band oben", mode="lines",  # Nur Linie, keine Punkte
        line=dict(color="rgba(245,158,11,0.5)", width=1),
    ))
    fig.add_trace(go.Scatter(  # Untere Grenze; Fläche bis zur oberen Grenze füllen
        x=full_path.index, y=full_path["lower"], name="95-%-Band unten", mode="lines",  # Nur Linie
        line=dict(color="rgba(245,158,11,0.5)", width=1),
        fill="tonexty", fillcolor="rgba(245,158,11,0.15)",
    ))
    fig.add_trace(go.Scatter(  # Erwarteter Kurs (gestrichelt = Schätzung, keine echten Daten)
        x=full_path.index, y=full_path["expected"], name="Prognose", mode="lines",  # Nur Linie
        line=dict(color="#f59e0b", width=2.5, dash="dash"),
    ))
    return _base_layout(fig, CHART_HEIGHT, f"Preis in {currency}")  # Einheitliches Layout


def backtest_chart(comparison: pd.DataFrame, horizon: int) -> go.Figure:
    """Vergleicht im Backtest die vorhergesagte mit der tatsächlichen Rendite.

    Args:
        comparison: Tabelle mit Spalten "actual" und "predicted" (Dezimalzahlen) je Testtag.
        horizon: Prognosezeitraum in Tagen (für die Beschriftung).

    Returns:
        Plotly-Diagramm.
    """
    fig = go.Figure()  # Leeres Diagramm
    fig.add_trace(go.Scatter(  # Was wirklich passiert ist
        x=comparison.index, y=comparison["actual"] * 100, name="Tatsächlich",
        line=dict(color="#2563eb", width=2),
    ))
    fig.add_trace(go.Scatter(  # Was das Modell vorhergesagt hatte
        x=comparison.index, y=comparison["predicted"] * 100, name="Vorhergesagt",
        line=dict(color="#f59e0b", width=2, dash="dash"),
    ))
    fig.add_hline(y=0, line_color="gray", line_dash="dot")  # Nulllinie: darüber = gestiegen, darunter = gefallen
    return _base_layout(fig, SMALL_CHART_HEIGHT, f"Rendite in {horizon} Tagen (%)")  # Einheitliches Layout


def correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    """Heatmap der Korrelationsmatrix.

    Args:
        corr: Quadratische Korrelationstabelle (Werte von -1 bis +1).

    Returns:
        Plotly-Diagramm.
    """
    fig = px.imshow(  # Tabelle als farbiges Raster darstellen
        corr,
        text_auto=".2f",  # Zahlen mit 2 Nachkommastellen in jedes Feld schreiben
        color_continuous_scale="RdBu",  # Farbskala: Rot (negativ) – Weiß – Blau (positiv)
        zmin=-1, zmax=1,  # Skala fest von -1 bis +1, damit Farben vergleichbar bleiben
        aspect="auto",  # Felder dürfen sich an die verfügbare Breite anpassen
    )
    fig.update_layout(height=CHART_HEIGHT, margin=dict(l=10, r=10, t=30, b=10), separators=",.")  # Größe, Ränder, Zahlenformat
    return fig  # Fertiges Diagramm zurückgeben
