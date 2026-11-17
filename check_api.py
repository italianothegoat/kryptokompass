"""
Was macht diese Datei?
----------------------
Ein kleines Testskript OHNE Streamlit: Es ruft einmal Daten von CoinGecko ab,
speichert sie in der SQLite-Datenbank und liest sie wieder aus.
So seht ihr, ob API-Key, Internet und Datenbank funktionieren.

Starten mit:   python check_api.py
Verbraucht 3 API-Aufrufe.
"""

import os  # os: prüfen, ob eine Datei existiert
import tomllib  # tomllib: liest .toml-Dateien (seit Python 3.11 eingebaut)
from datetime import datetime, timezone  # Für den aktuellen Zeitpunkt in UTC

from src import api_client, database  # Unsere Module

SECRETS_PATH = os.path.join(".streamlit", "secrets.toml")  # Wo die Geheimnis-Datei liegt


def read_api_key() -> str:
    """Liest den API-Key aus .streamlit/secrets.toml (falls vorhanden).

    Returns:
        Den Key oder einen leeren Text.
    """
    if not os.path.exists(SECRETS_PATH):  # Gibt es die Datei überhaupt?
        print("Hinweis: Keine .streamlit/secrets.toml gefunden – teste ohne API-Key.")  # Info ausgeben
        return ""  # Ohne Key weitermachen
    with open(SECRETS_PATH, "rb") as file:  # Datei im Binärmodus öffnen (verlangt tomllib so)
        secrets = tomllib.load(file)  # Inhalt als Dictionary einlesen
    return secrets.get("COINGECKO_API_KEY", "")  # Key zurückgeben (oder leer, falls Eintrag fehlt)


def main() -> None:
    """Ruft Daten ab, speichert sie und gibt eine kurze Zusammenfassung aus."""
    api_key = read_api_key()  # Key besorgen
    database.init_db()  # Tabellen anlegen, falls nötig
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")  # Aktueller Zeitpunkt in UTC als Text

    global_data = api_client.fetch_global_data("eur", api_key)  # 1. Aufruf: Gesamtmarkt
    print(f"Gesamte Marktkapitalisierung: {global_data['total_market_cap']:,.0f} EUR")  # Ausgabe
    print(f"BTC-Dominanz: {global_data['btc_dominance']:.1f} %")  # Ausgabe

    coins = api_client.fetch_top_coins("eur", api_key)  # 2. Aufruf: Top 20
    database.save_market_snapshot(coins, "eur", fetched_at)  # In der Datenbank speichern
    print("\nTop 5 Coins:")  # Überschrift (\n = Leerzeile davor)
    print(coins[["rank", "name", "price", "change_24h"]].head().to_string(index=False))  # Erste 5 Zeilen ausgeben

    history = api_client.fetch_price_history("bitcoin", "eur", api_key)  # 3. Aufruf: Bitcoin-Historie
    database.save_price_history(history, "bitcoin", "eur", fetched_at)  # Speichern
    loaded, _ = database.load_price_history("bitcoin", "eur")  # Zur Kontrolle wieder laden
    print(f"\nBitcoin-Historie: {len(loaded)} Tage in der Datenbank, "
          f"von {loaded.index[0]:%d.%m.%Y} bis {loaded.index[-1]:%d.%m.%Y}")  # Ausgabe mit Datumsformat
    print("\n✅ Alles funktioniert!")  # Erfolgsmeldung


if __name__ == "__main__":  # Nur ausführen, wenn die Datei direkt gestartet wird (nicht beim Import)
    main()  # Hauptfunktion aufrufen
