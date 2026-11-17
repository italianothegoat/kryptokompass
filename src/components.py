"""
Was macht diese Datei?
----------------------
Kleine, wiederverwendbare Bausteine für die Oberfläche (Dash-Komponenten):
Kennzahlen-Kacheln, Statusmeldungen, Erklärfelder und die Coin-Auswahlliste.

In Dash ist die Oberfläche aus Python-Objekten aufgebaut, die HTML entsprechen:
html.Div(...) wird zu <div>, html.H1(...) zu <h1> usw.
"className" ist der Name einer CSS-Klasse – das Aussehen steht in assets/style.css.
"""

from dash import dcc, html  # dcc: interaktive Bausteine (Diagramme, Auswahllisten); html: normale HTML-Elemente

from src import data_loader  # Für Coin-Liste und Zeitformat


def metric_card(label: str, value: str, delta: str | None = None, delta_value: float | None = None,
                help_text: str | None = None) -> html.Div:
    """Baut eine Kennzahlen-Kachel (Überschrift, großer Wert, optional grün/rote Veränderung).

    Args:
        label: Kleine Überschrift, z. B. "BTC-Dominanz".
        value: Großer Hauptwert als Text, z. B. "59,3 %".
        delta: Optionaler Zusatztext darunter, z. B. "+1,5 % (24 h)".
        delta_value: Zahl hinter dem Zusatztext – bestimmt die Farbe (grün ≥ 0, rot < 0).
        help_text: Optionaler Erklärtext, der beim Darüberfahren mit der Maus erscheint.

    Returns:
        Ein html.Div mit der fertigen Kachel.
    """
    children = [  # Inhalt der Kachel, von oben nach unten
        html.Div(label, className="metric-label", title=help_text),  # Überschrift (title = Tooltip)
        html.Div(value, className="metric-value"),  # Großer Hauptwert
    ]
    if delta is not None:  # Nur wenn ein Zusatztext übergeben wurde …
        color = "positive" if (delta_value or 0) >= 0 else "negative"  # … Farbe abhängig vom Vorzeichen wählen
        arrow = "▲" if (delta_value or 0) >= 0 else "▼"  # Pfeil nach oben oder unten
        children.append(html.Div(f"{arrow} {delta}", className=f"metric-delta {color}"))  # Zusatzzeile anhängen
    return html.Div(children, className="metric-card")  # Alles in einen Kasten packen


def status_message(result: data_loader.LoadResult, label: str) -> html.Div:
    """Zeigt an, wie aktuell die Daten sind – oder warnt freundlich bei Problemen.

    Args:
        result: Ergebnis einer Lade-Funktion aus data_loader.
        label: Kurzer Name der Daten, z. B. "Marktdaten".

    Returns:
        Grauer Hinweis (alles ok), gelbe Warnung (Reserve aus DB) oder roter Fehler (keine Daten).
    """
    if result.data is None:  # Weder live noch aus der Datenbank etwas bekommen
        return html.Div(  # Roter Fehlerkasten
            f"{label} konnten nicht geladen werden: {result.error_message} "
            "Leider sind auch noch keine gespeicherten Daten vorhanden.",
            className="alert alert-error",
        )
    if result.from_database:  # Live-Abruf gescheitert, aber Reserve vorhanden
        return html.Div(  # Gelber Warnkasten
            f"{result.error_message} Angezeigt werden gespeicherte {label} "
            f"vom {data_loader.format_timestamp(result.fetched_at)}.",
            className="alert alert-warning",
        )
    return html.Div(  # Dezenter grauer Hinweis
        f"{label}: Stand {data_loader.format_timestamp(result.fetched_at)}",
        className="status",
    )


def explanation(title: str, text: str) -> html.Details:
    """Ausklappbares Feld "Was bedeutet das?" (HTML-Element <details>).

    Args:
        title: Text auf dem Klappfeld.
        text: Erklärung in Markdown (**fett**, *kursiv*, "- " für Aufzählungen).

    Returns:
        Ein aufklappbares html.Details-Element.
    """
    return html.Details(  # <details> klappt beim Klick auf <summary> auf und zu – ganz ohne Python-Code
        [
            html.Summary(f"ℹ️ {title}"),  # Sichtbare Zeile zum Anklicken
            dcc.Markdown(text),  # Erklärtext, Markdown wird zu HTML umgewandelt
        ],
        className="explanation",
    )


def coin_options(currency: str):
    """Baut die Auswahlliste der Top-20-Coins für Dropdowns.

    Args:
        currency: "EUR" oder "USD".

    Returns:
        Tupel (Liste von {"label": "Bitcoin (BTC)", "value": "bitcoin"}, LoadResult).
        Die Liste ist leer, wenn keine Coin-Daten verfügbar sind.
    """
    result = data_loader.load_top_coins(currency.lower())  # Top 20 laden (meist aus dem Zwischenspeicher)
    if result.data is None:  # Keine Daten?
        return [], result  # Leere Liste zurückgeben
    coins = result.data  # Tabelle der Top 20
    options = [  # Für jeden Coin einen Eintrag bauen
        {"label": f"{row['name']} ({row['symbol']})", "value": row["coin_id"]}  # Angezeigter Text und interner Wert
        for _, row in coins.iterrows()  # iterrows() liefert jede Tabellenzeile einzeln
    ]
    return options, result  # Liste und Ladeergebnis zurückgeben


def graph(figure) -> dcc.Graph:
    """Packt ein Plotly-Diagramm in eine Dash-Komponente mit einheitlichen Einstellungen.

    Args:
        figure: Plotly-Figure aus charts.py.

    Returns:
        dcc.Graph zum Einbauen in die Seite.
    """
    return dcc.Graph(  # Interaktives Diagramm
        figure=figure,  # Das eigentliche Diagramm
        config={"displaylogo": False},  # Plotly-Logo in der Werkzeugleiste ausblenden
    )
