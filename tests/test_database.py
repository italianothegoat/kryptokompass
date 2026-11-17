"""
Was macht diese Datei?
----------------------
Automatische Tests für src/database.py.

Jeder Test bekommt von pytest einen eigenen, leeren Ordner (tmp_path).
Dort legen wir eine Test-Datenbank an – eure echte Datenbank bleibt unberührt.
"""

import pandas as pd  # pandas: Testdaten bauen

from src import database  # Das Modul, das wir testen


def test_price_history_roundtrip(tmp_path):
    """Was wir speichern, müssen wir genauso wieder laden können."""
    db_path = str(tmp_path / "test.db")  # Pfad zur Test-Datenbank im temporären Ordner
    database.init_db(db_path)  # Tabellen anlegen
    dates = pd.date_range("2026-01-01", periods=3, freq="D")  # Drei Tage
    series = pd.Series([100.0, 101.0, 102.0], index=dates)  # Drei Kurse
    database.save_price_history(series, "bitcoin", "eur", "2026-01-03T12:00:00+00:00", db_path)  # Speichern

    loaded, fetched_at = database.load_price_history("bitcoin", "eur", db_path)  # Wieder laden
    assert list(loaded) == [100.0, 101.0, 102.0]  # Gleiche Kurse
    assert fetched_at == "2026-01-03T12:00:00+00:00"  # Gleicher Abrufzeitpunkt


def test_price_history_overwrites_same_day(tmp_path):
    """Wird derselbe Tag erneut gespeichert, wird er ersetzt statt doppelt angelegt."""
    db_path = str(tmp_path / "test.db")  # Test-Datenbank
    database.init_db(db_path)  # Tabellen anlegen
    day = pd.date_range("2026-01-01", periods=1, freq="D")  # Ein einziger Tag
    database.save_price_history(pd.Series([100.0], index=day), "bitcoin", "eur", "t1", db_path)  # Erster Wert
    database.save_price_history(pd.Series([105.0], index=day), "bitcoin", "eur", "t2", db_path)  # Neuer Wert, gleicher Tag

    loaded, _ = database.load_price_history("bitcoin", "eur", db_path)  # Laden
    assert list(loaded) == [105.0]  # Nur der neue Wert ist übrig


def test_load_empty_database_returns_none(tmp_path):
    """Ist noch nichts gespeichert, kommt (None, None) zurück – kein Absturz."""
    db_path = str(tmp_path / "test.db")  # Test-Datenbank
    database.init_db(db_path)  # Leere Tabellen anlegen
    assert database.load_latest_market_snapshot("eur", db_path) == (None, None)  # Keine Marktdaten
    assert database.load_latest_global_snapshot("eur", db_path) == (None, None)  # Keine Gesamtmarktdaten
    assert database.load_price_history("bitcoin", "eur", db_path) == (None, None)  # Keine Historie


def test_market_snapshot_returns_latest(tmp_path):
    """Bei mehreren gespeicherten Abrufen wird immer der neueste geladen."""
    db_path = str(tmp_path / "test.db")  # Test-Datenbank
    database.init_db(db_path)  # Tabellen anlegen
    old = pd.DataFrame([{  # Alte Momentaufnahme mit Preis 1
        "coin_id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "rank": 1, "price": 1.0,
        "change_24h": 0.0, "change_7d": 0.0, "change_30d": 0.0, "market_cap": 1.0,
        "volume_24h": 1.0, "ath_change": 0.0,
    }])
    new = old.assign(price=2.0)  # Neue Momentaufnahme: gleiche Werte, aber Preis 2
    database.save_market_snapshot(old, "eur", "2026-01-01T00:00:00+00:00", db_path)  # Alt speichern
    database.save_market_snapshot(new, "eur", "2026-01-02T00:00:00+00:00", db_path)  # Neu speichern

    df, fetched_at = database.load_latest_market_snapshot("eur", db_path)  # Neueste laden
    assert df["price"].iloc[0] == 2.0  # Es ist die neue
    assert fetched_at == "2026-01-02T00:00:00+00:00"  # Mit dem neuen Zeitpunkt
