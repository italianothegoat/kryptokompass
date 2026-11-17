"""
Was macht diese Datei?
----------------------
Unterseite "Prognose" (Adresse "/prognose").
Sagt den Kurs eines Coins für 7, 14 oder 30 Tage voraus (lineare Regression aus
Indikatoren, siehe src/forecast.py) und zeigt mit einem Backtest, wie gut diese
Methode in der Vergangenheit funktioniert hätte.
"""

import dash  # dash: Seite registrieren
from dash import Input, Output, State, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import charts, data_loader, forecast  # Diagramme, Daten, Prognose
from src.components import coin_options, explanation, graph, metric_card, status_message  # Bausteine
from src.formatting import format_percent, format_price  # Deutsche Zahlenformate

dash.register_page(__name__, path="/prognose", name="Prognose", order=3,  # Seite bei Dash anmelden
                   title="Prognose · KryptoKompass")  # Titel im Browser-Tab

HISTORY_DAYS_SHOWN = 120  # So viele vergangene Tage zeigt das Prognose-Diagramm vor der Prognose

layout = html.Div(  # Aufbau der Seite
    [
        html.H1("🔮 Kursprognose"),  # Seitenüberschrift
        html.Div(  # Deutlicher Warnhinweis gleich oben
            "Experiment, keine Anlageberatung: Kryptokurse hängen stark von Nachrichten und Stimmung ab, die in "
            "vergangenen Kursen nicht enthalten sind. Der Backtest unten zeigt, wie verlässlich die Methode bisher war.",
            className="alert alert-info",
        ),
        html.Div(  # Zeile mit den Auswahlfeldern
            [
                html.Div([html.Label("Coin"), dcc.Dropdown(id="forecast-coin", clearable=False)],  # Coin-Auswahl
                         className="control-wide"),
                html.Div(  # Prognosezeitraum
                    [
                        html.Label("Prognose für"),  # Beschriftung
                        dcc.RadioItems(  # Auswahl 7/14/30 Tage
                            id="forecast-horizon",
                            options=[{"label": f"{d} Tage", "value": d} for d in (7, 14, 30)],  # Drei Optionen
                            value=14,  # Standard: 14 Tage
                            inline=True,  # Nebeneinander
                            className="radio",
                        ),
                    ],
                    className="control",
                ),
            ],
            className="controls",
        ),
        dcc.Loading(html.Div(id="forecast-content"), type="circle"),  # Inhalt mit Lade-Kreisel
    ]
)


@callback(  # Füllt die Coin-Auswahlliste
    Output("forecast-coin", "options"),  # Ergebnis 1: Einträge
    Output("forecast-coin", "value"),  # Ergebnis 2: Auswahl
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
    State("forecast-coin", "value"),  # Bisherige Auswahl (nur lesen)
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
    ids = [option["value"] for option in options]  # Nur die IDs
    if current_coin in ids:  # Bisherige Auswahl noch gültig?
        return options, current_coin  # Beibehalten
    return options, "bitcoin" if "bitcoin" in ids else (ids[0] if ids else None)  # Sonst Bitcoin (oder erster Coin)


@callback(  # Berechnet Prognose und Backtest
    Output("forecast-content", "children"),  # Ergebnis: Seiteninhalt
    Input("forecast-coin", "value"),  # Auslöser: Coin
    Input("forecast-horizon", "value"),  # Auslöser: Zeitraum
    Input("currency", "value"),  # Auslöser: Währung
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
)
def update_forecast(coin_id, horizon, currency, _refresh):
    """Lädt die Historie, erstellt Prognose und Backtest und baut Kacheln und Diagramme.

    Args:
        coin_id: CoinGecko-ID, z. B. "bitcoin".
        horizon: Prognosezeitraum in Tagen (7, 14 oder 30).
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).

    Returns:
        Liste von Dash-Komponenten für den Seiteninhalt.
    """
    if not coin_id:  # Noch kein Coin gewählt
        return html.Div("Bitte einen Coin auswählen.", className="alert alert-info")  # Hinweis

    symbol = "€" if currency == "EUR" else "$"  # Währungszeichen
    result = data_loader.load_price_history(coin_id, currency.lower())  # 365 Tage Kursverlauf laden
    status = status_message(result, "Kursdaten")  # Statusmeldung
    if result.data is None:  # Keine Daten?
        return status  # Nur Fehlermeldung zeigen
    prices = result.data  # Kursreihe
    if len(prices) < 150:  # Zu wenig Historie (z. B. sehr neuer Coin)?
        return [status, html.Div("Für eine Prognose braucht es mindestens ca. 150 Tage Kursdaten.",
                                 className="alert alert-warning")]  # Ehrlich sagen, statt Unsinn zu rechnen

    prediction = forecast.make_forecast(prices, horizon)  # Prognose berechnen
    backtest = forecast.run_backtest(prices, horizon)  # Backtest berechnen
    better_than_baseline = backtest.hit_rate > backtest.baseline_hit_rate  # Schlägt das Modell die einfache Regel?

    return [  # Seiteninhalt von oben nach unten
        status,  # "Stand …" oder Warnung
        html.H2(f"Prognose für die nächsten {horizon} Tage"),  # Zwischenüberschrift
        html.Div(  # Kacheln zur Prognose
            [
                metric_card("Letzter Kurs", f"{format_price(prediction.last_price)} {symbol}"),  # Ausgangspunkt
                metric_card(f"Erwarteter Kurs in {horizon} Tagen",  # Kernergebnis
                            f"{format_price(prediction.predicted_price)} {symbol}",
                            format_percent(prediction.expected_return * 100), prediction.expected_return),
                metric_card("95-%-Band (Spanne)",  # Unsicherheit
                            f"{format_price(prediction.lower_price)} – {format_price(prediction.upper_price)} {symbol}",
                            help_text="In diesem Bereich lagen die Ergebnisse in der Vergangenheit in ca. 95 % der Fälle"),
            ],
            className="metrics",
        ),
        graph(charts.forecast_chart(prices.iloc[-HISTORY_DAYS_SHOWN:], prediction.path, currency)),  # Diagramm
        explanation(  # Erklärung der Methode
            "Wie funktioniert die Prognose?",
            "1. Für jeden Tag der Vergangenheit berechnen wir fünf **Merkmale**: RSI, MACD-Histogramm, "
            "Abstand zu SMA 20 und SMA 50 sowie das Momentum der letzten 14 Tage.\n"
            f"2. Wir wissen auch, wie sich der Kurs jeweils in den {horizon} Tagen **danach** entwickelt hat.\n"
            "3. Eine **lineare Regression** (Methode der kleinsten Quadrate) sucht die Gewichte, mit denen sich diese "
            "Entwicklung am besten aus den Merkmalen berechnen lässt.\n"
            "4. Mit diesen Gewichten und den Merkmalen von **heute** schätzen wir die nächsten Tage.\n\n"
            "Das orange Band zeigt die Unsicherheit: Es ist umso breiter, je größer die Fehler des Modells in der "
            "Vergangenheit waren, und wird mit der Zeit breiter.",
        ),
        html.H2("Backtest: Wie gut war die Methode in der Vergangenheit?"),  # Zwischenüberschrift
        html.Div(  # Kacheln zum Backtest
            [
                metric_card("Trefferquote Richtung", format_percent(backtest.hit_rate * 100, 1, False),
                            "besser als die einfache Regel" if better_than_baseline else "nicht besser als die einfache Regel",
                            1 if better_than_baseline else -1,  # Farbe: grün, wenn besser
                            "Wie oft lag das Modell bei steigt/fällt richtig?"),
                metric_card("Einfache Regel", format_percent(backtest.baseline_hit_rate * 100, 1, False),
                            help_text="Zum Vergleich: die bessere der Regeln „steigt immer“ bzw. „fällt immer“"),
                metric_card("Ø Abweichung", f"{format_percent(backtest.mean_abs_error * 100, 1, False)}-Punkte",
                            help_text="Durchschnittlicher Unterschied zwischen vorhergesagter und echter Rendite"),
                metric_card("Testtage", str(backtest.test_days),
                            help_text="An so vielen Tagen wurde die Prognose mit der Wirklichkeit verglichen"),
            ],
            className="metrics",
        ),
        graph(charts.backtest_chart(backtest.comparison, horizon)),  # Vergleich vorhergesagt vs. tatsächlich
        explanation(  # Erklärung des Backtests
            "Wie lese ich den Backtest?",
            "Wir tun so, als wäre es früher: Das Modell lernt nur mit den **ersten 70 %** der Daten und muss dann "
            "die restlichen Tage vorhersagen, die es nie gesehen hat.\n\n"
            "- **Trefferquote Richtung:** Wie oft hat das Modell richtig gesagt, ob der Kurs steigt oder fällt? "
            "50 % wäre so gut wie ein Münzwurf.\n"
            "- **Einfache Regel:** Man sagt einfach immer „steigt“ (oder immer „fällt“ – je nachdem, was im "
            "Testzeitraum öfter stimmte). Ein Modell ist nur dann nützlich, wenn es diese Regel **schlägt**. "
            "Ist die Quote gleich hoch, hat das Modell vermutlich fast immer dieselbe Richtung vorhergesagt.\n"
            "- **Diagramm:** Liegen blaue und orange Linie oft auf derselben Seite der Nulllinie, hat das Modell "
            "die Richtung getroffen.",
        ),
    ]
