"""
Was macht diese Datei?
----------------------
Unterseite "Vergleich" (Adresse "/vergleich").
2 bis 4 Coins werden gewählt. Die Seite zeigt:
- die Kursentwicklung aller Coins, auf 100 normiert, in einem Diagramm
- die Korrelationsmatrix der täglichen Renditen als Heatmap
"""

import dash  # dash: Seite registrieren
import pandas as pd  # pandas: Kursreihen zu einer Tabelle zusammenfügen
from dash import Input, Output, State, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import charts, data_loader, indicators  # Unsere Module
from src.components import coin_options, explanation, graph  # Bausteine
from src.formatting import format_percent  # Deutsche Prozentformatierung

dash.register_page(__name__, path="/vergleich", name="Vergleich", order=4,  # Seite bei Dash anmelden
                   title="Vergleich · KryptoKompass")  # Titel im Browser-Tab

DEFAULT_COINS = ["bitcoin", "ethereum", "solana"]  # Vorauswahl beim ersten Öffnen
MAX_COINS = 4  # Höchstens so viele Coins gleichzeitig

layout = html.Div(  # Aufbau der Seite
    [
        html.H1("⚖️ Vergleich"),  # Seitenüberschrift
        html.Div(  # Zeile mit den Auswahlfeldern
            [
                html.Div(  # Mehrfachauswahl der Coins
                    [
                        html.Label("Coins (2 bis 4)"),  # Beschriftung
                        dcc.Dropdown(id="compare-coins", multi=True),  # multi=True: mehrere wählbar
                    ],
                    className="control-wide",
                ),
                html.Div(  # Zeitraum
                    [
                        html.Label("Zeitraum"),  # Beschriftung
                        dcc.RadioItems(  # Auswahl 30/90/365 Tage
                            id="compare-days",
                            options=[{"label": f"{d} Tage", "value": d} for d in (30, 90, 365)],  # Drei Optionen
                            value=90,  # Standard: 90 Tage
                            inline=True,  # Nebeneinander
                            className="radio",
                        ),
                    ],
                    className="control",
                ),
            ],
            className="controls",
        ),
        dcc.Loading(html.Div(id="compare-content"), type="circle"),  # Inhalt mit Lade-Kreisel
    ]
)


@callback(  # Füllt die Auswahlliste mit den Top-20-Coins
    Output("compare-coins", "options"),  # Ergebnis 1: Einträge
    Output("compare-coins", "value"),  # Ergebnis 2: ausgewählte Coins
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
    State("compare-coins", "value"),  # Bisherige Auswahl (nur lesen)
)
def update_coin_list(currency, _refresh, current_selection):
    """Lädt die Top-20-Liste und behält die bisherige Auswahl bei (sonst die Vorauswahl).

    Args:
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).
        current_selection: Bisher gewählte Coin-IDs oder None.

    Returns:
        Liste der Einträge und die ausgewählten Coin-IDs.
    """
    options, _ = coin_options(currency)  # Einträge bauen
    ids = [option["value"] for option in options]  # Nur die IDs
    still_valid = [cid for cid in (current_selection or []) if cid in ids]  # Bisherige Auswahl, soweit noch gültig
    if still_valid:  # Gab es schon eine Auswahl?
        return options, still_valid  # Dann beibehalten
    return options, [cid for cid in DEFAULT_COINS if cid in ids]  # Sonst die Vorauswahl (soweit vorhanden)


@callback(  # Baut Diagramme, sobald Auswahl, Zeitraum oder Währung sich ändern
    Output("compare-content", "children"),  # Ergebnis: Seiteninhalt
    Input("compare-coins", "value"),  # Auslöser: gewählte Coins
    Input("compare-days", "value"),  # Auslöser: Zeitraum
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
)
def update_comparison(selected, days, currency, _refresh):
    """Lädt die Historien aller gewählten Coins und baut Vergleichsdiagramm und Heatmap.

    Args:
        selected: Liste der gewählten Coin-IDs.
        days: Zeitraum in Tagen.
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).

    Returns:
        Liste von Dash-Komponenten für den Seiteninhalt.
    """
    selected = selected or []  # None (nichts gewählt) wie leere Liste behandeln
    if len(selected) < 2:  # Für einen Vergleich braucht man mindestens zwei
        return html.Div("Bitte mindestens zwei Coins auswählen.", className="alert alert-info")  # Hinweis

    messages = []  # Hier sammeln wir Hinweise und Warnungen
    if len(selected) > MAX_COINS:  # Zu viele gewählt?
        messages.append(html.Div(f"Es werden nur die ersten {MAX_COINS} Coins verglichen.",
                                 className="alert alert-info"))  # Hinweis
        selected = selected[:MAX_COINS]  # Auf die ersten vier kürzen

    options, _ = coin_options(currency)  # Für die schönen Namen
    names = {option["value"]: option["label"] for option in options}  # ID → Anzeigename

    series_list = []  # Hier sammeln wir die Kursreihen
    for coin_id in selected:  # Für jeden gewählten Coin …
        result = data_loader.load_price_history(coin_id, currency.lower())  # … Historie laden
        name = names.get(coin_id, coin_id)  # Anzeigename (oder ID, falls unbekannt)
        if result.from_database:  # Live-Abruf gescheitert, Reserve benutzt
            messages.append(html.Div(f"{name}: {result.error_message} Es werden gespeicherte Daten verwendet.",
                                     className="alert alert-warning"))  # Warnung
        if result.data is None:  # Gar keine Daten
            messages.append(html.Div(f"Für {name} sind keine Kursdaten verfügbar.", className="alert alert-error"))
            continue  # Diesen Coin überspringen
        series_list.append(result.data.rename(name))  # Spalte nach dem Anzeigenamen benennen

    if len(series_list) < 2:  # Nach Fehlern weniger als zwei übrig?
        return messages  # Nur die Meldungen zeigen

    prices_full = pd.concat(series_list, axis=1).dropna()  # Nebeneinanderstellen; nur Tage, an denen ALLE Werte haben
    prices = prices_full.iloc[-(days + 1):]  # Auf den gewählten Zeitraum zuschneiden
    normalized = indicators.normalize_to_100(prices)  # Alle Coins starten bei 100
    corr = indicators.correlation_matrix(prices)  # Korrelationsmatrix

    returns_text = ", ".join(  # Rendite jedes Coins als kurzer Text
        f"**{name}:** {format_percent(indicators.total_return(prices[name]) * 100)}"  # z. B. "Bitcoin (BTC): +5,12 %"
        for name in prices.columns  # für jede Spalte (= jeden Coin)
    )

    return messages + [  # Meldungen zuerst, dann der eigentliche Inhalt
        html.H2("Kursentwicklung (Start = 100)"),  # Zwischenüberschrift
        graph(charts.normalized_chart(normalized)),  # Diagramm
        dcc.Markdown(f"Rendite im Zeitraum – {returns_text}"),  # Renditen unter dem Diagramm
        explanation(  # Erklärung
            "Was bedeutet „auf 100 normiert“?",
            "Bitcoin kostet zehntausende Euro, andere Coins nur Cent-Beträge – in einem normalen Diagramm wäre der "
            "kleine Coin eine flache Linie. Deshalb setzen wir den Startkurs jedes Coins auf **100**. Ein Wert von 120 "
            "bedeutet dann: +20 % seit Beginn des Zeitraums, 80 bedeutet: −20 %.",
        ),
        html.H2("Korrelation der täglichen Renditen"),  # Zwischenüberschrift
        graph(charts.correlation_heatmap(corr)),  # Heatmap
        explanation(  # Erklärung
            "Was bedeutet die Korrelation?",
            "Die **Korrelation** zeigt, wie ähnlich sich zwei Coins von Tag zu Tag bewegen. **+1** heißt: Sie steigen "
            "und fallen immer gemeinsam, **0**: kein Zusammenhang, **−1**: genau gegenläufig. Viele Kryptowährungen "
            "sind stark positiv korreliert – wer mehrere davon besitzt, ist also weniger breit gestreut, als es scheint.",
        ),
    ]
