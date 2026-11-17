# 🧭 KryptoKompass

Ein Dashboard für Kryptowährungen: Marktübersicht, technische Indikatoren und Vergleich mehrerer Coins.
Gebaut mit Python und Streamlit im Rahmen des Studiengangs Digital Business Management (DHBW Stuttgart).

> **Keine Anlageberatung.** Alle Angaben ohne Gewähr, nur zu Lern- und Informationszwecken.
> Daten von [CoinGecko](https://www.coingecko.com).

## Funktionen (Version 1)

| Seite | Inhalt |
|---|---|
| 📊 Marktübersicht | Gesamt-Marktkapitalisierung, BTC-Dominanz, bester/schlechtester Coin (24 h), Top-20-Tabelle mit Suche, Sortierung und Grün/Rot-Färbung |
| 🔍 Coin-Analyse | Kurs mit SMA 20/50 und Bollinger-Bändern, RSI (14), MACD (12/26/9), Rendite, Volatilität, max. Drawdown – jeweils mit Erklärung für Laien |
| ⚖️ Vergleich | 2–4 Coins auf 100 normiert, Korrelations-Heatmap der Tagesrenditen |

Allgemein: Währung EUR/USD, Button „Daten aktualisieren“, Anzeige des Abrufzeitpunkts,
gespeicherte Daten als Reserve, falls CoinGecko nicht erreichbar ist.

## Projektstruktur

```
app.py                  Startpunkt: Navigation, Seitenleiste, Fußzeile
app_pages/
  market_overview.py    Seite 1 – Marktübersicht
  coin_analysis.py      Seite 2 – Coin-Analyse
  comparison.py         Seite 3 – Vergleich
src/
  api_client.py         Daten von CoinGecko holen
  database.py           SQLite: speichern & laden
  data_loader.py        Verbindet API + Datenbank + Zwischenspeicher
  indicators.py         Kennzahlen & Indikatoren (reines pandas)
  charts.py             Plotly-Diagramme
  formatting.py         Zahlen in deutscher Schreibweise
tests/                  Automatische Tests (pytest)
check_api.py            Testskript: API + Datenbank ohne App prüfen
```

## Architektur

```
Browser ──► Streamlit-App (app.py + app_pages/)
                 │
                 ▼
           data_loader.py ──► api_client.py ──► CoinGecko-API
                 │
                 └──────────► database.py ───► data/kryptokompass.db (SQLite)
                                                (Reserve, falls API ausfällt)
indicators.py + charts.py: Berechnung und Darstellung
```

## Lokal starten

1. Python 3.12 installieren.
2. Pakete installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. `.streamlit/secrets.toml.example` kopieren nach `.streamlit/secrets.toml` und den eigenen
   kostenlosen CoinGecko-Demo-Key eintragen. (Ohne Key funktioniert es meist auch, aber mit strengerem Limit.)
4. App starten:
   ```bash
   streamlit run app.py
   ```
   Die App öffnet sich unter http://localhost:8501.
5. Tests ausführen:
   ```bash
   pytest
   ```

## In GitHub Codespaces starten

Im Repository auf **Code → Codespaces → Create codespace on main** klicken. Die Pakete werden automatisch
installiert. Danach im Terminal `streamlit run app.py` eingeben. **Codespace nach der Arbeit stoppen!**

## Hinweis zur Datenbank auf Streamlit Cloud

Die SQLite-Datei liegt auf Streamlit Community Cloud auf einem flüchtigen Speicher und ist nach einem
Neustart der App leer. Für Version 1 ist das in Ordnung, weil sie nur als Zwischenspeicher und
Notfallreserve dient. Die Originaldaten liegen jederzeit bei CoinGecko.
