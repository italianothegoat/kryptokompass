"""
Was macht diese Datei?
----------------------
Automatische Tests für src/indicators.py.

Idee: Wir füttern jede Funktion mit kleinen, selbst ausgedachten Kursreihen,
bei denen wir das richtige Ergebnis im Kopf ausrechnen können – und prüfen,
ob die Funktion genau das liefert.

Starten mit:  pytest
pytest findet automatisch alle Funktionen, deren Name mit "test_" beginnt.
"""

import pandas as pd  # pandas: Kursreihen für die Tests bauen
import pytest  # pytest: Test-Werkzeug (hier für pytest.approx = "ungefähr gleich")

from src import indicators  # Das Modul, das wir testen


def make_prices(values: list[float]) -> pd.Series:
    """Hilfsfunktion: baut aus einer Zahlenliste eine Kursreihe mit Tagesdatum als Index.

    Args:
        values: Kurse, z. B. [100, 110, 120].

    Returns:
        Series mit einem Wert pro Tag, beginnend am 01.01.2026.
    """
    dates = pd.date_range("2026-01-01", periods=len(values), freq="D")  # Fortlaufende Tage erzeugen
    return pd.Series(values, index=dates, dtype=float)  # Zahlen + Datum zu einer Zeitreihe verbinden


def test_sma_simple_average():
    """SMA über 3 Tage von 1, 2, 3, 4, 5 muss 2, 3, 4 ergeben (erste zwei Tage leer)."""
    result = indicators.sma(make_prices([1, 2, 3, 4, 5]), window=3)  # SMA berechnen
    assert result.isna().sum() == 2  # Die ersten 2 Werte sind leer (zu wenig Daten)
    assert list(result.dropna()) == [2.0, 3.0, 4.0]  # Die restlichen Werte stimmen


def test_bollinger_bands_constant_price():
    """Bei konstantem Kurs gibt es keine Schwankung → alle drei Bänder liegen aufeinander."""
    bands = indicators.bollinger_bands(make_prices([50] * 30), window=20)  # 30 Tage immer 50
    last = bands.iloc[-1]  # Letzte Zeile ansehen
    assert last["upper"] == last["middle"] == last["lower"] == 50  # Alle drei sind genau 50


def test_bollinger_upper_above_lower():
    """Bei schwankendem Kurs muss das obere Band über dem unteren liegen."""
    bands = indicators.bollinger_bands(make_prices([10, 12, 9, 13, 8] * 5), window=20)  # Zickzack-Kurs
    last = bands.iloc[-1]  # Letzte Zeile
    assert last["upper"] > last["middle"] > last["lower"]  # Reihenfolge stimmt


def test_rsi_only_rising_is_100():
    """Steigt der Kurs jeden Tag, gibt es keine Verluste → RSI = 100."""
    result = indicators.rsi(make_prices(list(range(1, 31))), period=14)  # 1, 2, 3, … 30
    assert result.iloc[-1] == pytest.approx(100)  # Letzter Wert ist 100


def test_rsi_only_falling_is_0():
    """Fällt der Kurs jeden Tag, gibt es keine Gewinne → RSI = 0."""
    result = indicators.rsi(make_prices(list(range(30, 0, -1))), period=14)  # 30, 29, … 1
    assert result.iloc[-1] == pytest.approx(0)  # Letzter Wert ist 0


def test_rsi_stays_between_0_and_100():
    """Bei einem gemischten Kursverlauf liegt der RSI immer zwischen 0 und 100."""
    result = indicators.rsi(make_prices([10, 12, 9, 13, 8, 15, 14, 11] * 5), period=14)  # Zickzack
    valid = result.dropna()  # Leere Anfangswerte ignorieren
    assert ((valid >= 0) & (valid <= 100)).all()  # Alle Werte im erlaubten Bereich


def test_macd_constant_price_is_zero():
    """Bei konstantem Kurs sind alle Durchschnitte gleich → MACD, Signal und Histogramm = 0."""
    result = indicators.macd(make_prices([100] * 60))  # 60 Tage konstant 100
    assert result.iloc[-1].abs().max() == pytest.approx(0)  # Alle drei Werte sind 0


def test_macd_rising_price_is_positive():
    """Bei steigendem Kurs liegt der schnelle Durchschnitt über dem langsamen → MACD > 0."""
    result = indicators.macd(make_prices(list(range(1, 61))))  # Gleichmäßig steigend
    assert result["macd"].iloc[-1] > 0  # MACD-Linie ist positiv


def test_total_return():
    """Von 100 auf 110 sind +10 % → 0.10."""
    assert indicators.total_return(make_prices([100, 105, 110])) == pytest.approx(0.10)  # +10 %


def test_max_drawdown():
    """Hoch bei 120, danach Tief bei 60 → -50 %."""
    assert indicators.max_drawdown(make_prices([100, 120, 60, 90])) == pytest.approx(-0.5)  # -50 %


def test_max_drawdown_only_rising_is_zero():
    """Steigt der Kurs nur, gab es nie einen Verlust → Drawdown 0."""
    assert indicators.max_drawdown(make_prices([1, 2, 3, 4])) == pytest.approx(0)  # Kein Verlust


def test_volatility_constant_price_is_zero():
    """Konstanter Kurs = keine Schwankung = Volatilität 0."""
    assert indicators.annualized_volatility(make_prices([100] * 10)) == pytest.approx(0)  # Keine Schwankung


def test_daily_returns():
    """100 → 110 → 99 ergibt +10 % und -10 %."""
    result = indicators.daily_returns(make_prices([100, 110, 99]))  # Tagesrenditen berechnen
    assert list(result) == pytest.approx([0.10, -0.10])  # Zwei Renditen, der erste Tag fällt weg


def test_normalize_to_100():
    """Jede Spalte muss bei 100 starten, Verhältnisse bleiben erhalten."""
    prices = pd.DataFrame({"a": [50.0, 100.0], "b": [2.0, 1.0]})  # Zwei Coins mit sehr unterschiedlichen Preisen
    result = indicators.normalize_to_100(prices)  # Normieren
    assert list(result.iloc[0]) == [100.0, 100.0]  # Beide starten bei 100
    assert list(result.iloc[1]) == [200.0, 50.0]  # a hat sich verdoppelt, b halbiert


def test_correlation_identical_series_is_one():
    """Ein Coin, der sich exakt wie ein anderer bewegt, hat Korrelation 1."""
    values = [10, 12, 9, 13, 8, 15]  # Beliebiger Kursverlauf
    prices = pd.DataFrame({"a": values, "b": [v * 2 for v in values]})  # b = a mal 2 → gleiche Renditen
    corr = indicators.correlation_matrix(prices)  # Korrelationsmatrix berechnen
    assert corr.loc["a", "b"] == pytest.approx(1.0)  # Perfekte Korrelation
