"""
Was macht diese Datei?
----------------------
Kleine Hilfsfunktionen, die Zahlen in deutscher Schreibweise als Text ausgeben:
1234567.891 → "1.234.567,89"   (Punkt für Tausender, Komma für Dezimalstellen)

Python selbst schreibt Zahlen englisch ("1,234,567.89"). Wir lassen Python
zuerst englisch formatieren und tauschen danach Komma und Punkt aus.
"""

import pandas as pd  # pandas: nur für pd.isna (erkennt fehlende Werte)


def format_german(value: float, decimals: int = 2, show_sign: bool = False) -> str:
    """Formatiert eine Zahl auf Deutsch.

    Args:
        value: Die Zahl.
        decimals: Anzahl Nachkommastellen.
        show_sign: True = immer Vorzeichen zeigen ("+1,50" statt "1,50").

    Returns:
        Die Zahl als Text, z. B. "1.234,57" – oder "–" bei fehlendem Wert.
    """
    if pd.isna(value):  # Fehlender Wert (None oder NaN)?
        return "–"  # Dann einen Strich anzeigen
    sign = "+" if show_sign else ""  # Formatangabe für das Vorzeichen
    english = f"{value:{sign},.{decimals}f}"  # Englisch formatieren, z. B. "1,234.57"
    return english.replace(",", "X").replace(".", ",").replace("X", ".")  # Komma ↔ Punkt tauschen (X = Zwischenablage)


def format_percent(value: float, decimals: int = 2, show_sign: bool = True) -> str:
    """Formatiert eine Prozentzahl, z. B. 5.123 → "+5,12 %".

    Args:
        value: Prozentwert (5 bedeutet 5 %).
        decimals: Anzahl Nachkommastellen.
        show_sign: Vorzeichen anzeigen?

    Returns:
        Text mit Prozentzeichen.
    """
    return f"{format_german(value, decimals, show_sign)} %"  # Zahl formatieren und " %" anhängen


def format_big_number(value: float) -> str:
    """Kürzt große Zahlen lesbar ab, z. B. 2.345.000.000.000 → "2,35 Bio.".

    Args:
        value: Die Zahl.

    Returns:
        Gekürzter Text in deutscher Schreibweise.
    """
    if value >= 1e12:  # Ab einer Billion (1e12 = 1 mit 12 Nullen)
        return f"{format_german(value / 1e12)} Bio."  # In Billionen umrechnen
    if value >= 1e9:  # Ab einer Milliarde
        return f"{format_german(value / 1e9)} Mrd."  # In Milliarden umrechnen
    return f"{format_german(value / 1e6)} Mio."  # Sonst in Millionen


def format_price(value: float) -> str:
    """Formatiert einen Preis: unter 1 mit 4 Nachkommastellen (z. B. 0,1834), sonst mit 2.

    Args:
        value: Preis.

    Returns:
        Preis als Text.
    """
    if pd.isna(value):  # Fehlender Wert?
        return "–"  # Strich anzeigen
    return format_german(value, 4 if value < 1 else 2)  # Kleine Preise genauer anzeigen
