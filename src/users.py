"""
Was macht diese Datei?
----------------------
Sie verwaltet die Benutzerkonten und die persönlichen Einstellungen ("Mein Bereich").

Gespeichert werden:
- users:     Benutzername, verschlüsseltes Passwort, Lieblingswährung, Anlegedatum
- watchlist: welche Coins jede Person beobachten möchte

WO wird gespeichert? Das entscheidet die Einstellung DATABASE_URL:
- Ist sie gesetzt (auf Render): in einer Postgres-Datenbank bei Neon.
  Die bleibt dauerhaft erhalten – auch wenn Render neu startet.
- Ist sie leer (lokal in PyCharm): in der Datei data/users.db (SQLite).

Passwörter werden NIE im Klartext gespeichert, sondern nur als "Hash":
eine Einbahn-Verschlüsselung. Beim Login wird das eingegebene Passwort genauso
verschlüsselt und mit dem gespeicherten Hash verglichen.
"""

import os  # os: Ordner anlegen, Umgebungsvariablen lesen
import re  # re: Muster prüfen (erlaubte Zeichen im Benutzernamen)
import sqlite3  # sqlite3: lokale Datenbank (in Python eingebaut)
from datetime import datetime, timezone  # Für das Anlegedatum

from werkzeug.security import check_password_hash, generate_password_hash  # Passwort-Hashing (kommt mit Dash/Flask)

from src import config  # Geheime Einstellungen lesen (DATABASE_URL)

USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,30}$")  # 3–30 Zeichen: Kleinbuchstaben, Ziffern, _ und -
MIN_PASSWORD_LENGTH = 8  # Passwörter müssen mindestens 8 Zeichen lang sein
MAX_WATCHLIST = 10  # Höchstens so viele Coins pro Watchlist
CURRENCIES = ("EUR", "USD")  # Erlaubte Währungen


def _sqlite_path() -> str:
    """Pfad der lokalen Benutzer-Datenbank (für Tests per Umgebungsvariable änderbar).

    Returns:
        Dateipfad, standardmäßig data/users.db.
    """
    return os.environ.get("USERS_SQLITE_PATH", os.path.join("data", "users.db"))  # Standard: data/users.db


def _connect():
    """Öffnet eine Verbindung zur richtigen Datenbank.

    Returns:
        Tupel (Verbindung, Platzhalter-Zeichen). SQLite schreibt Platzhalter als "?",
        Postgres als "%s" – wir merken uns, welches gilt.
    """
    url = config.get_secret("DATABASE_URL")  # Adresse der Online-Datenbank (leer = lokal arbeiten)
    if url:  # Online-Datenbank konfiguriert?
        import psycopg  # psycopg: Verbindung zu Postgres (erst hier laden, lokal wird es nicht gebraucht)
        return psycopg.connect(url), "%s"  # Postgres-Verbindung
    path = _sqlite_path()  # Pfad zur lokalen Datei
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)  # Ordner anlegen, falls er fehlt
    return sqlite3.connect(path), "?"  # SQLite-Verbindung


def _run(query: str, params: tuple = (), fetch: bool = False):
    """Führt einen SQL-Befehl aus – egal ob SQLite oder Postgres.

    Wir schreiben alle Befehle mit "?" als Platzhalter und tauschen ihn
    bei Postgres gegen "%s" aus.

    Args:
        query: SQL-Befehl mit "?" als Platzhalter für Werte.
        params: Die Werte für die Platzhalter (werden sicher eingesetzt, kein SQL-Einschleusen möglich).
        fetch: True = Ergebniszeilen zurückgeben (für SELECT).

    Returns:
        Liste der Ergebniszeilen (bei fetch=True), sonst None.
    """
    conn, placeholder = _connect()  # Verbindung öffnen
    try:  # try/finally: Verbindung wird garantiert geschlossen
        cursor = conn.execute(query.replace("?", placeholder), params)  # Befehl ausführen
        rows = cursor.fetchall() if fetch else None  # Ergebnis abholen, falls gewünscht
        conn.commit()  # Änderungen dauerhaft speichern
        return rows  # Ergebnis zurückgeben
    finally:
        conn.close()  # Verbindung schließen


def init_db() -> None:
    """Legt die Tabellen an, falls es sie noch nicht gibt (kann bei jedem Start laufen)."""
    _run(  # Tabelle der Benutzer
        """
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,          -- eindeutiger Name (klein geschrieben)
            password_hash TEXT NOT NULL,             -- verschlüsseltes Passwort
            currency      TEXT NOT NULL DEFAULT 'EUR', -- Lieblingswährung
            created_at    TEXT NOT NULL              -- Anlegedatum (UTC, ISO-Format)
        )
        """
    )
    _run(  # Tabelle der Watchlists
        """
        CREATE TABLE IF NOT EXISTS watchlist (
            username TEXT NOT NULL,   -- wem der Eintrag gehört
            coin_id  TEXT NOT NULL,   -- z. B. "bitcoin"
            sort_order INTEGER NOT NULL, -- Reihenfolge in der Liste
            PRIMARY KEY (username, coin_id) -- jeder Coin nur einmal pro Person
        )
        """
    )


def normalize_username(username: str) -> str:
    """Vereinheitlicht einen Benutzernamen: Leerzeichen weg, alles klein.

    Args:
        username: Eingabe aus dem Formular.

    Returns:
        Bereinigter Name, z. B. " Marc " → "marc".
    """
    return (username or "").strip().lower()  # None abfangen, Leerzeichen entfernen, klein schreiben


def user_exists(username: str) -> bool:
    """Prüft, ob es ein Konto mit diesem Namen gibt.

    Args:
        username: Benutzername.

    Returns:
        True, wenn vorhanden.
    """
    rows = _run("SELECT 1 FROM users WHERE username = ?", (normalize_username(username),), fetch=True)  # Suchen
    return bool(rows)  # Mindestens eine Zeile gefunden → existiert


def register_user(username: str, password: str, password_repeat: str) -> str | None:
    """Legt ein neues Konto an.

    Args:
        username: Gewünschter Benutzername.
        password: Gewünschtes Passwort.
        password_repeat: Passwort-Wiederholung (gegen Tippfehler).

    Returns:
        None bei Erfolg, sonst eine verständliche Fehlermeldung.
    """
    name = normalize_username(username)  # Namen vereinheitlichen
    if not USERNAME_PATTERN.match(name):  # Erlaubte Zeichen und Länge prüfen
        return "Der Benutzername muss 3–30 Zeichen lang sein (nur Buchstaben a–z, Ziffern, _ und -)."
    if len(password or "") < MIN_PASSWORD_LENGTH:  # Mindestlänge prüfen
        return f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen lang sein."
    if password != password_repeat:  # Beide Eingaben gleich?
        return "Die beiden Passwörter stimmen nicht überein."
    if user_exists(name):  # Name schon vergeben?
        return "Diesen Benutzernamen gibt es schon. Bitte einen anderen wählen."
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")  # Anlegezeitpunkt
    _run(  # Neues Konto speichern – nur der Hash, nie das Passwort selbst
        "INSERT INTO users (username, password_hash, currency, created_at) VALUES (?, ?, ?, ?)",
        (name, generate_password_hash(password), "EUR", created_at),
    )
    return None  # Kein Fehler


def check_login(username: str, password: str) -> bool:
    """Prüft Benutzername und Passwort.

    Args:
        username: Eingegebener Benutzername.
        password: Eingegebenes Passwort.

    Returns:
        True, wenn das Konto existiert und das Passwort stimmt.
    """
    rows = _run("SELECT password_hash FROM users WHERE username = ?",  # Gespeicherten Hash holen
                (normalize_username(username),), fetch=True)
    if not rows:  # Kein Konto mit diesem Namen
        return False  # Login fehlgeschlagen
    return check_password_hash(rows[0][0], password or "")  # Eingabe verschlüsseln und mit Hash vergleichen


def get_currency(username: str) -> str:
    """Liest die Lieblingswährung einer Person.

    Args:
        username: Benutzername.

    Returns:
        "EUR" oder "USD" (Standard "EUR").
    """
    rows = _run("SELECT currency FROM users WHERE username = ?", (normalize_username(username),), fetch=True)
    return rows[0][0] if rows else "EUR"  # Gespeicherter Wert oder Euro


def set_currency(username: str, currency: str) -> None:
    """Speichert die Lieblingswährung einer Person.

    Args:
        username: Benutzername.
        currency: "EUR" oder "USD".
    """
    if currency not in CURRENCIES:  # Nur erlaubte Werte speichern
        return  # Ungültige Eingabe ignorieren
    _run("UPDATE users SET currency = ? WHERE username = ?", (currency, normalize_username(username)))  # Speichern


def get_watchlist(username: str) -> list[str]:
    """Liest die Watchlist einer Person in der gespeicherten Reihenfolge.

    Args:
        username: Benutzername.

    Returns:
        Liste von Coin-IDs, z. B. ["bitcoin", "solana"].
    """
    rows = _run("SELECT coin_id FROM watchlist WHERE username = ? ORDER BY sort_order",  # Alle Einträge holen
                (normalize_username(username),), fetch=True)
    return [row[0] for row in rows]  # Nur die Coin-IDs zurückgeben


def set_watchlist(username: str, coin_ids: list[str]) -> None:
    """Ersetzt die Watchlist einer Person durch eine neue Liste.

    Args:
        username: Benutzername.
        coin_ids: Neue Liste von Coin-IDs (Doppelte werden entfernt, max. 10).
    """
    name = normalize_username(username)  # Namen vereinheitlichen
    unique_ids = list(dict.fromkeys(coin_ids or []))[:MAX_WATCHLIST]  # Doppelte entfernen, Reihenfolge behalten, kürzen
    _run("DELETE FROM watchlist WHERE username = ?", (name,))  # Alte Liste löschen
    for position, coin_id in enumerate(unique_ids):  # Neue Liste Eintrag für Eintrag speichern
        _run("INSERT INTO watchlist (username, coin_id, sort_order) VALUES (?, ?, ?)", (name, coin_id, position))
