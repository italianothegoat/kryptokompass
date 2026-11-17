"""
Was macht diese Datei?
----------------------
Ein kleines Testskript OHNE Website: Es ruft einmal Daten von CoinGecko ab,
speichert sie in der SQLite-Datenbank und liest sie wieder aus.
So seht ihr, ob API-Key, Internet und Datenbank funktionieren.

Starten mit:   python check_api.py
Verbraucht 3 API-Aufrufe.
"""

from datetime import datetime, timezone  # Für den aktuellen Zeitpunkt in UTC

from src import api_client, data_loader, database  # Unsere Module


def main() -> None:
    """Ruft Daten ab, speichert sie und gibt eine kurze Zusammenfassung aus."""
    api_key = data_loader.get_api_key()  # Key aus Umgebungsvariable oder secrets.toml besorgen
    if not api_key:  # Kein Key gefunden?
        print("Hinweis: Kein API-Key gefunden (secrets.toml fehlt) – teste ohne Key.")  # Info ausgeben
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
