"""
Was macht diese Datei?
----------------------
Unterseite "Über uns" (Adresse "/ueber-uns").
Stellt das Projektteam, die verwendete Technik und die Datenquelle vor.
"""

import dash  # dash: Seite registrieren
from dash import dcc, html  # Bausteine für das Layout

dash.register_page(__name__, path="/ueber-uns", name="Über uns", order=5, title="Über uns · KryptoKompass")  # Anmelden

layout = html.Div(  # Aufbau der Seite
    [
        html.H1("Über uns"),  # Seitenüberschrift
        dcc.Markdown(  # Inhalt als Markdown (einfacher zu schreiben als viele html-Bausteine)
            """
KryptoKompass ist ein Studienprojekt im Studiengang **Digital Business Management** an der
**DHBW Stuttgart**, entwickelt von **Marc** und **Giuliano**.

### Ziel
Wir wollten verstehen, wie man Finanzdaten automatisch abruft, speichert, auswertet und
verständlich darstellt – und ausprobieren, ob sich Kryptokurse mit einfachen statistischen
Methoden vorhersagen lassen.

### Technik
| Baustein | Werkzeug |
|---|---|
| Programmiersprache | Python 3.12 |
| Website | Dash (Web-Framework vom Plotly-Team) |
| Diagramme | Plotly |
| Datenverarbeitung & Indikatoren | pandas, numpy (selbst berechnet, ohne Spezial-Bibliotheken) |
| Prognose | Lineare Regression (Methode der kleinsten Quadrate) mit Backtest |
| Datenbank | SQLite |
| Code & automatische Tests | GitHub + GitHub Actions |
| Hosting | Render (kostenloser Plan) |

### Datenquelle
Alle Marktdaten stammen von der [CoinGecko-API](https://www.coingecko.com/de/api).

### Haftungsausschluss
Alle Angaben ohne Gewähr. Die Inhalte dieser Website dienen ausschließlich Lern- und
Informationszwecken und sind **keine Anlageberatung**.
            """
        ),
    ],
    className="prose",
)
