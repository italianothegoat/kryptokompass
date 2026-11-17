"""
Was macht diese Datei?
----------------------
Sie ist der Startpunkt der KryptoKompass-Website (gebaut mit Dash, einem Web-Framework vom Plotly-Team).

Lokal starten:     python app.py          → im Browser http://127.0.0.1:8050 öffnen
Auf Render:        gunicorn app:server    → Render startet die Website mit diesem Befehl

Aufgaben dieser Datei:
- Die Dash-Website anlegen und alle Unterseiten aus dem Ordner app_pages/ einsammeln
- Datenbank-Tabellen anlegen (falls noch nicht vorhanden)
- Kopfzeile mit Menü, Währungswahl und "Daten aktualisieren" – auf ALLEN Seiten gleich
- Fußzeile mit Quellenangabe und "Keine Anlageberatung"

So funktioniert Dash in einem Satz: Das "layout" beschreibt, was auf der Seite steht,
und "Callbacks" sind Funktionen, die automatisch laufen, wenn sich eine Eingabe ändert
(z. B. Klick auf einen Button) – ihr Rückgabewert ersetzt dann einen Teil der Seite.
"""

from datetime import datetime  # Für die Uhrzeit in der Aktualisieren-Meldung

import dash  # dash: das Web-Framework
from dash import Input, Output, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import data_loader, database  # Unsere Module

app = dash.Dash(  # Die Website anlegen
    __name__,  # Name des Moduls – Dash findet darüber den Ordner assets/ (CSS)
    use_pages=True,  # Mehrere Unterseiten erlauben
    pages_folder="app_pages",  # Hier liegen die Unterseiten
    title="KryptoKompass",  # Titel im Browser-Tab
    suppress_callback_exceptions=True,  # Keine Fehler, weil nicht alle Seitenelemente gleichzeitig existieren
)
server = app.server  # Der Webserver dahinter (Flask) – Render startet ihn mit gunicorn

database.init_db()  # Tabellen anlegen, falls es sie noch nicht gibt

header = html.Header(  # Kopfzeile oben
    [
        dcc.Link("🧭 KryptoKompass", href="/", className="brand"),  # Logo/Name, führt zur Startseite
        html.Nav(  # Menü mit allen Unterseiten
            [
                dcc.Link(page["name"], href=page["relative_path"], className="nav-link")  # Ein Link je Seite
                for page in dash.page_registry.values()  # page_registry kennt alle registrierten Seiten
            ],
            className="nav",
        ),
        html.Div(  # Rechter Bereich: Währung und Aktualisieren
            [
                dcc.RadioItems(  # Auswahl EUR/USD
                    id="currency",  # Unter diesem Namen lesen die Unterseiten die Auswahl aus
                    options=["EUR", "USD"],  # Mögliche Werte
                    value="EUR",  # Standard: Euro
                    inline=True,  # Nebeneinander
                    persistence=True,  # Auswahl bleibt beim Seitenwechsel und Neuladen erhalten
                    className="radio",
                ),
                html.Button("🔄 Aktualisieren", id="refresh-button", className="button",  # Button
                            title="Zwischenspeicher leeren und frische Daten von CoinGecko holen"),
            ],
            className="header-tools",
        ),
        dcc.Store(id="refresh-store", data=0),  # Unsichtbarer Speicher: ändert sich bei jedem Klick → Seiten laden neu
    ],
    className="header",
)

footer = html.Footer(  # Fußzeile
    [
        html.Div(id="refresh-info", className="hint"),  # Platz für die Bestätigung nach "Aktualisieren"
        dcc.Markdown(
            "Daten von [CoinGecko](https://www.coingecko.com) · Marktdaten werden 10 Min., Kursverläufe 60 Min. "
            "zwischengespeichert · **Keine Anlageberatung** – alle Angaben und Prognosen ohne Gewähr, "
            "nur zu Lern- und Informationszwecken."
        ),
    ],
    className="footer",
)

app.layout = html.Div(  # Gesamtaufbau: Kopfzeile, Inhalt, Fußzeile
    [
        header,  # Kopfzeile mit Menü
        html.Main(dash.page_container, className="content"),  # page_container = die aktuell gewählte Unterseite
        footer,  # Fußzeile
    ]
)


@callback(  # Diese Funktion läuft bei jedem Klick auf "Aktualisieren"
    Output("refresh-store", "data"),  # Ergebnis 1: neuer Wert im unsichtbaren Speicher
    Output("refresh-info", "children"),  # Ergebnis 2: Bestätigungstext in der Fußzeile
    Input("refresh-button", "n_clicks"),  # Auslöser: Anzahl der Klicks hat sich geändert
    prevent_initial_call=True,  # Nicht beim ersten Laden der Seite ausführen
)
def refresh_data(n_clicks):
    """Leert den Zwischenspeicher, damit alle Seiten frische Daten von CoinGecko holen.

    Args:
        n_clicks: Wie oft der Button bisher geklickt wurde.

    Returns:
        Neuer Wert für den Speicher (löst Neuladen aus) und eine kurze Bestätigung.
    """
    data_loader.clear_cache()  # Zwischenspeicher leeren
    now = datetime.now().strftime("%H:%M:%S")  # Aktuelle Uhrzeit als Text
    return n_clicks, f"Zwischenspeicher geleert um {now} Uhr – Daten werden neu geladen."  # Beide Ausgaben


if __name__ == "__main__":  # Nur beim lokalen Start mit "python app.py" (nicht auf Render)
    app.run(debug=True)  # Entwicklungsserver starten; debug=True lädt bei Code-Änderungen automatisch neu
