"""
Was macht diese Datei?
----------------------
Seite 2 – Coin-Analyse.
Ein Coin und ein Zeitraum werden gewählt. Dann zeigt die Seite:
- Kennzahlen: Rendite, annualisierte Volatilität, maximaler Drawdown
- Kursdiagramm mit SMA 20, SMA 50 und Bollinger-Bändern
- RSI (14) und MACD (12/26/9)
- zu jedem Indikator eine ausklappbare Erklärung für Laien
"""

import streamlit as st  # streamlit: Oberfläche

from src import charts, data_loader, indicators  # Unsere Module: Diagramme, Daten, Berechnungen
from src.formatting import format_percent  # Deutsche Prozentformatierung

currency = st.session_state.get("currency", "EUR")  # Gewählte Währung aus der Seitenleiste

st.title("🔍 Coin-Analyse")  # Seitenüberschrift

coins_result = data_loader.load_top_coins(currency.lower())  # Top 20 laden – daraus bauen wir die Auswahlliste
data_loader.show_load_status(coins_result, "Coin-Liste")  # Bei Problemen warnen bzw. abbrechen
coins = coins_result.data  # Tabelle der Top 20

coin_names = dict(zip(coins["coin_id"], coins["name"] + " (" + coins["symbol"] + ")"))  # z. B. {"bitcoin": "Bitcoin (BTC)"}
coin_ids = list(coin_names.keys())  # Liste aller IDs in Rang-Reihenfolge
default_index = coin_ids.index("bitcoin") if "bitcoin" in coin_ids else 0  # Bitcoin vorauswählen, falls vorhanden

col_coin, col_period = st.columns([2, 1])  # Zwei Spalten: Coin-Auswahl breiter als Zeitraum-Auswahl
coin_id = col_coin.selectbox(  # Aufklappliste für den Coin
    "Coin",  # Beschriftung
    options=coin_ids,  # Intern arbeiten wir mit der ID …
    index=default_index,  # Vorauswahl
    format_func=lambda cid: coin_names[cid],  # … angezeigt wird aber der schöne Name
)
days = col_period.radio("Zeitraum", options=[30, 90, 365], index=1, horizontal=True,  # Zeitraum in Tagen (Standard 90)
                        format_func=lambda d: f"{d} Tage")  # Anzeige als "30 Tage" usw.

history_result = data_loader.load_price_history(coin_id, currency.lower())  # 365 Tage Kursverlauf laden
data_loader.show_load_status(history_result, "Kursdaten")  # Stand anzeigen bzw. warnen/abbrechen
prices_full = history_result.data  # Gesamte Historie (bis zu 365 Tage)

# Indikatoren auf der GESAMTEN Historie berechnen und erst danach zuschneiden.
# So hat z. B. SMA 50 auch am ersten sichtbaren Tag schon genug Vorlauf.
sma20_full = indicators.sma(prices_full, 20)  # SMA 20
sma50_full = indicators.sma(prices_full, 50)  # SMA 50
bands_full = indicators.bollinger_bands(prices_full)  # Bollinger-Bänder
rsi_full = indicators.rsi(prices_full)  # RSI 14
macd_full = indicators.macd(prices_full)  # MACD 12/26/9

prices = prices_full.iloc[-(days + 1):]  # Nur die letzten X Tage (+1, damit die Rendite über volle X Tage geht)
visible = prices.index  # Die sichtbaren Datumswerte
sma20 = sma20_full.loc[visible]  # SMA 20 auf den sichtbaren Zeitraum zuschneiden
sma50 = sma50_full.loc[visible]  # SMA 50 zuschneiden
bands = bands_full.loc[visible]  # Bollinger-Bänder zuschneiden
rsi_values = rsi_full.loc[visible]  # RSI zuschneiden
macd_values = macd_full.loc[visible]  # MACD zuschneiden

# ---------- Kennzahlen ----------
m1, m2, m3 = st.columns(3)  # Drei Kacheln nebeneinander
m1.metric(f"Rendite ({days} Tage)", format_percent(indicators.total_return(prices) * 100))  # *100: Dezimalzahl → Prozent
m2.metric("Volatilität (annualisiert)", format_percent(indicators.annualized_volatility(prices) * 100, 1, False))  # Schwankung
m3.metric("Max. Drawdown", format_percent(indicators.max_drawdown(prices) * 100, 1))  # Größter Verlust vom Hoch

with st.expander("ℹ️ Was bedeuten diese Kennzahlen?"):  # Ausklappbares Erklärfeld
    st.markdown(  # Erklärtext (Markdown: **fett**, *kursiv*, "- " = Aufzählung)
        "- **Rendite:** Um wie viel Prozent sich der Kurs vom ersten bis zum letzten Tag des Zeitraums verändert hat.\n"
        "- **Volatilität:** Wie stark der Kurs typischerweise schwankt, hochgerechnet auf ein Jahr. "
        "60 % heißt grob: Ein Kursausschlag von ±60 % innerhalb eines Jahres wäre nicht ungewöhnlich.\n"
        "- **Maximaler Drawdown:** Der größte Verlust, den jemand erlitten hätte, der am ungünstigsten "
        "Hochpunkt gekauft und am folgenden Tiefpunkt verkauft hätte."
    )

# ---------- Kursdiagramm ----------
st.subheader("Kursverlauf mit SMA und Bollinger-Bändern")  # Zwischenüberschrift
st.plotly_chart(charts.price_chart(prices, sma20, sma50, bands, currency), width="stretch")  # Diagramm anzeigen
with st.expander("ℹ️ Was bedeuten SMA und Bollinger-Bänder?"):  # Erklärung
    st.markdown(  # Erklärtext anzeigen
        "**SMA (Simple Moving Average)** ist der Durchschnittskurs der letzten 20 bzw. 50 Tage. "
        "Er glättet das Auf und Ab und zeigt den Trend: Liegt der Kurs über dem SMA, ging es zuletzt eher aufwärts.\n\n"
        "**Bollinger-Bänder** liegen zwei Standardabweichungen über und unter dem SMA 20. "
        "Ein breites Band bedeutet starke Schwankungen, ein schmales Band einen ruhigen Markt. "
        "Kurse am Rand des Bandes gelten als ungewöhnlich hoch bzw. niedrig."
    )

# ---------- RSI ----------
st.subheader("RSI (14 Tage)")  # Zwischenüberschrift
st.plotly_chart(charts.rsi_chart(rsi_values), width="stretch")  # RSI-Diagramm anzeigen
with st.expander("ℹ️ Was bedeutet der RSI?"):  # Erklärung
    st.markdown(  # Erklärtext anzeigen
        "Der **Relative Strength Index** vergleicht die Kursgewinne mit den Kursverlusten der letzten 14 Tage "
        "und liegt immer zwischen 0 und 100. Über 70 gilt ein Coin oft als *überkauft* (stark gestiegen, "
        "evtl. Rücksetzer möglich), unter 30 als *überverkauft*. Das sind Faustregeln, keine Vorhersagen."
    )

# ---------- MACD ----------
st.subheader("MACD (12/26/9)")  # Zwischenüberschrift
st.plotly_chart(charts.macd_chart(macd_values), width="stretch")  # MACD-Diagramm anzeigen
with st.expander("ℹ️ Was bedeutet der MACD?"):  # Erklärung
    st.markdown(  # Erklärtext anzeigen
        "Der **MACD** ist der Abstand zwischen einem schnellen (12 Tage) und einem langsamen (26 Tage) "
        "Durchschnittskurs. Die **Signallinie** ist dessen Durchschnitt über 9 Tage. Kreuzt der MACD die "
        "Signallinie von unten nach oben (Balken werden grün), deuten viele das als beginnenden Aufwärtsschwung – "
        "umgekehrt als Abwärtsschwung."
    )
