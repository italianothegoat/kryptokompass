"""
Was macht diese Datei?
----------------------
Sie spricht mit der CoinGecko-API (einem Web-Dienst, der Kryptodaten liefert).
Jede Funktion hier ruft genau EINE Adresse bei CoinGecko auf und gibt die Antwort
als gut nutzbare Python-/pandas-Daten zurück.

Wichtig: Diese Datei weiß nichts von der Website oder der Datenbank. Sie holt nur Daten.
Dadurch können wir sie auch ohne App testen (siehe check_api.py).
"""

import pandas as pd  # pandas: Tabellen (DataFrames) und Zeitreihen (Series)
import requests  # requests: schickt Anfragen ins Internet und empfängt Antworten

BASE_URL = "https://api.coingecko.com/api/v3"  # Grundadresse der CoinGecko-API
TIMEOUT_SECONDS = 15  # Nach so vielen Sekunden ohne Antwort brechen wir ab


class CoinGeckoError(Exception):
    """Eigener Fehlertyp: wird geworfen, wenn bei CoinGecko etwas schiefgeht.

    Die Nachricht ist bereits auf Deutsch und freundlich formuliert,
    damit wir sie direkt in der App anzeigen können.
    """


def _get(endpoint: str, params: dict, api_key: str):
    """Schickt eine GET-Anfrage an CoinGecko und gibt die Antwort als Python-Daten zurück.

    Der Unterstrich am Anfang des Namens bedeutet: "nur für den Gebrauch in dieser Datei".

    Args:
        endpoint: Teil der Adresse nach BASE_URL, z. B. "/global".
        params: Zusätzliche Angaben für die Anfrage, z. B. {"vs_currency": "eur"}.
        api_key: Euer Demo-API-Key. Leerer Text = ohne Key (stärker begrenzt).

    Returns:
        Die JSON-Antwort, umgewandelt in Python-Listen/-Dictionaries.

    Raises:
        CoinGeckoError: Bei Netzwerkproblemen, Limit-Überschreitung oder anderen Fehlern.
    """
    headers = {"accept": "application/json"}  # Wir wollen die Antwort im JSON-Format
    if api_key:  # Nur wenn ein Key vorhanden ist …
        headers["x-cg-demo-api-key"] = api_key  # … schicken wir ihn im passenden Header mit

    try:  # Versuchen, die Anfrage zu senden
        response = requests.get(  # GET-Anfrage = "Daten abholen"
            BASE_URL + endpoint,  # Vollständige Adresse zusammensetzen
            params=params,  # Parameter werden automatisch an die Adresse angehängt
            headers=headers,  # Header (inkl. API-Key) mitschicken
            timeout=TIMEOUT_SECONDS,  # Nicht ewig warten
        )
    except requests.RequestException as error:  # Kein Internet, Server nicht erreichbar, Timeout …
        raise CoinGeckoError(  # … wir übersetzen das in eine verständliche Meldung
            "CoinGecko ist gerade nicht erreichbar (Netzwerkproblem)."
        ) from error

    if response.status_code == 429:  # 429 = "Too Many Requests": Abruf-Limit erreicht
        raise CoinGeckoError("Das Abruf-Limit von CoinGecko ist erreicht. Bitte später erneut versuchen.")
    if response.status_code in (401, 403):  # 401/403 = Zugriff verweigert, meist falscher API-Key
        raise CoinGeckoError("CoinGecko hat den API-Key abgelehnt (Fehler 401). Bitte den Wert von "
                             "COINGECKO_API_KEY prüfen: genau der Demo-Key, ohne Anführungszeichen und Leerzeichen.")
    if response.status_code == 400 and api_key:  # 400 mit Key: oft ein Pro-Key statt eines Demo-Keys
        raise CoinGeckoError("CoinGecko meldet Fehler 400 – ist der Key ein Demo-Key? (Pro-Keys brauchen "
                             "eine andere Adresse.)")
    if response.status_code != 200:  # 200 = alles ok; alles andere ist ein Fehler
        raise CoinGeckoError(f"CoinGecko meldet einen Fehler (Statuscode {response.status_code}).")

    return response.json()  # Antworttext (JSON) in Python-Daten umwandeln und zurückgeben


def fetch_global_data(currency: str, api_key: str) -> dict:
    """Holt Kennzahlen für den gesamten Kryptomarkt.

    Args:
        currency: "eur" oder "usd" (klein geschrieben).
        api_key: Euer Demo-API-Key.

    Returns:
        Dictionary mit:
        - total_market_cap: gesamte Marktkapitalisierung in der Währung
        - market_cap_change_24h: Veränderung der Marktkapitalisierung in den letzten 24 h in %
        - btc_dominance: Anteil von Bitcoin an der gesamten Marktkapitalisierung in %
    """
    raw = _get("/global", params={}, api_key=api_key)  # Anfrage an /global senden
    data = raw["data"]  # Die eigentlichen Werte stecken im Feld "data"
    return {  # Nur die Werte zurückgeben, die wir wirklich brauchen
        "total_market_cap": data["total_market_cap"][currency],  # Gesamt-Marktkap. in gewählter Währung
        "market_cap_change_24h": data["market_cap_change_percentage_24h_usd"],  # 24-h-Veränderung in %
        "btc_dominance": data["market_cap_percentage"]["btc"],  # BTC-Anteil in %
    }


def fetch_top_coins(currency: str, api_key: str, limit: int = 20) -> pd.DataFrame:
    """Holt die größten Coins nach Marktkapitalisierung inklusive Kursveränderungen.

    Args:
        currency: "eur" oder "usd".
        api_key: Euer Demo-API-Key.
        limit: Wie viele Coins (Standard: 20).

    Returns:
        DataFrame mit einer Zeile pro Coin und englischen Spaltennamen
        (coin_id, name, symbol, rank, price, change_24h, change_7d, change_30d,
        market_cap, volume_24h, ath_change).
    """
    params = {  # Angaben für die Anfrage
        "vs_currency": currency,  # In welcher Währung die Preise kommen sollen
        "order": "market_cap_desc",  # Sortiert nach Marktkapitalisierung, größte zuerst
        "per_page": limit,  # Wie viele Coins pro Seite
        "page": 1,  # Erste Seite (= die größten Coins)
        "price_change_percentage": "24h,7d,30d",  # Zusätzlich diese Veränderungen mitliefern
    }
    raw = _get("/coins/markets", params=params, api_key=api_key)  # Anfrage senden, Liste von Coins kommt zurück

    df = pd.DataFrame(raw)  # Liste von Dictionaries in eine Tabelle umwandeln
    df = df.rename(  # CoinGecko-Spaltennamen in unsere kürzeren Namen umbenennen
        columns={
            "id": "coin_id",  # Interne CoinGecko-ID, z. B. "bitcoin"
            "market_cap_rank": "rank",  # Rang nach Marktkapitalisierung
            "current_price": "price",  # Aktueller Preis
            "price_change_percentage_24h_in_currency": "change_24h",  # Veränderung 24 h in %
            "price_change_percentage_7d_in_currency": "change_7d",  # Veränderung 7 Tage in %
            "price_change_percentage_30d_in_currency": "change_30d",  # Veränderung 30 Tage in %
            "total_volume": "volume_24h",  # Handelsvolumen der letzten 24 h
            "ath_change_percentage": "ath_change",  # Abstand zum Allzeithoch in %
        }
    )
    df["symbol"] = df["symbol"].str.upper()  # Symbole groß schreiben: "btc" → "BTC"
    columns = [  # Nur diese Spalten behalten, in dieser Reihenfolge
        "coin_id", "name", "symbol", "rank", "price", "change_24h", "change_7d",
        "change_30d", "market_cap", "volume_24h", "ath_change",
    ]
    return df[columns]  # Gekürzte Tabelle zurückgeben


def fetch_price_history(coin_id: str, currency: str, api_key: str, days: int = 365) -> pd.Series:
    """Holt die tägliche Kurshistorie eines Coins.

    Wir holen immer 365 Tage auf einmal und schneiden später in der App den
    gewünschten Zeitraum heraus. Das spart API-Aufrufe (ein Abruf statt drei)
    und gibt den Indikatoren genug Vorlauf (z. B. braucht SMA 50 schon 50 Tage).

    Args:
        coin_id: CoinGecko-ID, z. B. "bitcoin".
        currency: "eur" oder "usd".
        api_key: Euer Demo-API-Key.
        days: Anzahl Tage (Demo-Plan erlaubt max. 365).

    Returns:
        Series mit Schlusskursen; Index = Datum (ein Wert pro Tag).
    """
    params = {"vs_currency": currency, "days": days, "interval": "daily"}  # Tageswerte für X Tage
    raw = _get(f"/coins/{coin_id}/market_chart", params=params, api_key=api_key)  # Anfrage senden

    prices = pd.DataFrame(raw["prices"], columns=["timestamp", "price"])  # Liste [[Zeit, Preis], …] → Tabelle
    prices["date"] = pd.to_datetime(prices["timestamp"], unit="ms").dt.normalize()  # Millisekunden → Datum (ohne Uhrzeit)
    prices = prices.drop_duplicates(subset="date", keep="last")  # Pro Tag nur einen Wert behalten (den neuesten)
    series = prices.set_index("date")["price"]  # Datum als Index, Preis als Werte
    series.name = coin_id  # Der Zeitreihe den Coin-Namen geben (hilfreich beim Zusammenfügen)
    return series  # Fertige Zeitreihe zurückgeben
