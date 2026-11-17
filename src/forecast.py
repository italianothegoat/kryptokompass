"""
Was macht diese Datei?
----------------------
Sie erstellt eine Kursprognose mit einer linearen Regression – und prüft mit einem
Backtest ehrlich, wie gut diese Methode in der Vergangenheit funktioniert hätte.

Die Idee in einfachen Worten:
1. Für jeden vergangenen Tag berechnen wir "Merkmale" aus den Indikatoren
   (RSI, MACD, Abstand zu SMA 20/50, Momentum).
2. Für jeden vergangenen Tag wissen wir auch, wie sich der Kurs in den X Tagen
   DANACH tatsächlich entwickelt hat ("Ziel").
3. Die Regression sucht die Gewichte, mit denen sich das Ziel am besten aus den
   Merkmalen berechnen lässt (Methode der kleinsten Quadrate – wie in Statistik).
4. Mit diesen Gewichten und den Merkmalen von HEUTE schätzen wir die nächsten X Tage.

Wichtig: Kryptokurse sind sehr schwer vorherzusagen. Der Backtest zeigt, wie oft
das Modell früher richtig lag. Liegt die Trefferquote nahe 50 %, ist die Prognose
kaum besser als ein Münzwurf. Keine Anlageberatung!
"""

from dataclasses import dataclass  # dataclass: einfache Klasse, die nur Werte bündelt

import numpy as np  # numpy: Rechnen mit Matrizen (für die Regression)
import pandas as pd  # pandas: Zeitreihen und Tabellen

from src import indicators  # Unsere Indikatoren (RSI, MACD, SMA)

Z_95 = 1.96  # Faktor für ein 95-%-Schwankungsband (aus der Normalverteilung)
TEST_SHARE = 0.3  # Anteil der Daten, der im Backtest als "unbekannte Zukunft" dient (30 %)

FEATURE_LABELS = {  # Deutsche Namen der Merkmale für die Anzeige
    "rsi": "RSI (14)",
    "macd_hist": "MACD-Histogramm (relativ)",
    "dist_sma20": "Abstand zu SMA 20",
    "dist_sma50": "Abstand zu SMA 50",
    "momentum_14": "Momentum (14 Tage)",
    "intercept": "Konstante",
}


@dataclass
class ForecastResult:
    """Ergebnis einer Prognose.

    Attributes:
        horizon: Prognosezeitraum in Tagen.
        last_price: Letzter bekannter Kurs.
        expected_return: Erwartete Rendite über den Zeitraum (Dezimalzahl, 0.05 = +5 %).
        predicted_price: Erwarteter Kurs am Ende des Zeitraums.
        lower_price: Untere Grenze des 95-%-Bands am Ende des Zeitraums.
        upper_price: Obere Grenze des 95-%-Bands am Ende des Zeitraums.
        path: Tabelle mit Spalten "expected", "lower", "upper" für jeden zukünftigen Tag.
        coefficients: Gewichte der Regression (welches Merkmal wie stark zählt).
    """

    horizon: int
    last_price: float
    expected_return: float
    predicted_price: float
    lower_price: float
    upper_price: float
    path: pd.DataFrame
    coefficients: pd.Series


@dataclass
class BacktestResult:
    """Ergebnis eines Backtests.

    Attributes:
        hit_rate: Anteil der Testtage, an denen die Richtung (steigt/fällt) richtig war.
        baseline_hit_rate: Trefferquote der besseren einfachen Regel ("steigt immer" oder "fällt immer").
        mean_abs_error: Durchschnittliche Abweichung der Rendite-Prognose (Dezimalzahl).
        test_days: Anzahl der Testtage.
        comparison: Tabelle mit Spalten "actual" und "predicted" (Renditen) je Testtag.
    """

    hit_rate: float
    baseline_hit_rate: float
    mean_abs_error: float
    test_days: int
    comparison: pd.DataFrame


def build_features(prices: pd.Series) -> pd.DataFrame:
    """Berechnet für jeden Tag die Merkmale, aus denen die Regression lernt.

    Alle Merkmale sind "relativ" (Prozent bzw. 0–1), damit sie bei teuren und
    billigen Coins vergleichbar sind.

    Args:
        prices: Tageskurse.

    Returns:
        Tabelle mit einer Spalte pro Merkmal. Die ersten ca. 50 Tage sind leer (Vorlauf für SMA 50).
    """
    features = pd.DataFrame(index=prices.index)  # Leere Tabelle mit denselben Tagen wie die Kurse
    features["rsi"] = indicators.rsi(prices) / 100  # RSI auf 0–1 skalieren
    features["macd_hist"] = indicators.macd(prices)["histogram"] / prices  # MACD-Histogramm relativ zum Kurs
    features["dist_sma20"] = prices / indicators.sma(prices, 20) - 1  # Wie weit liegt der Kurs über/unter SMA 20?
    features["dist_sma50"] = prices / indicators.sma(prices, 50) - 1  # Wie weit liegt der Kurs über/unter SMA 50?
    features["momentum_14"] = prices.pct_change(14)  # Kursveränderung der letzten 14 Tage
    return features  # Fertige Merkmalstabelle zurückgeben


def build_target(prices: pd.Series, horizon: int) -> pd.Series:
    """Berechnet für jeden Tag die tatsächliche Rendite der folgenden `horizon` Tage.

    Beispiel horizon=7: Wert am 01.03. = Kurs am 08.03. / Kurs am 01.03. − 1.
    Für die letzten `horizon` Tage kennen wir die Zukunft noch nicht → NaN.

    Args:
        prices: Tageskurse.
        horizon: Anzahl Tage in die Zukunft.

    Returns:
        Series mit den zukünftigen Renditen.
    """
    return prices.shift(-horizon) / prices - 1  # shift(-X) holt den Kurs von X Tagen später in die aktuelle Zeile


def fit_linear_regression(features: pd.DataFrame, target: pd.Series) -> pd.Series:
    """Schätzt die Gewichte einer linearen Regression (Methode der kleinsten Quadrate).

    Modell: Ziel ≈ Konstante + w1·Merkmal1 + w2·Merkmal2 + …

    Args:
        features: Merkmalstabelle (ohne leere Werte).
        target: Zielwerte zu denselben Tagen.

    Returns:
        Series mit einem Gewicht pro Merkmal plus "intercept" (die Konstante).
    """
    design = features.assign(intercept=1.0)  # Spalte mit lauter Einsen anhängen = Konstante im Modell
    weights, _, _, _ = np.linalg.lstsq(design.to_numpy(), target.to_numpy(), rcond=None)  # Kleinste-Quadrate-Lösung
    return pd.Series(weights, index=design.columns)  # Gewichte mit Spaltennamen zurückgeben


def predict(features: pd.DataFrame, coefficients: pd.Series) -> pd.Series:
    """Wendet die Gewichte auf Merkmale an und berechnet die vorhergesagte Rendite.

    Args:
        features: Merkmalstabelle.
        coefficients: Gewichte aus fit_linear_regression().

    Returns:
        Vorhergesagte Rendite je Zeile.
    """
    design = features.assign(intercept=1.0)[coefficients.index]  # Konstante anhängen, Spaltenreihenfolge angleichen
    return design.dot(coefficients)  # Jede Zeile: Summe aus Merkmal × Gewicht


def _training_data(prices: pd.Series, horizon: int) -> pd.DataFrame:
    """Baut die Lerntabelle: Merkmale + Ziel, nur vollständige Zeilen.

    Args:
        prices: Tageskurse.
        horizon: Prognosezeitraum in Tagen.

    Returns:
        Tabelle mit allen Merkmalsspalten und der Spalte "target".
    """
    data = build_features(prices)  # Merkmale berechnen
    data["target"] = build_target(prices, horizon)  # Ziel als zusätzliche Spalte
    return data.dropna()  # Zeilen mit Lücken (Vorlauf am Anfang, unbekannte Zukunft am Ende) entfernen


def make_forecast(prices: pd.Series, horizon: int) -> ForecastResult:
    """Erstellt eine Prognose für die nächsten `horizon` Tage.

    Args:
        prices: Tageskurse (mindestens ca. 120 Tage für sinnvolle Ergebnisse).
        horizon: Prognosezeitraum in Tagen, z. B. 7, 14 oder 30.

    Returns:
        ForecastResult mit erwartetem Kurs, Schwankungsband und Verlauf.
    """
    training = _training_data(prices, horizon)  # Lerntabelle aus der Vergangenheit
    feature_columns = [c for c in training.columns if c != "target"]  # Alle Spalten außer dem Ziel
    coefficients = fit_linear_regression(training[feature_columns], training["target"])  # Gewichte lernen

    residuals = training["target"] - predict(training[feature_columns], coefficients)  # Fehler auf den Lerndaten
    residual_std = residuals.std()  # Typische Größe des Fehlers → bestimmt die Breite des Bands

    today_features = build_features(prices).iloc[[-1]]  # Merkmale des letzten Tages (doppelte Klammer = Tabelle)
    expected_return = float(predict(today_features, coefficients).iloc[0])  # Vorhergesagte Rendite
    last_price = float(prices.iloc[-1])  # Letzter bekannter Kurs

    future_dates = pd.date_range(prices.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")  # Zukünftige Tage
    progress = pd.Series(range(1, horizon + 1), index=future_dates) / horizon  # Fortschritt 1/X … X/X für jeden Tag
    band = Z_95 * residual_std * progress ** 0.5  # Band wächst mit der Wurzel der Zeit (Unsicherheit nimmt zu)
    path = pd.DataFrame(  # Verlauf für das Diagramm
        {
            "expected": last_price * (1 + expected_return * progress),  # Erwarteter Kurs, gleichmäßig verteilt
            "lower": last_price * (1 + expected_return * progress - band),  # Untere Grenze
            "upper": last_price * (1 + expected_return * progress + band),  # Obere Grenze
        }
    )

    return ForecastResult(  # Alles zu einem Ergebnis bündeln
        horizon=horizon,
        last_price=last_price,
        expected_return=expected_return,
        predicted_price=float(path["expected"].iloc[-1]),
        lower_price=float(path["lower"].iloc[-1]),
        upper_price=float(path["upper"].iloc[-1]),
        path=path,
        coefficients=coefficients,
    )


def run_backtest(prices: pd.Series, horizon: int) -> BacktestResult:
    """Prüft die Methode an der Vergangenheit: lernen mit alten Daten, testen mit neueren.

    Ablauf:
    - Die ersten 70 % der Lerntabelle sind "Vergangenheit" (Training).
    - Danach lassen wir `horizon` Tage Abstand, damit keine Zukunftsinfos ins Training rutschen.
    - Auf den restlichen Tagen vergleichen wir Prognose und tatsächliche Entwicklung.

    Args:
        prices: Tageskurse.
        horizon: Prognosezeitraum in Tagen.

    Returns:
        BacktestResult mit Trefferquote, Vergleichswert und Fehler.
    """
    data = _training_data(prices, horizon)  # Lerntabelle
    feature_columns = [c for c in data.columns if c != "target"]  # Merkmalsspalten
    split = int(len(data) * (1 - TEST_SHARE))  # Position, an der Training endet
    train = data.iloc[:split]  # Trainingsteil
    test = data.iloc[split + horizon:]  # Testteil (mit Abstand von `horizon` Tagen)

    coefficients = fit_linear_regression(train[feature_columns], train["target"])  # Nur mit Trainingsdaten lernen
    predicted = predict(test[feature_columns], coefficients)  # Prognosen für die Testtage
    actual = test["target"]  # Was tatsächlich passiert ist

    hit_rate = float(((predicted > 0) == (actual > 0)).mean())  # Wie oft stimmte die Richtung?
    share_up = float((actual > 0).mean())  # Anteil der Testtage, an denen der Kurs danach gestiegen ist
    baseline_hit_rate = max(share_up, 1 - share_up)  # Bessere der Regeln "steigt immer" / "fällt immer"
    mean_abs_error = float((predicted - actual).abs().mean())  # Durchschnittlicher Fehler der Rendite

    return BacktestResult(  # Ergebnis bündeln
        hit_rate=hit_rate,
        baseline_hit_rate=baseline_hit_rate,
        mean_abs_error=mean_abs_error,
        test_days=len(test),
        comparison=pd.DataFrame({"actual": actual, "predicted": predicted}),
    )
