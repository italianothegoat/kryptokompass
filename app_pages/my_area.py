"""
Was macht diese Datei?
----------------------
Unterseite "Mein Bereich" (Adresse "/mein-bereich") – für jede angemeldete Person anders.

Hier kann man:
- seine Lieblingswährung festlegen (wird beim nächsten Laden der Website vorausgewählt)
- eine eigene Watchlist mit bis zu 10 Coins anlegen und deren aktuelle Kurse sehen

Alles wird in der Benutzerdatenbank gespeichert (siehe src/users.py) und ist damit
auch nach dem Abmelden und auf anderen Geräten wieder da.
"""

import dash  # dash: Seite registrieren
from dash import Input, Output, callback, dcc, html  # Bausteine für Layout und Callbacks

from src import auth, data_loader, users  # Login, Daten, Benutzerdatenbank
from src.components import coin_options, metric_card, status_message  # Bausteine
from src.formatting import format_percent, format_price  # Deutsche Zahlenformate

dash.register_page(__name__, path="/mein-bereich", name="Mein Bereich", order=5,  # Seite bei Dash anmelden
                   title="Mein Bereich · KryptoKompass")  # Titel im Browser-Tab


def layout(**_kwargs):
    """Baut die Seite – als FUNKTION, damit sie bei jedem Aufruf die Daten der angemeldeten Person zeigt.

    Args:
        _kwargs: Zusätzliche Angaben aus der Adresse (werden hier nicht gebraucht).

    Returns:
        Der Seiteninhalt.
    """
    username = auth.current_user()  # Wer ist angemeldet?
    if not username:  # Beim Programmstart gibt es niemanden – dann nur eine leere Hülle liefern
        return html.Div()  # Leerer Platzhalter
    currency = users.get_currency(username)  # Gespeicherte Lieblingswährung
    options, _ = coin_options(currency)  # Auswahlliste der Top-20-Coins
    watchlist = [cid for cid in users.get_watchlist(username)  # Gespeicherte Watchlist …
                 if cid in {option["value"] for option in options}]  # … nur Coins, die in der Liste vorkommen
    return html.Div(  # Aufbau der Seite
        [
            html.H1(f"👤 Hallo, {username}!"),  # Persönliche Begrüßung
            html.P("Das ist dein persönlicher Bereich. Deine Einstellungen werden automatisch gespeichert.",
                   className="lead"),
            html.H2("Lieblingswährung"),  # Zwischenüberschrift
            dcc.RadioItems(  # Auswahl EUR/USD
                id="my-currency",
                options=list(users.CURRENCIES),  # "EUR" und "USD"
                value=currency,  # Gespeicherter Wert
                inline=True,  # Nebeneinander
                className="radio",
            ),
            html.Div(id="my-currency-info", className="hint"),  # Platz für "Gespeichert"
            html.H2("Meine Watchlist"),  # Zwischenüberschrift
            dcc.Dropdown(  # Mehrfachauswahl der Lieblings-Coins
                id="my-watchlist",
                options=options,  # Top-20-Coins
                value=watchlist,  # Gespeicherte Auswahl
                multi=True,  # Mehrere wählbar
                placeholder="Coins auswählen, z. B. Bitcoin, Solana …",
            ),
            html.Div(id="my-watchlist-info", className="hint"),  # Platz für "Gespeichert"
            dcc.Loading(html.Div(id="my-watchlist-cards"), type="circle"),  # Kacheln mit Kursen
        ]
    )


@callback(  # Speichert die Lieblingswährung, sobald sie geändert wird
    Output("my-currency-info", "children"),  # Ergebnis 1: Bestätigung
    Output("currency", "value", allow_duplicate=True),  # Ergebnis 2: Währung oben in der Kopfzeile gleich mit umstellen
    Input("my-currency", "value"),  # Auslöser: neue Auswahl
    prevent_initial_call=True,  # Nicht beim Öffnen der Seite ausführen (da hat sich nichts geändert)
)
def save_currency(currency):
    """Speichert die Lieblingswährung der angemeldeten Person.

    Args:
        currency: "EUR" oder "USD".

    Returns:
        Bestätigungstext und die Währung für die Kopfzeile.
    """
    users.set_currency(auth.current_user(), currency)  # In der Datenbank speichern
    return f"✔ Gespeichert: {currency} ist jetzt deine Lieblingswährung.", currency  # Bestätigung + Kopfzeile


@callback(  # Speichert die Watchlist, sobald sie geändert wird
    Output("my-watchlist-info", "children"),  # Ergebnis: Bestätigung
    Input("my-watchlist", "value"),  # Auslöser: neue Auswahl
    prevent_initial_call=True,  # Nicht beim Öffnen der Seite ausführen
)
def save_watchlist(coin_ids):
    """Speichert die Watchlist der angemeldeten Person.

    Args:
        coin_ids: Liste der gewählten Coin-IDs.

    Returns:
        Bestätigungstext.
    """
    coin_ids = coin_ids or []  # None (nichts gewählt) wie leere Liste behandeln
    users.set_watchlist(auth.current_user(), coin_ids)  # In der Datenbank speichern
    if len(coin_ids) > users.MAX_WATCHLIST:  # Mehr als erlaubt gewählt?
        return f"⚠ Gespeichert wurden nur die ersten {users.MAX_WATCHLIST} Coins."  # Hinweis
    return "✔ Watchlist gespeichert."  # Bestätigung


@callback(  # Zeigt zu jedem Coin der Watchlist eine Kachel mit aktuellem Kurs
    Output("my-watchlist-cards", "children"),  # Ergebnis: Kacheln
    Input("my-watchlist", "value"),  # Auslöser: Auswahl
    Input("currency", "value"),  # Auslöser: Währung in der Kopfzeile
    Input("refresh-store", "data"),  # Auslöser: Aktualisieren
)
def show_watchlist(coin_ids, currency, _refresh):
    """Baut für jeden Coin der Watchlist eine Kachel mit Preis und Veränderungen.

    Args:
        coin_ids: Liste der gewählten Coin-IDs.
        currency: "EUR" oder "USD".
        _refresh: Zähler der Aktualisieren-Klicks (nur Auslöser).

    Returns:
        Statusmeldung und Kacheln – oder ein Hinweis bei leerer Watchlist.
    """
    if not coin_ids:  # Noch nichts ausgewählt?
        return html.Div("Deine Watchlist ist noch leer. Wähle oben ein paar Coins aus.", className="alert alert-info")
    symbol = "€" if currency == "EUR" else "$"  # Währungszeichen
    result = data_loader.load_top_coins(currency.lower())  # Aktuelle Marktdaten (meist aus dem Zwischenspeicher)
    if result.data is None:  # Keine Daten verfügbar?
        return status_message(result, "Marktdaten")  # Fehlermeldung zeigen
    coins = result.data.set_index("coin_id")  # Tabelle nach Coin-ID durchsuchbar machen
    cards = []  # Liste der Kacheln
    for coin_id in coin_ids:  # Für jeden Coin der Watchlist …
        if coin_id not in coins.index:  # … der (gerade) nicht in den Top 20 ist,
            continue  # überspringen
        coin = coins.loc[coin_id]  # Zeile mit den Daten dieses Coins
        cards.append(metric_card(  # Kachel bauen
            f"{coin['name']} ({coin['symbol']})",  # Überschrift
            f"{format_price(coin['price'])} {symbol}",  # Aktueller Preis
            f"{format_percent(coin['change_24h'])} (24 h) · {format_percent(coin['change_7d'])} (7 T)",  # Veränderungen
            coin["change_24h"],  # Farbe nach 24-h-Veränderung
        ))
    return [status_message(result, "Marktdaten"), html.Div(cards, className="metrics")]  # Stand + Kacheln
