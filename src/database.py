"""
Was macht diese Datei?
----------------------
Sie speichert abgerufene Daten in einer kleinen SQLite-Datenbank und liest sie wieder aus.

SQLite ist eine Datenbank, die komplett in EINER Datei steckt (data/kryptokompass.db).
Man braucht keinen Server, Python bringt das Modul sqlite3 schon mit.

Wir haben drei Tabellen:
- market_snapshots: Momentaufnahmen der Top-20-Tabelle (jeder Abruf = neue Zeilen)
- global_snapshots: Momentaufnahmen der Gesamtmarkt-Kennzahlen
- price_history:    Tageskurse pro Coin und Währung (ein Wert pro Tag, wird überschrieben)

Wozu? Wenn CoinGecko ausfällt oder das Limit erreicht ist, zeigt die App die
zuletzt gespeicherten Daten an, statt abzustürzen.

Hinweis Streamlit Cloud: Die Datei liegt dort auf einer "flüchtigen" Festplatte.
Bei jedem Neustart der App (z. B. nach einem Push) ist sie wieder leer.
Für Version 1 ist das okay, weil sie nur Zwischenspeicher/Notfallreserve ist –
die Originaldaten liegen ja jederzeit bei CoinGecko.
"""

import os  # os: Arbeiten mit Ordnern und Dateipfaden
import sqlite3  # sqlite3: Pythons eingebaute SQLite-Datenbank

import pandas as pd  # pandas: Tabellen lesen und schreiben

DB_PATH = os.path.join("data", "kryptokompass.db")  # Standard-Speicherort der Datenbankdatei


def _connect(db_path: str) -> sqlite3.Connection:
    """Öffnet eine Verbindung zur Datenbankdatei (legt den Ordner bei Bedarf an).

    Args:
        db_path: Pfad zur Datenbankdatei.

    Returns:
        Eine offene Verbindung. Wer sie öffnet, muss sie mit .close() wieder schließen.
    """
    folder = os.path.dirname(db_path)  # Ordneranteil des Pfads, z. B. "data"
    if folder:  # Nur wenn es überhaupt einen Ordner im Pfad gibt …
        os.makedirs(folder, exist_ok=True)  # … diesen anlegen (kein Fehler, falls er schon existiert)
    return sqlite3.connect(db_path)  # Verbindung öffnen (Datei wird angelegt, falls sie fehlt)


def init_db(db_path: str = DB_PATH) -> None:
    """Legt alle Tabellen an, falls sie noch nicht existieren.

    Kann gefahrlos bei jedem Start aufgerufen werden ("IF NOT EXISTS").

    Args:
        db_path: Pfad zur Datenbankdatei.
    """
    conn = _connect(db_path)  # Verbindung öffnen
    try:  # try/finally: Verbindung wird garantiert geschlossen, auch bei Fehlern
        conn.execute(  # Tabelle für die Top-20-Momentaufnahmen anlegen
            """
            CREATE TABLE IF NOT EXISTS market_snapshots (
                fetched_at TEXT,      -- Zeitpunkt des Abrufs (UTC, ISO-Format)
                currency   TEXT,      -- "eur" oder "usd"
                coin_id    TEXT,      -- z. B. "bitcoin"
                name       TEXT,      -- z. B. "Bitcoin"
                symbol     TEXT,      -- z. B. "BTC"
                rank       INTEGER,   -- Rang nach Marktkapitalisierung
                price      REAL,      -- Preis
                change_24h REAL,      -- Veränderung 24 h in %
                change_7d  REAL,      -- Veränderung 7 Tage in %
                change_30d REAL,      -- Veränderung 30 Tage in %
                market_cap REAL,      -- Marktkapitalisierung
                volume_24h REAL,      -- Handelsvolumen 24 h
                ath_change REAL       -- Abstand zum Allzeithoch in %
            )
            """
        )
        conn.execute(  # Tabelle für die Gesamtmarkt-Kennzahlen anlegen
            """
            CREATE TABLE IF NOT EXISTS global_snapshots (
                fetched_at            TEXT,  -- Zeitpunkt des Abrufs
                currency              TEXT,  -- "eur" oder "usd"
                total_market_cap      REAL,  -- gesamte Marktkapitalisierung
                market_cap_change_24h REAL,  -- Veränderung 24 h in %
                btc_dominance         REAL   -- BTC-Anteil in %
            )
            """
        )
        conn.execute(  # Tabelle für die Kurshistorie anlegen
            """
            CREATE TABLE IF NOT EXISTS price_history (
                coin_id    TEXT,  -- z. B. "bitcoin"
                currency   TEXT,  -- "eur" oder "usd"
                date       TEXT,  -- Tag im Format JJJJ-MM-TT
                price      REAL,  -- Kurs an diesem Tag
                fetched_at TEXT,  -- wann dieser Wert abgerufen wurde
                PRIMARY KEY (coin_id, currency, date)  -- pro Coin/Währung/Tag nur EINE Zeile
            )
            """
        )
        conn.commit()  # Änderungen dauerhaft in die Datei schreiben
    finally:
        conn.close()  # Verbindung schließen


def save_market_snapshot(df: pd.DataFrame, currency: str, fetched_at: str, db_path: str = DB_PATH) -> None:
    """Speichert die Top-Coins-Tabelle als neue Momentaufnahme.

    Args:
        df: Tabelle aus api_client.fetch_top_coins().
        currency: "eur" oder "usd".
        fetched_at: Zeitpunkt des Abrufs als Text (UTC, ISO-Format).
        db_path: Pfad zur Datenbankdatei.
    """
    to_save = df.copy()  # Kopie anlegen, damit wir das Original nicht verändern
    to_save.insert(0, "currency", currency)  # Spalte "currency" vorne einfügen
    to_save.insert(0, "fetched_at", fetched_at)  # Spalte "fetched_at" ganz vorne einfügen
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        to_save.to_sql("market_snapshots", conn, if_exists="append", index=False)  # Zeilen an Tabelle anhängen
    finally:
        conn.close()  # Verbindung schließen


def load_latest_market_snapshot(currency: str, db_path: str = DB_PATH):
    """Lädt die neueste gespeicherte Top-Coins-Tabelle für eine Währung.

    Args:
        currency: "eur" oder "usd".
        db_path: Pfad zur Datenbankdatei.

    Returns:
        Tupel (DataFrame, fetched_at) – oder (None, None), wenn nichts gespeichert ist.
    """
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        df = pd.read_sql_query(  # SQL-Abfrage ausführen und Ergebnis direkt als Tabelle bekommen
            """
            SELECT * FROM market_snapshots
            WHERE currency = ?
              AND fetched_at = (SELECT MAX(fetched_at) FROM market_snapshots WHERE currency = ?)
            ORDER BY rank
            """,
            conn,
            params=(currency, currency),  # Die ? werden sicher durch diese Werte ersetzt
        )
    finally:
        conn.close()  # Verbindung schließen
    if df.empty:  # Noch nie etwas gespeichert?
        return None, None  # Dann gibt es nichts zurückzugeben
    fetched_at = df["fetched_at"].iloc[0]  # Abrufzeitpunkt aus der ersten Zeile lesen
    return df.drop(columns=["fetched_at", "currency"]), fetched_at  # Hilfsspalten entfernen und zurückgeben


def save_global_snapshot(data: dict, currency: str, fetched_at: str, db_path: str = DB_PATH) -> None:
    """Speichert die Gesamtmarkt-Kennzahlen als neue Momentaufnahme.

    Args:
        data: Dictionary aus api_client.fetch_global_data().
        currency: "eur" oder "usd".
        fetched_at: Zeitpunkt des Abrufs.
        db_path: Pfad zur Datenbankdatei.
    """
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        conn.execute(  # Eine neue Zeile einfügen
            "INSERT INTO global_snapshots VALUES (?, ?, ?, ?, ?)",  # Fünf Platzhalter für fünf Spalten
            (
                fetched_at,  # Zeitpunkt
                currency,  # Währung
                data["total_market_cap"],  # Gesamt-Marktkapitalisierung
                data["market_cap_change_24h"],  # Veränderung 24 h
                data["btc_dominance"],  # BTC-Dominanz
            ),
        )
        conn.commit()  # Änderung speichern
    finally:
        conn.close()  # Verbindung schließen


def load_latest_global_snapshot(currency: str, db_path: str = DB_PATH):
    """Lädt die neuesten Gesamtmarkt-Kennzahlen für eine Währung.

    Args:
        currency: "eur" oder "usd".
        db_path: Pfad zur Datenbankdatei.

    Returns:
        Tupel (Dictionary, fetched_at) – oder (None, None), wenn nichts gespeichert ist.
    """
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        row = conn.execute(  # Neueste Zeile für diese Währung suchen
            """
            SELECT fetched_at, total_market_cap, market_cap_change_24h, btc_dominance
            FROM global_snapshots
            WHERE currency = ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (currency,),  # Platzhalter-Wert (Komma nötig, damit es ein Tupel ist)
        ).fetchone()  # Nur die erste Ergebniszeile holen (oder None)
    finally:
        conn.close()  # Verbindung schließen
    if row is None:  # Nichts gefunden?
        return None, None  # Leeres Ergebnis zurückgeben
    data = {  # Zeile wieder in dasselbe Format wie aus der API bringen
        "total_market_cap": row[1],
        "market_cap_change_24h": row[2],
        "btc_dominance": row[3],
    }
    return data, row[0]  # Daten und Abrufzeitpunkt zurückgeben


def save_price_history(series: pd.Series, coin_id: str, currency: str, fetched_at: str,
                       db_path: str = DB_PATH) -> None:
    """Speichert eine Kurshistorie. Bereits vorhandene Tage werden überschrieben.

    Args:
        series: Zeitreihe aus api_client.fetch_price_history().
        coin_id: z. B. "bitcoin".
        currency: "eur" oder "usd".
        fetched_at: Zeitpunkt des Abrufs.
        db_path: Pfad zur Datenbankdatei.
    """
    rows = [  # Für jeden Tag ein Tupel bauen, das in die Tabelle passt
        (coin_id, currency, date.strftime("%Y-%m-%d"), float(price), fetched_at)  # Datum als Text speichern
        for date, price in series.items()  # series.items() liefert Paare (Datum, Preis)
    ]
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        conn.executemany(  # Viele Zeilen auf einmal einfügen
            "INSERT OR REPLACE INTO price_history VALUES (?, ?, ?, ?, ?)",  # Gibt es den Tag schon → ersetzen
            rows,
        )
        conn.commit()  # Änderungen speichern
    finally:
        conn.close()  # Verbindung schließen


def load_price_history(coin_id: str, currency: str, db_path: str = DB_PATH):
    """Lädt die gespeicherte Kurshistorie eines Coins.

    Args:
        coin_id: z. B. "bitcoin".
        currency: "eur" oder "usd".
        db_path: Pfad zur Datenbankdatei.

    Returns:
        Tupel (Series, fetched_at) – oder (None, None), wenn nichts gespeichert ist.
        fetched_at ist der jüngste Abrufzeitpunkt dieser Historie.
    """
    conn = _connect(db_path)  # Verbindung öffnen
    try:
        df = pd.read_sql_query(  # Alle Tage für diesen Coin und diese Währung laden
            "SELECT date, price, fetched_at FROM price_history WHERE coin_id = ? AND currency = ? ORDER BY date",
            conn,
            params=(coin_id, currency),
        )
    finally:
        conn.close()  # Verbindung schließen
    if df.empty:  # Nichts gespeichert?
        return None, None  # Leeres Ergebnis
    df["date"] = pd.to_datetime(df["date"])  # Text-Datum wieder in echtes Datum umwandeln
    series = df.set_index("date")["price"]  # Datum als Index, Preis als Werte
    series.name = coin_id  # Zeitreihe benennen
    return series, df["fetched_at"].max()  # Zeitreihe und neuesten Abrufzeitpunkt zurückgeben
