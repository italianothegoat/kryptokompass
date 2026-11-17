"""
Was macht diese Datei?
----------------------
Sie berechnet alle Kennzahlen und technischen Indikatoren – nur mit pandas, ohne
Spezial-Bibliotheken, damit man jede Formel nachvollziehen kann.

Alle Funktionen bekommen eine pandas-Series mit Tageskursen (Index = Datum)
und geben Zahlen, Series oder DataFrames zurück. Sie wissen nichts von
Streamlit oder CoinGecko – deshalb lassen sie sich einfach mit pytest testen.
"""

import pandas as pd  # pandas: Rechnen mit Zeitreihen

TRADING_DAYS_PER_YEAR = 365  # Krypto wird an allen 365 Tagen gehandelt (Aktien: ca. 252)


def sma(prices: pd.Series, window: int) -> pd.Series:
    """Einfacher gleitender Durchschnitt (Simple Moving Average, SMA).

    Für jeden Tag: Durchschnitt der letzten `window` Schlusskurse.
    Die ersten `window - 1` Tage haben noch nicht genug Daten → NaN (leer).

    Args:
        prices: Tageskurse.
        window: Anzahl Tage, z. B. 20 oder 50.

    Returns:
        Series mit den Durchschnittswerten.
    """
    return prices.rolling(window=window).mean()  # "rolling" = rollendes Fenster über die letzten X Tage


def bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger-Bänder: Mittellinie (SMA) plus/minus ein Vielfaches der Standardabweichung.

    Die Bänder zeigen, wie stark der Kurs zuletzt geschwankt hat:
    weit auseinander = unruhiger Markt, eng zusammen = ruhiger Markt.

    Args:
        prices: Tageskurse.
        window: Fenstergröße in Tagen (Standard 20).
        num_std: Wie viele Standardabweichungen Abstand (Standard 2).

    Returns:
        DataFrame mit den Spalten "middle", "upper", "lower".
    """
    middle = sma(prices, window)  # Mittellinie = SMA 20
    std = prices.rolling(window=window).std(ddof=0)  # Standardabweichung im gleichen Fenster (Bollinger-Konvention: ddof=0)
    return pd.DataFrame(  # Drei Linien zu einer Tabelle zusammenfassen
        {
            "middle": middle,  # Mittellinie
            "upper": middle + num_std * std,  # Oberes Band
            "lower": middle - num_std * std,  # Unteres Band
        }
    )


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (RSI) nach J. Welles Wilder.

    Vergleicht die durchschnittlichen Kursgewinne mit den durchschnittlichen Kursverlusten
    der letzten `period` Tage. Ergebnis liegt zwischen 0 und 100.
    Über 70 gilt oft als "überkauft", unter 30 als "überverkauft".

    Args:
        prices: Tageskurse.
        period: Anzahl Tage (Standard 14).

    Returns:
        Series mit RSI-Werten (0–100). Die ersten Tage sind NaN.
    """
    change = prices.diff()  # Veränderung zum Vortag (erster Wert ist NaN)
    gain = change.clip(lower=0)  # Nur Gewinne behalten, Verluste werden zu 0
    loss = -change.clip(upper=0)  # Nur Verluste behalten (als positive Zahl), Gewinne werden zu 0
    # Wilder-Glättung: eine Art gleitender Durchschnitt, der neuere Tage etwas stärker gewichtet
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()  # Durchschnittlicher Gewinn
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()  # Durchschnittlicher Verlust
    rs = avg_gain / avg_loss  # "Relative Stärke" = Gewinne geteilt durch Verluste
    result = 100 - 100 / (1 + rs)  # Umrechnen auf eine Skala von 0 bis 100
    result[(avg_loss == 0) & (avg_gain > 0)] = 100.0  # Nur Gewinne, keine Verluste → RSI = 100 (sonst Division durch 0)
    result[(avg_loss == 0) & (avg_gain == 0)] = 50.0  # Kurs völlig unverändert → neutral 50
    return result  # Fertige RSI-Reihe zurückgeben


def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence).

    MACD-Linie   = schneller EMA (12 Tage) minus langsamer EMA (26 Tage)
    Signallinie  = EMA (9 Tage) der MACD-Linie
    Histogramm   = MACD-Linie minus Signallinie

    EMA = exponentieller gleitender Durchschnitt: wie SMA, nur zählen neuere Tage mehr.

    Args:
        prices: Tageskurse.
        fast: Tage für den schnellen EMA (Standard 12).
        slow: Tage für den langsamen EMA (Standard 26).
        signal: Tage für die Signallinie (Standard 9).

    Returns:
        DataFrame mit den Spalten "macd", "signal", "histogram".
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()  # Schneller EMA
    ema_slow = prices.ewm(span=slow, adjust=False).mean()  # Langsamer EMA
    macd_line = ema_fast - ema_slow  # MACD-Linie
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()  # Signallinie
    return pd.DataFrame(  # Alles zu einer Tabelle zusammenfassen
        {
            "macd": macd_line,  # MACD-Linie
            "signal": signal_line,  # Signallinie
            "histogram": macd_line - signal_line,  # Differenz als Balken
        }
    )


def daily_returns(prices: pd.Series) -> pd.Series:
    """Tägliche Rendite: prozentuale Veränderung von einem Tag zum nächsten (als Dezimalzahl).

    Beispiel: 100 € → 105 € ergibt 0.05 (= +5 %).

    Args:
        prices: Tageskurse.

    Returns:
        Series der Tagesrenditen (der erste Tag fällt weg, weil es keinen Vortag gibt).
    """
    return prices.pct_change().dropna()  # pct_change = (heute / gestern) - 1; leere Werte entfernen


def total_return(prices: pd.Series) -> float:
    """Gesamtrendite im Zeitraum: vom ersten bis zum letzten Kurs.

    Args:
        prices: Tageskurse.

    Returns:
        Rendite als Dezimalzahl, z. B. 0.25 für +25 %.
    """
    return prices.iloc[-1] / prices.iloc[0] - 1  # Letzter Kurs geteilt durch ersten Kurs, minus 1


def annualized_volatility(prices: pd.Series) -> float:
    """Annualisierte Volatilität: wie stark der Kurs schwankt, hochgerechnet auf ein Jahr.

    Formel: Standardabweichung der Tagesrenditen × Wurzel(365).

    Args:
        prices: Tageskurse.

    Returns:
        Volatilität als Dezimalzahl, z. B. 0.6 für 60 % pro Jahr.
    """
    return daily_returns(prices).std() * TRADING_DAYS_PER_YEAR ** 0.5  # Tagesschwankung × Wurzel(365) = Jahresschwankung


def max_drawdown(prices: pd.Series) -> float:
    """Maximaler Drawdown: der größte Verlust von einem Höchststand bis zum nachfolgenden Tiefpunkt.

    Beispiel: Kurs steigt auf 120, fällt dann auf 60 → Drawdown = -50 %.

    Args:
        prices: Tageskurse.

    Returns:
        Größter Verlust als (negative) Dezimalzahl, z. B. -0.5 für -50 %.
    """
    running_max = prices.cummax()  # Bisheriger Höchststand an jedem Tag
    drawdown = prices / running_max - 1  # Wie weit liegt der Kurs unter dem bisherigen Hoch?
    return drawdown.min()  # Der schlimmste (kleinste) Wert ist der maximale Drawdown


def normalize_to_100(prices: pd.DataFrame) -> pd.DataFrame:
    """Setzt den ersten Kurs jeder Spalte auf 100, damit man Coins mit sehr
    unterschiedlichen Preisen (z. B. 90.000 € vs. 0,50 €) in einem Diagramm vergleichen kann.

    Args:
        prices: Tabelle mit einer Spalte pro Coin (Index = Datum).

    Returns:
        Tabelle, in der jede Spalte bei 100 startet.
    """
    return prices / prices.iloc[0] * 100  # Jede Zeile durch die erste Zeile teilen, mal 100


def correlation_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Korrelationsmatrix der täglichen Renditen.

    Korrelation +1: Coins bewegen sich immer gleich. 0: kein Zusammenhang. -1: genau gegensätzlich.

    Args:
        prices: Tabelle mit einer Spalte pro Coin (Index = Datum).

    Returns:
        Quadratische Tabelle mit den Korrelationen jedes Coin-Paares.
    """
    returns = prices.pct_change().dropna()  # Tagesrenditen aller Coins berechnen
    return returns.corr()  # Korrelation jedes Spaltenpaares berechnen
