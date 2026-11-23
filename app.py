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

import threading  # threading: etwas zeitversetzt im Hintergrund ausführen (Browser öffnen)
import webbrowser  # webbrowser: öffnet eine Adresse im Standard-Browser
from datetime import datetime  # Für die Uhrzeit in der Aktualisieren-Meldung

import dash  # dash: das Web-Framework
from dash import Input, Output, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import auth, data_loader, database, users  # Unsere Module

app = dash.Dash(  # Die Website anlegen
    __name__,  # Name des Moduls – Dash findet darüber den Ordner assets/ (CSS)
    use_pages=True,  # Mehrere Unterseiten erlauben
    pages_folder="app_pages",  # Hier liegen die Unterseiten
    title="KryptoKompass",  # Titel im Browser-Tab
    suppress_callback_exceptions=True,  # Keine Fehler, weil nicht alle Seitenelemente gleichzeitig existieren
)
server = app.server  # Der Webserver dahinter (Flask) – Render startet ihn mit gunicorn

database.init_db()  # Tabellen für Kursdaten anlegen, falls es sie noch nicht gibt
auth.setup_auth(server)  # Login, Registrierung, Abmelden und "Türsteher" einrichten (siehe src/auth.py)


def build_header(username: str | None, currency: str) -> html.Header:
    """Baut die Kopfzeile – mit dem Namen der angemeldeten Person und ihrer Lieblingswährung.

    Args:
        username: Benutzername oder None.
        currency: Vorausgewählte Währung ("EUR" oder "USD").

    Returns:
        Die fertige Kopfzeile.
    """
    return html.Header(  # Kopfzeile oben
        [
            dcc.Link("🧭 KryptoKompass", href="/", className="brand"),  # Logo/Name, führt zur Startseite
            html.Nav(  # Menü mit allen Unterseiten
                [
                    dcc.Link(page["name"], href=page["relative_path"], className="nav-link")  # Ein Link je Seite
                    for page in dash.page_registry.values()  # page_registry kennt alle registrierten Seiten
                ],
                className="nav",
            ),
            html.Div(  # Rechter Bereich: Währung, Aktualisieren, Benutzer
                [
                    dcc.RadioItems(  # Auswahl EUR/USD
                        id="currency",  # Unter diesem Namen lesen die Unterseiten die Auswahl aus
                        options=["EUR", "USD"],  # Mögliche Werte
                        value=currency,  # Start: Lieblingswährung der angemeldeten Person
                        inline=True,  # Nebeneinander
                        className="radio",
                    ),
                    html.Button("🔄 Aktualisieren", id="refresh-button", className="button",  # Button
                                title="Zwischenspeicher leeren und frische Daten von CoinGecko holen"),
                    html.Span(f"👤 {username}", className="user-badge") if username else None,  # Wer ist angemeldet?
                    html.A("Abmelden", href="/logout", className="button"),  # html.A = echter Link (lädt Seite neu)
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

def serve_layout() -> html.Div:
    """Baut den Gesamtaufbau der Seite – bei JEDEM Laden neu, damit er zur angemeldeten Person passt.

    Returns:
        Kopfzeile, aktuelle Unterseite und Fußzeile.
    """
    username = auth.current_user()  # Wer ist angemeldet? (None beim Programmstart)
    currency = users.get_currency(username) if username else "EUR"  # Lieblingswährung aus der Datenbank
    return html.Div(  # Gesamtaufbau: Kopfzeile, Inhalt, Fußzeile
        [
            build_header(username, currency),  # Kopfzeile mit Menü und Benutzer
            html.Main(dash.page_container, className="content"),  # page_container = die aktuell gewählte Unterseite
            footer,  # Fußzeile
        ]
    )


app.layout = serve_layout  # OHNE Klammern: Dash ruft die Funktion bei jedem Laden der Seite selbst auf


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
    LOCAL_URL = "http://127.0.0.1:8050"  # Adresse der Website auf dem eigenen Rechner
    print(f"\n🧭 KryptoKompass startet … Website: {LOCAL_URL}")  # Deutliche Meldung im Terminal
    print("   Der Browser öffnet sich gleich von selbst. Beenden mit Strg+C (oder rotes Quadrat in PyCharm).\n")
    threading.Timer(2, webbrowser.open, args=[LOCAL_URL]).start()  # Nach 2 Sekunden den Browser öffnen
    app.run(debug=True, use_reloader=False)  # Server starten; debug=True zeigt Fehler im Browser an
    # use_reloader=False: nur EIN Prozess (sonst öffnet sich der Browser doppelt).
    # Nach Code-Änderungen die Website deshalb einmal stoppen und neu starten.
