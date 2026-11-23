"""
Was macht diese Datei?
----------------------
Sie liest geheime Einstellungen (API-Key, Datenbank-Adresse, Sitzungs-Schlüssel).

Reihenfolge:
1. Umgebungsvariable mit diesem Namen (so macht es Render unter "Environment")
2. Datei secrets.toml im Projektordner (so macht ihr es lokal in PyCharm)

Geheimnisse stehen dadurch NIE im Code und landen nie auf GitHub.
"""

import os  # os: Umgebungsvariablen lesen, prüfen ob eine Datei existiert
import tomllib  # tomllib: liest .toml-Dateien (seit Python 3.11 eingebaut)

SECRETS_PATH = "secrets.toml"  # Lokale Geheimnis-Datei (steht in .gitignore)


def get_secret(name: str, default: str = "") -> str:
    """Liest eine geheime Einstellung.

    Args:
        name: Name der Einstellung, z. B. "COINGECKO_API_KEY".
        default: Rückgabewert, falls die Einstellung nirgends gesetzt ist.

    Returns:
        Den Wert als Text (oder `default`).
    """
    value = os.environ.get(name, "")  # Zuerst in den Umgebungsvariablen nachsehen
    if value:  # Gefunden?
        return value  # Dann direkt verwenden
    if os.path.exists(SECRETS_PATH):  # Sonst: Gibt es eine lokale secrets.toml?
        with open(SECRETS_PATH, "rb") as file:  # Datei öffnen (tomllib verlangt Binärmodus)
            value = tomllib.load(file).get(name, "")  # Wert auslesen (oder leer)
        if value:  # Dort gefunden?
            return value  # Verwenden
    return default  # Nirgends gesetzt → Standardwert
