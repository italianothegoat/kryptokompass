"""
Was macht diese Datei?
----------------------
Unterseite "Analyse" (Adresse "/analyse").
Ein Coin und ein Zeitraum werden gewählt. Dann zeigt die Seite:
- Kennzahlen: Rendite, annualisierte Volatilität, maximaler Drawdown
- Kursdiagramm mit SMA 20, SMA 50 und Bollinger-Bändern
- RSI (14) und MACD (12/26/9)
- zu jedem Indikator eine ausklappbare Erklärung für Laien
"""

import dash  # dash: Seite registrieren
from dash import Input, Output, State, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import charts, data_loader, indicators  # Diagramme, Daten, Berechnungen
from src.components import coin_options, explanation, graph, metric_card, status_message  # Bausteine
from src.formatting import format_percent  # Deutsche Prozentformatierung

dash.register_page(__name__, path="/analyse", name="Analyse", order=2,  # Seite bei Dash anmelden
                   title="Analyse · KryptoKompass")  # Titel im Browser-Tab

layout = html.Div(  # Aufbau der Seite
    [
        html.H1("🔍 Coin-Analyse"),  # Seitenüberschrift
        html.Div(  # Zeile mit den Auswahlfeldern
            [
                html.Div([html.Label("Coin"), dcc.Dropdown(id="analysis-coin", clearable=False)],  # Coin-Auswahl
                         className="control-wide"),
                html.Div(  # Zeitraum-Auswahl
                    [
                        html.Label("Zeitraum"),  # Beschriftung
                        dcc.RadioItems(  # Auswahl 30/90/365 Tage
                            id="analysis-days",
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
        dcc.Loading(html.Div(id="analysis-content"), type="circle"),  # Inhalt mit Lade-Kreisel
    ]
)


@callback(  # Füllt die Coin-Auswahlliste (beim Öffnen, Währungswechsel, Aktualisieren)
    Output("analysis-coin", "options"),  # Ergebnis 1: die Einträge der Liste
    Output("analysis-coin", "value"),  # Ergebnis 2: der ausgewählte Coin
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
    State("analysis-coin", "value"),  # Nur lesen (kein Auslöser): bisher gewählter Coin
)
def update_coin_list(currency, _refresh, current_coin):
    """Lädt die Top-20-Liste und behält die bisherige Auswahl bei (sonst Bitcoin).

    Args:
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).
        current_coin: Bisher ausgewählte Coin-ID oder None.

    Returns:
        Liste der Einträge und die ausgewählte Coin-ID.
    """
    options, _ = coin_options(currency)  # Einträge bauen
    ids = [option["value"] for option in options]  # Nur die IDs herausziehen
    if current_coin in ids:  # Bisherige Auswahl noch in der Liste?
        return options, current_coin  # Dann beibehalten
    return options, "bitcoin" if "bitcoin" in ids else (ids[0] if ids else None)  # Sonst Bitcoin (oder erster Coin)


@callback(  # Baut den Seiteninhalt, sobald Coin, Zeitraum oder Währung sich ändern
    Output("analysis-content", "children"),  # Ergebnis: alles unterhalb der Auswahlfelder
    Input("analysis-coin", "value"),  # Auslöser: Coin
    Input("analysis-days", "value"),  # Auslöser: Zeitraum
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
)
def update_analysis(coin_id, days, currency, _refresh):
    """Lädt die Kurshistorie, berechnet alle Indikatoren und baut Kennzahlen und Diagramme.

    Args:
        coin_id: CoinGecko-ID, z. B. "bitcoin".
        days: Zeitraum in Tagen (30, 90 oder 365).
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).

    Returns:
        Liste von Dash-Komponenten für den Seiteninhalt.
    """
    if not coin_id:  # Noch kein Coin gewählt (z. B. Coin-Liste nicht ladbar)
        return html.Div("Bitte einen Coin auswählen.", className="alert alert-info")  # Freundlicher Hinweis

    result = data_loader.load_price_history(coin_id, currency.lower())  # 365 Tage Kursverlauf laden
    status = status_message(result, "Kursdaten")  # Statusmeldung bauen
    if result.data is None:  # Keine Daten?
        return status  # Nur die Fehlermeldung anzeigen
    prices_full = result.data  # Gesamte Historie (bis zu 365 Tage)

    # Indikatoren auf der GESAMTEN Historie berechnen und erst danach zuschneiden.
    # So hat z. B. SMA 50 auch am ersten sichtbaren Tag schon genug Vorlauf.
    sma20_full = indicators.sma(prices_full, 20)  # SMA 20
    sma50_full = indicators.sma(prices_full, 50)  # SMA 50
    bands_full = indicators.bollinger_bands(prices_full)  # Bollinger-Bänder
    rsi_full = indicators.rsi(prices_full)  # RSI 14
    macd_full = indicators.macd(prices_full)  # MACD 12/26/9

    prices = prices_full.iloc[-(days + 1):]  # Nur die letzten X Tage (+1, damit die Rendite über volle X Tage geht)
    visible = prices.index  # Die sichtbaren Datumswerte

    return [  # Seiteninhalt von oben nach unten
        status,  # "Stand …" oder Warnung
        html.Div(  # Drei Kennzahlen-Kacheln
            [
                metric_card(f"Rendite ({days} Tage)",  # Kachel 1
                            format_percent(indicators.total_return(prices) * 100)),  # *100: Dezimalzahl → Prozent
                metric_card("Volatilität (annualisiert)",  # Kachel 2
                            format_percent(indicators.annualized_volatility(prices) * 100, 1, False)),
                metric_card("Max. Drawdown",  # Kachel 3
                            format_percent(indicators.max_drawdown(prices) * 100, 1)),
            ],
            className="metrics",
        ),
        explanation(  # Erklärfeld zu den Kennzahlen
            "Was bedeuten diese Kennzahlen?",
            "- **Rendite:** Um wie viel Prozent sich der Kurs vom ersten bis zum letzten Tag des Zeitraums "
            "verändert hat.\n"
            "- **Volatilität:** Wie stark der Kurs typischerweise schwankt, hochgerechnet auf ein Jahr. "
            "60 % heißt grob: Ein Ausschlag von ±60 % innerhalb eines Jahres wäre nicht ungewöhnlich.\n"
            "- **Maximaler Drawdown:** Der größte Verlust, den jemand erlitten hätte, der am ungünstigsten "
            "Hochpunkt gekauft und am folgenden Tiefpunkt verkauft hätte.",
        ),
        html.H2("Kursverlauf mit SMA und Bollinger-Bändern"),  # Zwischenüberschrift
        graph(charts.price_chart(  # Kursdiagramm, Indikatoren auf den sichtbaren Zeitraum zugeschnitten
            prices, sma20_full.loc[visible], sma50_full.loc[visible], bands_full.loc[visible], currency)),
        explanation(  # Erklärfeld
            "Was bedeuten SMA und Bollinger-Bänder?",
            "**SMA (Simple Moving Average)** ist der Durchschnittskurs der letzten 20 bzw. 50 Tage. Er glättet "
            "das Auf und Ab und zeigt den Trend: Liegt der Kurs über dem SMA, ging es zuletzt eher aufwärts.\n\n"
            "**Bollinger-Bänder** liegen zwei Standardabweichungen über und unter dem SMA 20. Ein breites Band "
            "bedeutet starke Schwankungen, ein schmales Band einen ruhigen Markt.",
        ),
        html.H2("RSI (14 Tage)"),  # Zwischenüberschrift
        graph(charts.rsi_chart(rsi_full.loc[visible])),  # RSI-Diagramm
        explanation(  # Erklärfeld
            "Was bedeutet der RSI?",
            "Der **Relative Strength Index** vergleicht die Kursgewinne mit den Kursverlusten der letzten 14 Tage "
            "und liegt immer zwischen 0 und 100. Über 70 gilt ein Coin oft als *überkauft*, unter 30 als "
            "*überverkauft*. Das sind Faustregeln, keine Vorhersagen.",
        ),
        html.H2("MACD (12/26/9)"),  # Zwischenüberschrift
        graph(charts.macd_chart(macd_full.loc[visible])),  # MACD-Diagramm
        explanation(  # Erklärfeld
            "Was bedeutet der MACD?",
            "Der **MACD** ist der Abstand zwischen einem schnellen (12 Tage) und einem langsamen (26 Tage) "
            "Durchschnittskurs. Die **Signallinie** ist dessen Durchschnitt über 9 Tage. Kreuzt der MACD die "
            "Signallinie von unten nach oben (Balken werden grün), deuten viele das als beginnenden "
            "Aufwärtsschwung – umgekehrt als Abwärtsschwung.",
        ),
    ]
