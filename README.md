# 🧭 KryptoKompass

Eine Website für Kryptowährungen: Marktübersicht, technische Indikatoren, Kursprognose
und Vergleich mehrerer Coins. Gebaut mit Python und Dash im Rahmen des Studiengangs
Digital Business Management (DHBW Stuttgart).

> **Keine Anlageberatung.** Alle Angaben und Prognosen ohne Gewähr, nur zu Lern- und
> Informationszwecken. Daten von [CoinGecko](https://www.coingecko.com).

## Unterseiten

| Seite | Adresse | Inhalt |
|---|---|---|
| Start | `/` | Projektvorstellung mit Kacheln zu allen Unterseiten |
| 📊 Markt | `/markt` | Gesamt-Marktkapitalisierung, BTC-Dominanz, Top-Gewinner/-Verlierer, Top-20-Tabelle (sortier- und durchsuchbar, grün/rot) |
| 🔍 Analyse | `/analyse` | Kurs mit SMA 20/50 und Bollinger-Bändern, RSI (14), MACD (12/26/9), Rendite, Volatilität, max. Drawdown |
| 🔮 Prognose | `/prognose` | Kursprognose für 7/14/30 Tage per linearer Regression aus Indikatoren, mit 95-%-Band und Backtest |
| ⚖️ Vergleich | `/vergleich` | 2–4 Coins auf 100 normiert, Korrelations-Heatmap der Tagesrenditen |
| Über uns | `/ueber-uns` | Team, Technik, Datenquelle, Haftungsausschluss |

Auf allen Seiten: Währung EUR/USD, Button „Aktualisieren“, Abrufzeitpunkt, gespeicherte Daten
als Reserve, falls CoinGecko nicht erreichbar ist.

## Projektstruktur

```
app.py                  Startpunkt: Website anlegen, Kopfzeile mit Menü, Fußzeile
app_pages/              Die Unterseiten (je Datei eine Seite)
  home.py               Startseite
  market_overview.py    Markt
  coin_analysis.py      Analyse
  price_forecast.py     Prognose
  comparison.py         Vergleich
  about.py              Über uns
assets/style.css        Aussehen der Website (wird von Dash automatisch geladen)
src/
  api_client.py         Daten von CoinGecko holen
  database.py           SQLite: speichern & laden
  data_loader.py        Verbindet API + Datenbank + Zwischenspeicher
  indicators.py         Kennzahlen & Indikatoren (reines pandas)
  forecast.py           Prognose (lineare Regression) & Backtest
  charts.py             Plotly-Diagramme
  components.py         Wiederverwendbare Bausteine (Kacheln, Meldungen, Erklärfelder)
  formatting.py         Zahlen in deutscher Schreibweise
tests/                  Automatische Tests (pytest)
check_api.py            Testskript: API + Datenbank ohne Website prüfen
.python-version         Python-Version für Render (3.12)
```

## Architektur

```
Browser ──► Dash-Website auf Render (app.py + app_pages/)
                 │
                 ▼
           data_loader.py ──► api_client.py ──► CoinGecko-API
                 │
                 └──────────► database.py ───► data/kryptokompass.db (SQLite)
                                                (Reserve, falls API ausfällt)
indicators.py → forecast.py → charts.py: Berechnung, Prognose und Darstellung
```

## Lokal starten (PyCharm oder Codespaces)

1. Python 3.12 und die Pakete installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. `secrets.toml.example` kopieren nach `secrets.toml` und den eigenen kostenlosen
   CoinGecko-Demo-Key eintragen. (Ohne Key funktioniert es meist auch, aber mit strengerem Limit.)
3. Website starten:
   ```bash
   python app.py
   ```
   Dann im Browser http://127.0.0.1:8050 öffnen. Beenden mit **Strg+C** im Terminal.
4. Tests ausführen:
   ```bash
   pytest
   ```

## Auf Render veröffentlichen (kostenloser Plan)

1. Auf [render.com](https://render.com) mit dem GitHub-Konto anmelden.
   ⚠️ Falls nach einer Kreditkarte gefragt wird: abbrechen – der Free-Plan braucht keine.
2. **New → Web Service** → das GitHub-Repo `kryptokompass` auswählen.
3. Einstellungen:
   | Feld | Wert |
   |---|---|
   | Language | Python 3 |
   | Branch | `main` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:server` |
   | Instance Type | **Free** |
4. Unter **Environment Variables** eintragen: `COINGECKO_API_KEY` = euer Demo-Key.
5. **Deploy Web Service** klicken. Nach ein paar Minuten ist die Website unter
   `https://<name>.onrender.com` erreichbar. Jeder `git push` auf `main` aktualisiert sie automatisch.

Hinweise zum Free-Plan: Die Website „schläft“ nach 15 Minuten ohne Besucher ein; der nächste
Aufruf dauert dann ca. 1 Minute. Die SQLite-Datei ist nach jedem Neustart leer – für Version 1
ist das in Ordnung, weil sie nur Zwischenspeicher und Notfallreserve ist.

## Zur Prognose

Die Prognose nutzt eine lineare Regression (Methode der kleinsten Quadrate) mit fünf Merkmalen:
RSI, MACD-Histogramm, Abstand zu SMA 20 und SMA 50, Momentum über 14 Tage. Ein Backtest lernt
nur mit den ersten 70 % der Daten und prüft die restlichen 30 %. Verglichen wird mit der besseren
der einfachen Regeln „steigt immer“ / „fällt immer“ – nur wenn das Modell diese schlägt, ist es nützlich.
