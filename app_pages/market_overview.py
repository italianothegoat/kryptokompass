"""
Was macht diese Datei?
----------------------
Unterseite "Markt" (Adresse "/markt").
Zeigt oben vier Kennzahlen-Kacheln (Gesamtmarkt, BTC-Dominanz, bester/schlechtester Coin)
und darunter eine durchsuchbare, sortierbare Tabelle der 20 größten Coins.

Die Tabelle ist ein "AG Grid" (dash-ag-grid). Sortieren per Klick auf die Spaltenüberschrift
und Grün/Rot-Färbung bringt es selbst mit. Zahlenformat und Farben werden als kleine
JavaScript-Ausdrücke angegeben, weil die Tabelle im Browser gezeichnet wird.
"""

import dash  # dash: Seite registrieren
import dash_ag_grid as dag  # dash-ag-grid: leistungsfähige Tabelle
from dash import Input, Output, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import data_loader  # Daten laden
from src.components import metric_card, status_message  # Wiederverwendbare Bausteine
from src.formatting import format_big_number, format_percent  # Deutsche Zahlenformate

dash.register_page(__name__, path="/markt", name="Markt", order=1,  # Seite bei Dash anmelden
                   title="Markt · KryptoKompass")  # Titel im Browser-Tab


def german_number(decimals: int, show_sign: bool = False) -> dict:
    """Baut ein Zahlenformat für eine Tabellenspalte (deutsche Schreibweise, im Browser berechnet).

    Args:
        decimals: Anzahl Nachkommastellen.
        show_sign: True = immer Vorzeichen (+/−) anzeigen.

    Returns:
        Dictionary im Format, das AG Grid für "valueFormatter" erwartet.
    """
    sign = "exceptZero" if show_sign else "auto"  # JavaScript-Option für das Vorzeichen
    return {  # "function" = JavaScript-Ausdruck; params.value ist der Zellwert
        "function": f"params.value == null ? '–' : params.value.toLocaleString('de-DE', "
                    f"{{minimumFractionDigits: {decimals}, maximumFractionDigits: {decimals}, signDisplay: '{sign}'}})"
    }


PRICE_FORMAT = {  # Preise unter 1 mit 4 Nachkommastellen (z. B. 0,1834), sonst mit 2
    "function": "params.value == null ? '–' : params.value.toLocaleString('de-DE', "
                "{minimumFractionDigits: params.value < 1 ? 4 : 2, maximumFractionDigits: params.value < 1 ? 4 : 2})"
}
GREEN_RED = {  # Schriftfarbe abhängig vom Wert: grün bei > 0, rot bei < 0
    "styleConditions": [
        {"condition": "params.value > 0", "style": {"color": "#16a34a"}},
        {"condition": "params.value < 0", "style": {"color": "#dc2626"}},
    ]
}


def column_definitions(symbol: str) -> list:
    """Beschreibt alle Spalten der Tabelle (Überschrift, Datenfeld, Format, Farbe).

    Args:
        symbol: Währungszeichen "€" oder "$" für die Überschriften.

    Returns:
        Liste von Spaltenbeschreibungen für AG Grid.
    """
    return [
        {"headerName": "Rang", "field": "rank", "width": 80},  # Rang nach Marktkapitalisierung
        {"headerName": "Name", "field": "name", "minWidth": 130},  # Name
        {"headerName": "Symbol", "field": "symbol", "width": 100},  # Kürzel
        {"headerName": f"Preis ({symbol})", "field": "price", "valueFormatter": PRICE_FORMAT, "type": "rightAligned"},
        {"headerName": "24 h %", "field": "change_24h", "valueFormatter": german_number(2, True),
         "cellStyle": GREEN_RED, "type": "rightAligned"},  # Veränderung 24 h, grün/rot
        {"headerName": "7 T %", "field": "change_7d", "valueFormatter": german_number(2, True),
         "cellStyle": GREEN_RED, "type": "rightAligned"},  # Veränderung 7 Tage
        {"headerName": "30 T %", "field": "change_30d", "valueFormatter": german_number(2, True),
         "cellStyle": GREEN_RED, "type": "rightAligned"},  # Veränderung 30 Tage
        {"headerName": f"Marktkap. ({symbol})", "field": "market_cap", "valueFormatter": german_number(0),
         "type": "rightAligned", "minWidth": 170},  # Marktkapitalisierung (breiter, große Zahlen)
        {"headerName": f"Volumen 24 h ({symbol})", "field": "volume_24h", "valueFormatter": german_number(0),
         "type": "rightAligned", "minWidth": 170},  # Handelsvolumen (breiter, große Zahlen)
        {"headerName": "Vol./MKap. %", "field": "vol_mcap", "valueFormatter": german_number(2),
         "type": "rightAligned"},  # Wie viel % der Marktkapitalisierung heute gehandelt wurde
        {"headerName": "Abstand ATH %", "field": "ath_change", "valueFormatter": german_number(2),
         "cellStyle": GREEN_RED, "type": "rightAligned"},  # Abstand zum Allzeithoch
    ]


layout = html.Div(  # Aufbau der Seite (Inhalte werden per Callback eingefüllt)
    [
        html.H1("📊 Marktübersicht"),  # Seitenüberschrift
        html.Div(id="market-status"),  # Platz für "Stand …" bzw. Warnungen
        html.Div(id="market-metrics", className="metrics"),  # Platz für die vier Kacheln
        html.H2("Top 20 nach Marktkapitalisierung"),  # Zwischenüberschrift
        dcc.Input(  # Suchfeld
            id="market-search",
            type="text",
            placeholder="🔎 Suche nach Name oder Symbol, z. B. Solana oder SOL",
            className="search",
        ),
        dag.AgGrid(  # Die Tabelle
            id="market-grid",
            rowData=[],  # Wird per Callback gefüllt
            columnDefs=column_definitions("€"),  # Startwerte, werden je nach Währung ersetzt
            defaultColDef={"sortable": True, "resizable": True, "flex": 1},  # Alle Spalten sortierbar und gleichmäßig breit
            dashGridOptions={"domLayout": "autoHeight"},  # Tabelle so hoch wie nötig, kein eigener Scrollbalken
        ),
        html.P("Tipp: Klick auf eine Spaltenüberschrift sortiert die Tabelle.", className="hint"),  # Bedienhinweis
    ]
)


@callback(  # Läuft beim Öffnen der Seite, bei Währungswechsel und nach "Daten aktualisieren"
    Output("market-status", "children"),  # Statusmeldung
    Output("market-metrics", "children"),  # Kacheln
    Output("market-grid", "rowData"),  # Tabellenzeilen
    Output("market-grid", "columnDefs"),  # Spalten (Überschriften mit Währungszeichen)
    Input("currency", "value"),  # Auslöser 1: Währung
    Input("refresh-store", "data"),  # Auslöser 2: "Daten aktualisieren" wurde geklickt
)
def update_market(currency, _refresh):
    """Lädt Markt- und Gesamtmarktdaten und baut Kacheln und Tabelle.

    Args:
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (wird nur als Auslöser gebraucht).

    Returns:
        Statusmeldung, Liste der Kacheln, Tabellenzeilen und Spaltenbeschreibungen.
    """
    symbol = "€" if currency == "EUR" else "$"  # Passendes Währungszeichen
    coins_result = data_loader.load_top_coins(currency.lower())  # Top 20 laden
    global_result = data_loader.load_global_data(currency.lower())  # Gesamtmarkt laden
    status = status_message(coins_result, "Marktdaten")  # Statusmeldung bauen

    if coins_result.data is None:  # Gar keine Coin-Daten?
        return status, [], [], column_definitions(symbol)  # Nur die Fehlermeldung zeigen

    coins = coins_result.data.copy()  # Kopie, damit wir die zwischengespeicherte Tabelle nicht verändern
    coins["vol_mcap"] = coins["volume_24h"] / coins["market_cap"] * 100  # Verhältnis Volumen/Marktkap. in %

    cards = []  # Liste der Kacheln
    if global_result.data is not None:  # Gesamtmarkt-Daten vorhanden?
        global_data = global_result.data  # Dictionary mit den Werten
        cards.append(metric_card(  # Kachel 1: Marktkapitalisierung
            "Marktkapitalisierung",
            f"{format_big_number(global_data['total_market_cap'])} {symbol}",
            f"{format_percent(global_data['market_cap_change_24h'])} (24 h)",
            global_data["market_cap_change_24h"],
            "Gesamtwert aller Kryptowährungen zusammen",
        ))
        cards.append(metric_card("BTC-Dominanz", format_percent(global_data["btc_dominance"], 1, False),  # Kachel 2
                                 help_text="Anteil von Bitcoin an der gesamten Marktkapitalisierung"))
    else:  # Gesamtmarkt-Daten fehlen
        cards.append(metric_card("Marktkapitalisierung", "–"))  # Platzhalter statt Absturz
        cards.append(metric_card("BTC-Dominanz", "–"))  # Platzhalter
        status = html.Div([status, html.Div(  # Zusätzlich eine Warnung mit dem Grund anzeigen
            f"Gesamtmarkt-Daten fehlen gerade: {global_result.error_message}", className="alert alert-warning")])

    best = coins.loc[coins["change_24h"].idxmax()]  # Zeile mit der höchsten 24-h-Veränderung
    worst = coins.loc[coins["change_24h"].idxmin()]  # Zeile mit der niedrigsten 24-h-Veränderung
    cards.append(metric_card("Top-Gewinner 24 h", best["name"], format_percent(best["change_24h"]),  # Kachel 3
                             best["change_24h"], "Bester Coin der letzten 24 h unter den Top 20"))
    cards.append(metric_card("Top-Verlierer 24 h", worst["name"], format_percent(worst["change_24h"]),  # Kachel 4
                             worst["change_24h"], "Schlechtester Coin der letzten 24 h unter den Top 20"))

    rows = coins.astype(object).where(coins.notna(), None).to_dict("records")  # Tabelle → Liste von Zeilen; NaN → None (leer)
    return status, cards, rows, column_definitions(symbol)  # Alles an die Seite zurückgeben


@callback(  # Läuft bei jeder Eingabe im Suchfeld
    Output("market-grid", "dashGridOptions"),  # Ergebnis: Tabellen-Optionen inkl. Suchtext
    Input("market-search", "value"),  # Auslöser: Text im Suchfeld
)
def search_table(search_text):
    """Filtert die Tabelle nach dem Suchtext (AG Grid sucht dann in allen Spalten).

    Args:
        search_text: Eingabe im Suchfeld (oder None).

    Returns:
        Tabellen-Optionen mit dem Suchtext als "quickFilterText".
    """
    return {"domLayout": "autoHeight", "quickFilterText": search_text or ""}  # Leerer Text = alles anzeigen
