"""
Was macht diese Datei?
----------------------
Automatische Tests für src/forecast.py (Regression, Prognose, Backtest).
"""

import numpy as np  # numpy: Zufallszahlen für realistische Test-Kurse
import pandas as pd  # pandas: Testdaten bauen
import pytest  # pytest: pytest.approx = "ungefähr gleich"

from src import forecast  # Das Modul, das wir testen


def make_prices(values) -> pd.Series:
    """Hilfsfunktion: baut aus Zahlen eine Kursreihe mit Tagesdatum als Index.

    Args:
        values: Kurse.

    Returns:
        Series mit einem Wert pro Tag ab 01.01.2026.
    """
    dates = pd.date_range("2026-01-01", periods=len(values), freq="D")  # Fortlaufende Tage
    return pd.Series(list(values), index=dates, dtype=float)  # Zeitreihe bauen


def random_walk(days: int = 365, seed: int = 42) -> pd.Series:
    """Erzeugt einen zufälligen, aber reproduzierbaren Kursverlauf (wie ein echter Coin).

    Args:
        days: Anzahl Tage.
        seed: Startwert des Zufallsgenerators – gleicher Seed = gleiche Zahlen.

    Returns:
        Kursreihe, die bei 100 startet.
    """
    rng = np.random.default_rng(seed)  # Zufallsgenerator mit festem Startwert
    daily_returns = rng.normal(0.001, 0.03, days)  # Tagesrenditen: im Schnitt +0,1 %, Schwankung 3 %
    return make_prices(100 * np.cumprod(1 + daily_returns))  # Renditen zu Kursen aufmultiplizieren


def test_build_target():
    """100 → 110 → 121: Die 1-Tages-Rendite ist jeweils +10 %, der letzte Tag ist unbekannt."""
    target = forecast.build_target(make_prices([100, 110, 121]), horizon=1)  # Ziel berechnen
    assert target.iloc[0] == pytest.approx(0.1)  # Tag 1 → Tag 2: +10 %
    assert target.iloc[1] == pytest.approx(0.1)  # Tag 2 → Tag 3: +10 %
    assert pd.isna(target.iloc[2])  # Zukunft von Tag 3 ist unbekannt


def test_regression_finds_known_weights():
    """Bei y = 2·x + 1 muss die Regression genau Gewicht 2 und Konstante 1 finden."""
    x = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0, 4.0]})  # Ein Merkmal
    y = 2 * x["x"] + 1  # Bekannter Zusammenhang
    weights = forecast.fit_linear_regression(x, y)  # Gewichte schätzen
    assert weights["x"] == pytest.approx(2.0)  # Steigung stimmt
    assert weights["intercept"] == pytest.approx(1.0)  # Konstante stimmt


def test_predict_uses_weights():
    """Vorhersage = Konstante + Gewicht × Merkmal."""
    weights = pd.Series({"x": 2.0, "intercept": 1.0})  # Feste Gewichte
    result = forecast.predict(pd.DataFrame({"x": [10.0]}), weights)  # Für x = 10 vorhersagen
    assert result.iloc[0] == pytest.approx(21.0)  # 2 · 10 + 1 = 21


def test_forecast_shape_and_band():
    """Die Prognose hat einen Wert pro Zukunftstag und das Band umschließt den erwarteten Kurs."""
    result = forecast.make_forecast(random_walk(), horizon=14)  # 14-Tage-Prognose
    assert len(result.path) == 14  # 14 zukünftige Tage
    assert result.lower_price < result.predicted_price < result.upper_price  # Erwartung liegt im Band
    assert (result.path["upper"] >= result.path["lower"]).all()  # Band nie "verdreht"
    assert result.path.index[0] > random_walk().index[-1]  # Prognose beginnt NACH dem letzten bekannten Tag


def test_forecast_rising_series_predicts_rise():
    """Steigt ein Kurs gleichmäßig, muss die Prognose ebenfalls einen Anstieg erwarten."""
    prices = make_prices(100 * 1.01 ** np.arange(200))  # Jeden Tag +1 %
    result = forecast.make_forecast(prices, horizon=7)  # 7-Tage-Prognose
    assert result.expected_return == pytest.approx(1.01 ** 7 - 1, rel=0.01)  # ca. +7,2 %
    assert result.predicted_price > result.last_price  # Erwarteter Kurs liegt höher


def test_backtest_values_are_valid():
    """Trefferquoten liegen zwischen 0 und 1, und es gibt Testtage."""
    result = forecast.run_backtest(random_walk(), horizon=7)  # Backtest auf Zufallskursen
    assert 0 <= result.hit_rate <= 1  # Gültige Quote
    assert 0.5 <= result.baseline_hit_rate <= 1  # Bessere der beiden einfachen Regeln schafft immer mind. 50 %
    assert result.test_days > 50  # Genug Testtage für eine Aussage
    assert len(result.comparison) == result.test_days  # Vergleichstabelle passt zur Anzahl
