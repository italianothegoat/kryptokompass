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
| 👤 Mein Bereich | `/mein-bereich` | Persönlich je Konto: Lieblingswährung und eigene Watchlist (bis 10 Coins) mit aktuellen Kursen |
| Über uns | `/ueber-uns` | Team, Technik, Datenquelle, Haftungsausschluss |
| Login | `/login`, `/register`, `/logout` | Anmelden, Konto anlegen, Abmelden – ohne Login ist die Website gesperrt |

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
  my_area.py            Mein Bereich (Watchlist, Lieblingswährung)
  about.py              Über uns
assets/style.css        Aussehen der Website (wird von Dash automatisch geladen)
src/
  api_client.py         Daten von CoinGecko holen
  auth.py               Login, Registrierung, Abmelden, "Türsteher" vor jeder Seite
  users.py              Benutzerkonten & Einstellungen (SQLite lokal, Postgres online)
  config.py             Geheime Einstellungen lesen (Umgebungsvariable oder secrets.toml)
  database.py           SQLite: speichern & laden
  data_loader.py        Verbindet API + Datenbank + Zwischenspeicher
  indicators.py         Kennzahlen & Indikatoren (reines pandas)
  forecast.py           Prognose (lineare Regression) & Backtest
  charts.py             Plotly-Diagramme
  components.py         Wiederverwendbare Bausteine (Kacheln, Meldungen, Erklärfelder)
  formatting.py         Zahlen in deutscher Schreibweise
tests/                  Automatische Tests (pytest)
check_api.py            Testskript: API + Datenbank ohne Website prüfen
KryptoKompass.bat       Startmenü für Windows: Website starten, Tests, auf GitHub hochladen
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

## Der schnellste Weg (Windows): `KryptoKompass.bat`

Im Projektordner **doppelt auf `KryptoKompass.bat` klicken**. Es öffnet sich ein Menü:

| Taste | Was passiert |
|---|---|
| **1** | Website lokal starten: Beim ersten Mal wird die Python-Umgebung `.venv` angelegt und alle Pakete werden installiert (dauert ein paar Minuten). Danach öffnet sich der Browser mit http://127.0.0.1:8050. Beenden mit **Strg+C**. |
| **2** | Alle automatischen Tests ausführen |
| **3** | Änderungen auf GitHub hochladen: erst Tests (bei Fehlern wird **nichts** hochgeladen), dann kurze Beschreibung eingeben → `git add`, `git commit`, `git push`. Render veröffentlicht die neue Version danach automatisch in ca. 2–3 Minuten. |
| **4** | Beenden |

Abkürzung ohne Menü, z. B. im PyCharm-Terminal: `.\KryptoKompass.bat 1` (Website), `.\KryptoKompass.bat 2` (Tests).

Euer Arbeitsablauf: **Code in PyCharm ändern → [1] lokal ansehen → [3] hochladen → fertig.**

## Lokal starten von Hand (PyCharm oder Codespaces)

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
4. Unter **Environment Variables** eintragen (Groß-/Kleinschreibung beachten, keine Anführungszeichen):
   | Key | Value |
   |---|---|
   | `COINGECKO_API_KEY` | euer Demo-Key von CoinGecko |
   | `SECRET_KEY` | auf **Generate** klicken (Render erzeugt einen zufälligen Schlüssel) |
   | `DATABASE_URL` | Verbindungsadresse von Neon (siehe unten) |
5. **Deploy Web Service** klicken. Nach ein paar Minuten ist die Website unter
   `https://<name>.onrender.com` erreichbar. Jeder `git push` auf `main` aktualisiert sie automatisch.

Hinweise zum Free-Plan: Die Website „schläft“ nach 15 Minuten ohne Besucher ein; der nächste
Aufruf dauert dann ca. 1 Minute. Die SQLite-Datei ist nach jedem Neustart leer – für Version 1
ist das in Ordnung, weil sie nur Zwischenspeicher und Notfallreserve ist.

## Benutzerkonten: Datenbank bei Neon (kostenlos)

Render vergisst im Free-Plan bei jedem Neustart alle Dateien. Damit Konten und Watchlists erhalten
bleiben, liegen sie online in einer kostenlosen Postgres-Datenbank bei **Neon**:

1. Auf [neon.tech](https://neon.tech) mit dem GitHub-Konto registrieren und den **Free**-Plan wählen.
   ⚠️ Falls nach einer Kreditkarte gefragt wird: abbrechen.
2. **Create project** → Name z. B. `kryptokompass`, Region **Europe (Frankfurt)**.
3. Im Dashboard auf **Connect** klicken und die **Connection string** kopieren
   (beginnt mit `postgresql://…` und endet meist mit `?sslmode=require`).
4. Bei Render unter **Environment** als `DATABASE_URL` eintragen → speichern. Render startet neu,
   die Tabellen legt die Website beim Start selbst an.

Lokal ist nichts zu tun: Ohne `DATABASE_URL` speichert die Website die Konten in `data/users.db`.
Passwörter werden nie im Klartext gespeichert, sondern nur als Hash (`werkzeug.security`).

## Zur Prognose

Die Prognose nutzt eine lineare Regression (Methode der kleinsten Quadrate) mit fünf Merkmalen:
RSI, MACD-Histogramm, Abstand zu SMA 20 und SMA 50, Momentum über 14 Tage. Ein Backtest lernt
nur mit den ersten 70 % der Daten und prüft die restlichen 30 %. Verglichen wird mit der besseren
der einfachen Regeln „steigt immer“ / „fällt immer“ – nur wenn das Modell diese schlägt, ist es nützlich.
