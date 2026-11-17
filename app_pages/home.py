"""
Was macht diese Datei?
----------------------
Startseite der Website (Adresse "/").
Stellt das Projekt vor und führt mit "Kacheln" zu den Unterseiten.
Diese Seite braucht keine Daten von CoinGecko – sie lädt deshalb sofort.
"""

import dash  # dash: Seite registrieren
from dash import dcc, html  # Bausteine für das Layout

dash.register_page(__name__, path="/", name="Start", order=0, title="KryptoKompass")  # Als Startseite anmelden

SECTIONS = [  # Die Unterseiten, die auf der Startseite vorgestellt werden: (Symbol, Titel, Adresse, Beschreibung)
    ("📊", "Markt", "/markt", "Die 20 größten Kryptowährungen mit Kursveränderungen, Marktkapitalisierung "
                               "und Handelsvolumen – sortier- und durchsuchbar."),
    ("🔍", "Analyse", "/analyse", "Kursverlauf eines Coins mit technischen Indikatoren: gleitende Durchschnitte, "
                                   "Bollinger-Bänder, RSI und MACD – jeweils verständlich erklärt."),
    ("🔮", "Prognose", "/prognose", "Eine Kursprognose für 7, 14 oder 30 Tage, berechnet mit einer linearen "
                                     "Regression aus den Indikatoren – inklusive ehrlichem Backtest."),
    ("⚖️", "Vergleich", "/vergleich", "Mehrere Coins im direkten Vergleich: Kursentwicklung auf 100 normiert "
                                       "und wie stark sie sich gemeinsam bewegen."),
]

layout = html.Div(  # Aufbau der Startseite
    [
        html.Section(  # Großer Begrüßungsbereich ("Hero")
            [
                html.H1("Kryptowährungen verstehen – mit Daten statt Bauchgefühl"),  # Hauptüberschrift
                html.P(  # Einleitungstext
                    "KryptoKompass zeigt aktuelle Marktdaten, erklärt technische Indikatoren in einfachen Worten "
                    "und probiert aus, wie gut sich Kurse aus vergangenen Daten vorhersagen lassen.",
                    className="lead",
                ),
                dcc.Link("Zur Marktübersicht →", href="/markt", className="button button-primary"),  # Einstiegs-Button
            ],
            className="hero",
        ),
        html.Div(  # Raster mit einer Kachel je Unterseite
            [
                dcc.Link(  # Die ganze Kachel ist ein Link
                    [
                        html.Div(icon, className="card-icon"),  # Großes Symbol
                        html.H3(title),  # Titel
                        html.P(text),  # Beschreibung
                    ],
                    href=path,  # Ziel des Links
                    className="card",
                )
                for icon, title, path, text in SECTIONS  # Für jede Unterseite eine Kachel
            ],
            className="card-grid",
        ),
        html.Section(  # Kurzer Hinweis zur Datenquelle und Verantwortung
            [
                html.H2("Wichtig zu wissen"),  # Zwischenüberschrift
                html.Ul(  # Aufzählung
                    [
                        html.Li("Alle Kursdaten stammen von CoinGecko und werden in einer eigenen kleinen Datenbank gespeichert."),
                        html.Li("Die Prognosen sind ein Lernprojekt: Kryptokurse sind sehr schwer vorhersagbar."),
                        html.Li("Nichts auf dieser Website ist eine Anlageberatung."),
                    ]
                ),
            ],
            className="info-box",
        ),
    ]
)
