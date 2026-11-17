"""
Was macht diese Datei?
----------------------
Seite 3 – Vergleich.
2 bis 4 Coins werden gewählt. Die Seite zeigt:
- die Kursentwicklung aller Coins, auf 100 normiert, in einem Diagramm
- die Korrelationsmatrix der täglichen Renditen als Heatmap
"""

import pandas as pd  # pandas: Kursreihen zu einer Tabelle zusammenfügen
import streamlit as st  # streamlit: Oberfläche

from src import charts, data_loader, indicators  # Unsere Module
from src.formatting import format_percent  # Deutsche Prozentformatierung

DEFAULT_COINS = ["bitcoin", "ethereum", "solana"]  # Vorauswahl beim ersten Öffnen

currency = st.session_state.get("currency", "EUR")  # Gewählte Währung aus der Seitenleiste

st.title("⚖️ Vergleich")  # Seitenüberschrift

coins_result = data_loader.load_top_coins(currency.lower())  # Top 20 laden für die Auswahlliste
data_loader.show_load_status(coins_result, "Coin-Liste")  # Bei Problemen warnen bzw. abbrechen
coins = coins_result.data  # Tabelle der Top 20

coin_names = dict(zip(coins["coin_id"], coins["name"] + " (" + coins["symbol"] + ")"))  # ID → Anzeigename
defaults = [cid for cid in DEFAULT_COINS if cid in coin_names]  # Nur Vorauswahl-Coins, die es in der Liste gibt

col_coins, col_period = st.columns([2, 1])  # Zwei Spalten nebeneinander
selected = col_coins.multiselect(  # Mehrfachauswahl
    "Coins (2 bis 4)",  # Beschriftung
    options=list(coin_names.keys()),  # Alle Top-20-IDs
    default=defaults,  # Vorauswahl
    format_func=lambda cid: coin_names[cid],  # Schöne Namen anzeigen
    max_selections=4,  # Höchstens 4 Coins
)
days = col_period.radio("Zeitraum", options=[30, 90, 365], index=1, horizontal=True,  # Zeitraum (Standard 90 Tage)
                        format_func=lambda d: f"{d} Tage")  # Anzeige als "30 Tage" usw.

if len(selected) < 2:  # Für einen Vergleich braucht man mindestens zwei
    st.info("Bitte mindestens zwei Coins auswählen.")  # Freundlicher Hinweis
    st.stop()  # Rest der Seite nicht ausführen

series_list = []  # Hier sammeln wir die Kursreihen aller gewählten Coins
for coin_id in selected:  # Für jeden gewählten Coin …
    result = data_loader.load_price_history(coin_id, currency.lower())  # … Historie laden
    if result.from_database:  # Live-Abruf gescheitert, Reserve benutzt
        st.warning(f"{coin_names[coin_id]}: {result.error_message} Es werden gespeicherte Daten verwendet.")  # Hinweis
    if result.data is None:  # Gar keine Daten (weder live noch gespeichert)
        st.error(f"Für {coin_names[coin_id]} sind keine Kursdaten verfügbar.")  # Fehlermeldung
        continue  # Diesen Coin überspringen, mit dem nächsten weitermachen
    series = result.data.rename(coin_names[coin_id])  # Spalte nach dem Anzeigenamen benennen
    series_list.append(series)  # Zur Sammlung hinzufügen

if len(series_list) < 2:  # Nach Fehlern weniger als zwei übrig?
    st.stop()  # Dann können wir nichts vergleichen

prices_full = pd.concat(series_list, axis=1).dropna()  # Nebeneinanderstellen; nur Tage behalten, an denen ALLE Werte haben
prices = prices_full.iloc[-(days + 1):]  # Auf den gewählten Zeitraum zuschneiden

# ---------- Normierte Kursentwicklung ----------
st.subheader("Kursentwicklung (Start = 100)")  # Zwischenüberschrift
normalized = indicators.normalize_to_100(prices)  # Alle Coins starten bei 100
st.plotly_chart(charts.normalized_chart(normalized), width="stretch")  # Diagramm anzeigen

returns_text = ", ".join(  # Rendite jedes Coins als kurzen Text zusammenbauen
    f"**{name}:** {format_percent(indicators.total_return(prices[name]) * 100)}"  # z. B. "Bitcoin (BTC): +5,12 %"
    for name in prices.columns  # für jede Spalte (= jeden Coin)
)
st.markdown(f"Rendite im Zeitraum – {returns_text}")  # Renditen unter dem Diagramm anzeigen

with st.expander("ℹ️ Was bedeutet „auf 100 normiert“?"):  # Erklärung
    st.markdown(  # Erklärtext anzeigen
        "Bitcoin kostet zehntausende Euro, andere Coins nur Cent-Beträge – in einem normalen Diagramm "
        "wäre der kleine Coin eine flache Linie. Deshalb setzen wir den Startkurs jedes Coins auf **100**. "
        "Ein Wert von 120 bedeutet dann: +20 % seit Beginn des Zeitraums, 80 bedeutet: −20 %."
    )

# ---------- Korrelation ----------
st.subheader("Korrelation der täglichen Renditen")  # Zwischenüberschrift
corr = indicators.correlation_matrix(prices)  # Korrelationsmatrix berechnen
st.plotly_chart(charts.correlation_heatmap(corr), width="stretch")  # Heatmap anzeigen

with st.expander("ℹ️ Was bedeutet die Korrelation?"):  # Erklärung
    st.markdown(  # Erklärtext anzeigen
        "Die **Korrelation** zeigt, wie ähnlich sich zwei Coins von Tag zu Tag bewegen. "
        "**+1** heißt: Sie steigen und fallen immer gemeinsam, **0**: kein Zusammenhang, "
        "**−1**: genau gegenläufig. Viele Kryptowährungen sind stark positiv korreliert – "
        "wer mehrere davon besitzt, ist also weniger breit gestreut, als es scheint."
    )
