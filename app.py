"""
Was macht diese Datei?
----------------------
Sie ist der Startpunkt der App. Gestartet wird mit:   streamlit run app.py

Aufgaben dieser Datei:
- Grundeinstellungen der Seite (Titel, Icon, breites Layout)
- Datenbank-Tabellen anlegen (falls noch nicht vorhanden)
- Navigation zwischen den drei Seiten im Ordner app_pages/
- Seitenleiste, die auf ALLEN Seiten gleich ist (Währung, "Daten aktualisieren")
- Fußzeile mit Quellenangabe und "Keine Anlageberatung"

Streamlit führt diese Datei bei JEDER Interaktion (Klick, Auswahl …) komplett neu
von oben nach unten aus. Das ist das wichtigste Prinzip von Streamlit!
"""

import streamlit as st  # streamlit: baut aus Python-Code eine Web-Oberfläche

from src import database  # Unser Datenbank-Modul

st.set_page_config(  # Grundeinstellungen – muss der erste Streamlit-Befehl sein
    page_title="KryptoKompass",  # Titel im Browser-Tab
    page_icon="🧭",  # Icon im Browser-Tab
    layout="wide",  # Ganze Bildschirmbreite nutzen (wichtig für die große Tabelle)
)

database.init_db()  # Tabellen anlegen, falls es sie noch nicht gibt

navigation = st.navigation(  # Liste aller Seiten der App – erscheint links in der Seitenleiste
    [
        st.Page("app_pages/market_overview.py", title="Marktübersicht", icon="📊", default=True),  # Startseite
        st.Page("app_pages/coin_analysis.py", title="Coin-Analyse", icon="🔍"),  # Seite 2
        st.Page("app_pages/comparison.py", title="Vergleich", icon="⚖️"),  # Seite 3
    ]
)

with st.sidebar:  # Alles in diesem Block erscheint in der Seitenleiste
    st.title("🧭 KryptoKompass")  # App-Name oben in der Seitenleiste
    st.radio(  # Auswahl der Währung
        "Währung",  # Beschriftung
        options=["EUR", "USD"],  # Mögliche Werte
        horizontal=True,  # Nebeneinander statt untereinander
        key="currency",  # Unter diesem Namen liegt die Auswahl in st.session_state – alle Seiten lesen sie dort
    )
    if st.button("🔄 Daten aktualisieren", width="stretch"):  # Button über volle Breite; True, wenn gerade geklickt
        st.cache_data.clear()  # Zwischenspeicher leeren → beim Neuladen wird CoinGecko frisch gefragt
        st.toast("Zwischenspeicher geleert – Daten werden neu geladen.")  # Kurze Info-Einblendung
    st.caption("Daten werden 10 Min. (Marktdaten) bzw. 60 Min. (Kursverläufe) zwischengespeichert.")  # Hinweis zum Cache

navigation.run()  # Die aktuell gewählte Seite ausführen und anzeigen

st.divider()  # Trennlinie vor der Fußzeile
st.caption(  # Fußzeile in kleiner, grauer Schrift
    "Daten von [CoinGecko](https://www.coingecko.com). "
    "**Keine Anlageberatung** – alle Angaben ohne Gewähr, nur zu Lern- und Informationszwecken."
)
