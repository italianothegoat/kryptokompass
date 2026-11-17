"""
Was macht diese Datei?
----------------------
Seite 1 – Marktübersicht.
Zeigt oben vier Kennzahlen-Kacheln (Gesamtmarkt, BTC-Dominanz, bester/schlechtester Coin)
und darunter eine durchsuchbare, sortierbare Tabelle der 20 größten Coins.
"""

import pandas as pd  # pandas: Tabelle für die Anzeige vorbereiten
import streamlit as st  # streamlit: Oberfläche

from src import data_loader  # Daten laden (live oder aus der Datenbank)
from src.formatting import format_big_number, format_german, format_percent, format_price  # Deutsche Zahlenformate

currency = st.session_state.get("currency", "EUR")  # Gewählte Währung aus der Seitenleiste (Standard EUR)
symbol = "€" if currency == "EUR" else "$"  # Passendes Währungszeichen

st.title("📊 Marktübersicht")  # Seitenüberschrift

coins_result = data_loader.load_top_coins(currency.lower())  # Top 20 laden (API erwartet "eur"/"usd")
global_result = data_loader.load_global_data(currency.lower())  # Gesamtmarkt-Kennzahlen laden
data_loader.show_load_status(coins_result, "Marktdaten")  # Stand anzeigen bzw. warnen/abbrechen
coins = coins_result.data  # Die eigentliche Tabelle herausholen

# ---------- Kennzahlen-Kacheln ----------
col1, col2, col3, col4 = st.columns(4)  # Vier gleich breite Spalten nebeneinander

if global_result.data is not None:  # Nur anzeigen, wenn Gesamtmarkt-Daten vorhanden sind
    global_data = global_result.data  # Dictionary mit den Gesamtmarkt-Werten
    col1.metric(  # Kachel 1: gesamte Marktkapitalisierung
        "Marktkapitalisierung",  # Beschriftung (kurz, damit sie in die Kachel passt)
        f"{format_big_number(global_data['total_market_cap'])} {symbol}",  # Hauptwert, z. B. "2,85 Bio. €"
        f"{format_percent(global_data['market_cap_change_24h'])} (24 h)",  # Veränderung (grün/rot mit Pfeil)
        help="Gesamtwert aller Kryptowährungen zusammen",  # Erklärung beim Darüberfahren
    )
    col2.metric("BTC-Dominanz", format_percent(global_data["btc_dominance"], 1, False))  # Kachel 2: BTC-Anteil
else:  # Gesamtmarkt-Daten fehlen komplett
    col1.metric("Marktkapitalisierung", "–")  # Platzhalter-Strich statt Absturz
    col2.metric("BTC-Dominanz", "–")  # Platzhalter-Strich

best = coins.loc[coins["change_24h"].idxmax()]  # Zeile mit der höchsten 24-h-Veränderung
worst = coins.loc[coins["change_24h"].idxmin()]  # Zeile mit der niedrigsten 24-h-Veränderung
col3.metric("Top-Gewinner 24 h", best["name"], format_percent(best["change_24h"]),  # Kachel 3: bester Coin
            help="Bester Coin der letzten 24 h unter den Top 20")  # Erklärung beim Darüberfahren (Fragezeichen-Symbol)
col4.metric("Top-Verlierer 24 h", worst["name"], format_percent(worst["change_24h"]),  # Kachel 4: schlechtester Coin
            help="Schlechtester Coin der letzten 24 h unter den Top 20")  # Erklärung beim Darüberfahren

# ---------- Tabelle der Top 20 ----------
st.subheader("Top 20 nach Marktkapitalisierung")  # Zwischenüberschrift

search = st.text_input("🔎 Suche nach Name oder Symbol", placeholder="z. B. Solana oder SOL")  # Suchfeld
if search:  # Nur filtern, wenn etwas eingetippt wurde
    matches_name = coins["name"].str.contains(search, case=False, regex=False)  # Treffer im Namen (Groß/klein egal)
    matches_symbol = coins["symbol"].str.contains(search, case=False, regex=False)  # Treffer im Symbol
    coins = coins[matches_name | matches_symbol]  # Nur Zeilen behalten, die irgendwo passen

table = pd.DataFrame(  # Neue Tabelle mit deutschen Spaltennamen für die Anzeige
    {
        "Rang": coins["rank"],  # Rang
        "Name": coins["name"],  # Name
        "Symbol": coins["symbol"],  # Kürzel
        f"Preis ({symbol})": coins["price"],  # Aktueller Preis
        "24 h %": coins["change_24h"],  # Veränderung 24 Stunden
        "7 T %": coins["change_7d"],  # Veränderung 7 Tage
        "30 T %": coins["change_30d"],  # Veränderung 30 Tage
        f"Marktkap. ({symbol})": coins["market_cap"],  # Marktkapitalisierung
        f"Volumen 24 h ({symbol})": coins["volume_24h"],  # Handelsvolumen
        "Vol./MKap. %": coins["volume_24h"] / coins["market_cap"] * 100,  # Wie viel % der Marktkap. heute gehandelt wurde
        "Abstand ATH %": coins["ath_change"],  # ATH = All-Time-High (Allzeithoch)
    }
)

change_columns = ["24 h %", "7 T %", "30 T %", "Abstand ATH %"]  # Diese Spalten sollen grün/rot werden


def color_change(value: float) -> str:
    """Gibt für positive Werte grüne und für negative Werte rote Schrift zurück (CSS).

    Args:
        value: Eine Prozent-Veränderung.

    Returns:
        CSS-Anweisung als Text, z. B. "color: #16a34a".
    """
    if pd.isna(value):  # Fehlender Wert (kommt bei ganz neuen Coins vor)
        return ""  # Keine Färbung
    return "color: #16a34a" if value >= 0 else "color: #dc2626"  # Grün bei ≥ 0, sonst rot


styled = table.style.map(color_change, subset=change_columns)  # Färbefunktion auf jede Zelle dieser Spalten anwenden
styled = styled.format(  # Anzeigeformat pro Spalte – die Zahlen dahinter bleiben echte Zahlen (wichtig fürs Sortieren)
    {
        f"Preis ({symbol})": format_price,  # Preis mit 2 oder 4 Nachkommastellen
        "24 h %": lambda v: format_german(v, 2, True),  # "lambda" = kleine Funktion ohne Namen
        "7 T %": lambda v: format_german(v, 2, True),  # Mit Vorzeichen
        "30 T %": lambda v: format_german(v, 2, True),  # Mit Vorzeichen
        f"Marktkap. ({symbol})": lambda v: format_german(v, 0),  # Ganze Zahl mit Tausenderpunkten
        f"Volumen 24 h ({symbol})": lambda v: format_german(v, 0),  # Ganze Zahl mit Tausenderpunkten
        "Vol./MKap. %": lambda v: format_german(v, 2),  # 2 Nachkommastellen
        "Abstand ATH %": lambda v: format_german(v, 2),  # 2 Nachkommastellen
    }
)  # Hinweis: Fehlende Werte (bei ganz neuen Coins) zeigt Streamlit immer grau als "None" an

st.dataframe(  # Tabelle anzeigen – Klick auf eine Spaltenüberschrift sortiert sie
    styled,  # Die gefärbte und formatierte Tabelle
    hide_index=True,  # Die interne Zeilennummer ausblenden
    width="stretch",  # Volle Breite nutzen
    height=740,  # Hoch genug für alle 20 Zeilen ohne Scrollen
)
st.caption("Tipp: Klick auf eine Spaltenüberschrift sortiert die Tabelle.")  # Bedienhinweis
