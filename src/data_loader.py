"""
Was macht diese Datei?
----------------------
Sie ist die "Schaltzentrale" für Daten in der App und verbindet api_client.py mit database.py.

Ablauf bei jeder Lade-Funktion:
  1. Versuche, frische Daten von CoinGecko zu holen.
  2. Hat das geklappt → in der Datenbank speichern und zurückgeben.
  3. Hat es NICHT geklappt → die zuletzt gespeicherten Daten aus der Datenbank nehmen
     und eine freundliche Warnung mitgeben.

Zusätzlich merkt sich Streamlit die Ergebnisse eine Weile im Arbeitsspeicher
(@st.cache_data). Solange dieser Zwischenspeicher gültig ist, wird CoinGecko gar
nicht erst gefragt – das schont unser Monatslimit von ca. 10.000 Aufrufen.
"""

import os  # os: Umgebungsvariablen lesen
from dataclasses import dataclass  # dataclass: einfache Klasse, die nur Werte bündelt
from datetime import datetime, timezone  # Für den aktuellen Zeitpunkt in UTC

import pandas as pd  # pandas: für die Umrechnung von Zeitzonen
import streamlit as st  # streamlit: Web-Oberfläche und Zwischenspeicher

from src import api_client, database  # Unsere eigenen Module

MARKET_CACHE_SECONDS = 10 * 60  # Marktdaten 10 Minuten im Zwischenspeicher halten
HISTORY_CACHE_SECONDS = 60 * 60  # Kurshistorie 60 Minuten im Zwischenspeicher halten


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
    """Liest den CoinGecko-API-Key aus den Streamlit-Secrets (oder einer Umgebungsvariable).

    Returns:
        Den Key als Text oder einen leeren Text, falls keiner hinterlegt ist.
        Ohne Key funktioniert CoinGecko meist trotzdem, aber mit strengerem Limit.
    """
    try:  # st.secrets wirft einen Fehler, wenn es gar keine secrets.toml gibt
        return st.secrets["COINGECKO_API_KEY"]  # Key aus .streamlit/secrets.toml bzw. Cloud-Secrets
    except Exception:  # Keine Datei oder kein Eintrag vorhanden
        return os.environ.get("COINGECKO_API_KEY", "")  # Ersatzweise Umgebungsvariable, sonst leer


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


@st.cache_data(ttl=MARKET_CACHE_SECONDS, show_spinner="Lade Marktdaten …")
def load_top_coins(currency: str) -> LoadResult:
    """Lädt die Top-20-Coins (live oder aus der Datenbank).

    Args:
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einem DataFrame als data.
    """
    try:  # Zuerst live bei CoinGecko versuchen
        df = api_client.fetch_top_coins(currency, get_api_key())  # Daten abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_market_snapshot(df, currency, fetched_at)  # In der Datenbank sichern
        return LoadResult(df, fetched_at, False, None)  # Erfolg: frische Daten zurückgeben
    except api_client.CoinGeckoError as error:  # Live-Abruf hat nicht geklappt
        df, fetched_at = database.load_latest_market_snapshot(currency)  # Letzten Stand aus der DB holen
        return LoadResult(df, fetched_at, True, str(error))  # Mit Fehlermeldung zurückgeben


@st.cache_data(ttl=MARKET_CACHE_SECONDS, show_spinner="Lade Gesamtmarkt-Daten …")
def load_global_data(currency: str) -> LoadResult:
    """Lädt die Gesamtmarkt-Kennzahlen (live oder aus der Datenbank).

    Args:
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einem Dictionary als data.
    """
    try:  # Zuerst live versuchen
        data = api_client.fetch_global_data(currency, get_api_key())  # Daten abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_global_snapshot(data, currency, fetched_at)  # In der Datenbank sichern
        return LoadResult(data, fetched_at, False, None)  # Erfolg
    except api_client.CoinGeckoError as error:  # Live-Abruf gescheitert
        data, fetched_at = database.load_latest_global_snapshot(currency)  # Letzten Stand aus der DB holen
        return LoadResult(data, fetched_at, True, str(error))  # Mit Fehlermeldung zurückgeben


@st.cache_data(ttl=HISTORY_CACHE_SECONDS, show_spinner="Lade Kurshistorie …")
def load_price_history(coin_id: str, currency: str) -> LoadResult:
    """Lädt die Kurshistorie der letzten 365 Tage (live oder aus der Datenbank).

    Args:
        coin_id: CoinGecko-ID, z. B. "bitcoin".
        currency: "eur" oder "usd".

    Returns:
        LoadResult mit einer Series (Index = Datum) als data.
    """
    try:  # Zuerst live versuchen
        series = api_client.fetch_price_history(coin_id, currency, get_api_key())  # Historie abrufen
        fetched_at = _now_utc()  # Abrufzeitpunkt merken
        database.save_price_history(series, coin_id, currency, fetched_at)  # In der Datenbank sichern
        return LoadResult(series, fetched_at, False, None)  # Erfolg
    except api_client.CoinGeckoError as error:  # Live-Abruf gescheitert
        series, fetched_at = database.load_price_history(coin_id, currency)  # Gespeicherte Historie holen
        return LoadResult(series, fetched_at, True, str(error))  # Mit Fehlermeldung zurückgeben


def show_load_status(result: LoadResult, label: str) -> None:
    """Zeigt unter einer Überschrift an, wie aktuell die Daten sind – und warnt bei Problemen.

    Args:
        result: Das Ergebnis einer Lade-Funktion.
        label: Kurzer Name der Daten für die Anzeige, z. B. "Marktdaten".
    """
    if result.data is None:  # Weder live noch aus der Datenbank etwas bekommen
        st.error(  # Rote Fehlermeldung anzeigen
            f"{label} konnten nicht geladen werden: {result.error_message} "
            "Leider sind auch noch keine gespeicherten Daten vorhanden."
        )
        st.stop()  # Rest der Seite nicht ausführen – ohne Daten gibt es nichts anzuzeigen
    if result.from_database:  # Live-Abruf gescheitert, aber Reserve aus der DB vorhanden
        st.warning(  # Gelbe Warnung anzeigen
            f"{result.error_message} Angezeigt werden gespeicherte {label} "
            f"vom {format_timestamp(result.fetched_at)}."
        )
    else:  # Alles live geklappt
        st.caption(f"{label}: Stand {format_timestamp(result.fetched_at)}")  # Dezenter Hinweis zum Abrufzeitpunkt
