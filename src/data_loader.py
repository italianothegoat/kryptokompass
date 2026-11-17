"""
Was macht diese Datei?
----------------------
Sie ist die "Schaltzentrale" für Daten in der App und verbindet api_client.py mit database.py.

Ablauf bei jeder Lade-Funktion:
  1. Liegt ein frisches Ergebnis im Zwischenspeicher (Cache)? → sofort zurückgeben.
  2. Sonst: frische Daten von CoinGecko holen, in der Datenbank speichern, zurückgeben.
  3. Klappt der Abruf nicht → die zuletzt gespeicherten Daten aus der Datenbank nehmen
     und eine freundliche Warnung mitgeben.

Der Zwischenspeicher ist ein einfaches Python-Dictionary im Arbeitsspeicher.
Er schont unser CoinGecko-Monatslimit (ca. 10.000 Aufrufe): Solange ein Ergebnis
"frisch" ist, wird CoinGecko gar nicht erst gefragt.
"""

import os  # os: Umgebungsvariablen und Dateipfade
import time  # time: aktuelle Uhrzeit in Sekunden (für das Alter der Cache-Einträge)
import tomllib  # tomllib: liest .toml-Dateien (seit Python 3.11 eingebaut)
from dataclasses import dataclass  # dataclass: einfache Klasse, die nur Werte bündelt
from datetime import datetime, timezone  # Für den aktuellen Zeitpunkt in UTC

import pandas as pd  # pandas: für die Umrechnung von Zeitzonen

from src import api_client, database  # Unsere eigenen Module

MARKET_CACHE_SECONDS = 10 * 60  # Marktdaten 10 Minuten im Zwischenspeicher halten
HISTORY_CACHE_SECONDS = 60 * 60  # Kurshistorie 60 Minuten im Zwischenspeicher halten
SECRETS_PATH = "secrets.toml"  # Lokale Geheimnis-Datei (steht in .gitignore)

_cache = {}  # Zwischenspeicher: Schlüssel → (Zeitpunkt in Sekunden, LoadResult)


@dataclass
class LoadResult:
    """Ergebnis eines Ladevorgangs – die Daten plus Infos, woher sie kommen.

    Attributes:
        data: Die eigentlichen Daten (DataFrame, Series oder Dictionary) oder None.
        fetched_at: Zeitpunkt, zu dem die Daten bei CoinGecko abgerufen wurden (Text, UTC).
        from_database: True, wenn die Daten aus der Datenbank stammen (Notfall-Reserve).
        error_message: Fehlermeldung, falls der Live-Abruf gescheitert ist, sonst None.
    """

    data: object
    fetched_at: str | None
    from_database: bool
    error_message: str | None


def get_api_key() -> str:
    """Liest den CoinGecko-API-Key.

    Reihenfolge:
    1. Umgebungsvariable COINGECKO_API_KEY (so machen es Render und Codespaces)
    2. Datei secrets.toml im Projektordner (so macht ihr es lokal in PyCharm)

    Returns:
        Den Key als Text oder einen leeren Text, falls keiner hinterlegt ist.
        Ohne Key funktioniert CoinGecko meist trotzdem, aber mit strengerem Limit.
    """
    key = os.environ.get("COINGECKO_API_KEY", "")  # Zuerst in den Umgebungsvariablen nachsehen
    if key:  # Gefunden?
        return key  # Dann direkt verwenden
    if os.path.exists(SECRETS_PATH):  # Sonst: Gibt es eine lokale secrets.toml?
        with open(SECRETS_PATH, "rb") as file:  # Datei öffnen (tomllib verlangt Binärmodus)
            return tomllib.load(file).get("COINGECKO_API_KEY", "")  # Key auslesen (oder leer)
    return ""  # Nirgends ein Key → ohne Key weitermachen


def clear_cache() -> None:
    """Leert den Zwischenspeicher – beim nächsten Laden wird CoinGecko frisch gefragt."""
    _cache.clear()  # Alle Einträge löschen


def _get_cached(key: str, max_age_seconds: int):
    """Gibt einen Cache-Eintrag zurück, wenn er jünger als `max_age_seconds` ist.

    Args:
        key: Name des Eintrags, z. B. "top_coins_eur".
        max_age_seconds: Wie alt der Eintrag höchstens sein darf.

    Returns:
        Das gespeicherte LoadResult oder None, wenn nichts (Frisches) da ist.
    """
    entry = _cache.get(key)  # Eintrag suchen (None, falls nicht vorhanden)
    if entry is None:  # Nichts gespeichert?
        return None  # Dann gibt es nichts zurückzugeben
    saved_at, result = entry  # Eintrag in Zeitpunkt und Ergebnis aufteilen
    if time.time() - saved_at > max_age_seconds:  # Zu alt?
        return None  # Dann behandeln wir ihn wie nicht vorhanden
    return result  # Frischer Eintrag → zurückgeben


def _now_utc() -> str:
    """Gibt den aktuellen Zeitpunkt in UTC als Text zurück, z. B. '2026-11-16T09:30:00+00:00'."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")  # Jetzt, sekundengenau, als ISO-Text


def format_timestamp(fetched_at: str | None) -> str:
    """Wandelt einen UTC-Zeitpunkt in deutsche Ortszeit für die Anzeige um.

    Args:
        fetched_at: Zeitpunkt als ISO-Text in UTC (oder None).

    Returns:
        Z. B. "16.11.2026, 10:30 Uhr" – oder "unbekannt".
    """
    if not fetched_at:  # Kein Zeitpunkt vorhanden?
        return "unbekannt"  # Dann ehrlich "unbekannt" anzeigen
    local_time = pd.Timestamp(fetched_at).tz_convert("Europe/Berlin")  # UTC → deutsche Zeit (inkl. Sommerzeit)
    return local_time.strftime("%d.%m.%Y, %H:%M Uhr")  # In deutsches Datumsformat bringen


def load_top_coins(currency: str) -> LoadResult:
    """Lädt die Top-20-Coins (Cache → live → Datenbank).

    Args:
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einem DataFrame als data.
    """
    cache_key = f"top_coins_{currency}"  # Eindeutiger Name für den Cache
    cached = _get_cached(cache_key, MARKET_CACHE_SECONDS)  # Frisches Ergebnis vorhanden?
    if cached is not None:  # Ja →
        return cached  # sofort zurückgeben, kein API-Aufruf nötig
    try:  # Live bei CoinGecko versuchen
        df = api_client.fetch_top_coins(currency, get_api_key())  # Daten abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_market_snapshot(df, currency, fetched_at)  # In der Datenbank sichern
        result = LoadResult(df, fetched_at, False, None)  # Erfolg
    except api_client.CoinGeckoError as error:  # Live-Abruf hat nicht geklappt
        df, fetched_at = database.load_latest_market_snapshot(currency)  # Letzten Stand aus der DB holen
        result = LoadResult(df, fetched_at, True, str(error))  # Mit Fehlermeldung
    _cache[cache_key] = (time.time(), result)  # Ergebnis im Zwischenspeicher ablegen
    return result  # Ergebnis zurückgeben


def load_global_data(currency: str) -> LoadResult:
    """Lädt die Gesamtmarkt-Kennzahlen (Cache → live → Datenbank).

    Args:
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einem Dictionary als data.
    """
    cache_key = f"global_{currency}"  # Eindeutiger Name für den Cache
    cached = _get_cached(cache_key, MARKET_CACHE_SECONDS)  # Frisches Ergebnis vorhanden?
    if cached is not None:  # Ja →
        return cached  # sofort zurückgeben
    try:  # Live versuchen
        data = api_client.fetch_global_data(currency, get_api_key())  # Daten abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_global_snapshot(data, currency, fetched_at)  # In der Datenbank sichern
        result = LoadResult(data, fetched_at, False, None)  # Erfolg
    except api_client.CoinGeckoError as error:  # Live-Abruf gescheitert
        data, fetched_at = database.load_latest_global_snapshot(currency)  # Letzten Stand aus der DB holen
        result = LoadResult(data, fetched_at, True, str(error))  # Mit Fehlermeldung
    _cache[cache_key] = (time.time(), result)  # Im Zwischenspeicher ablegen
    return result  # Ergebnis zurückgeben


def load_price_history(coin_id: str, currency: str) -> LoadResult:
    """Lädt die Kurshistorie der letzten 365 Tage (Cache → live → Datenbank).

    Args:
        coin_id: CoinGecko-ID, z. B. "bitcoin".
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einer Series (Index = Datum) als data.
    """
    cache_key = f"history_{coin_id}_{currency}"  # Eindeutiger Name für den Cache
    cached = _get_cached(cache_key, HISTORY_CACHE_SECONDS)  # Frisches Ergebnis vorhanden?
    if cached is not None:  # Ja →
        return cached  # sofort zurückgeben
    try:  # Live versuchen
        series = api_client.fetch_price_history(coin_id, currency, get_api_key())  # Historie abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_price_history(series, coin_id, currency, fetched_at)  # In der Datenbank sichern
        result = LoadResult(series, fetched_at, False, None)  # Erfolg
    except api_client.CoinGeckoError as error:  # Live-Abruf gescheitert
        series, fetched_at = database.load_price_history(coin_id, currency)  # Gespeicherte Historie holen
        result = LoadResult(series, fetched_at, True, str(error))  # Mit Fehlermeldung
    _cache[cache_key] = (time.time(), result)  # Im Zwischenspeicher ablegen
    return result  # Ergebnis zurückgeben
