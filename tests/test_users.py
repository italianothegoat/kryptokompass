"""
Was macht diese Datei?
----------------------
Automatische Tests für die Benutzerverwaltung (src/users.py) und den Login (src/auth.py).

Jeder Test bekommt eine eigene, leere Test-Datenbank im temporären Ordner (tmp_path),
damit eure echten Konten nie berührt werden.
"""

import pytest  # pytest: Test-Werkzeug (fixture = Vorbereitung, die mehrere Tests teilen)

from src import users  # Das Modul, das wir testen


@pytest.fixture(autouse=True)  # autouse=True: läuft automatisch vor JEDEM Test in dieser Datei
def test_database(tmp_path, monkeypatch):
    """Leitet die Benutzerdatenbank in eine leere Test-Datei um.

    Args:
        tmp_path: Von pytest bereitgestellter, leerer Ordner.
        monkeypatch: pytest-Werkzeug, um Umgebungsvariablen nur für den Test zu ändern.
    """
    monkeypatch.setenv("USERS_SQLITE_PATH", str(tmp_path / "users.db"))  # Eigene Test-Datei verwenden
    monkeypatch.setenv("DATABASE_URL", "")  # Sicherstellen, dass NICHT die Online-Datenbank benutzt wird
    users.init_db()  # Leere Tabellen anlegen


def test_register_and_login():
    """Nach dem Registrieren klappt der Login nur mit dem richtigen Passwort."""
    assert users.register_user("Marc", "geheim123", "geheim123") is None  # Anlegen klappt (kein Fehler)
    assert users.check_login("marc", "geheim123")  # Richtiges Passwort → Login ok (Groß/klein egal)
    assert not users.check_login("marc", "falsch123")  # Falsches Passwort → abgelehnt
    assert not users.check_login("unbekannt", "geheim123")  # Unbekannter Name → abgelehnt


def test_password_is_not_stored_in_plain_text():
    """Das Passwort selbst darf nirgends in der Datenbank stehen – nur der Hash."""
    users.register_user("marc", "geheim123", "geheim123")  # Konto anlegen
    stored = users._run("SELECT password_hash FROM users", fetch=True)[0][0]  # Gespeicherten Wert lesen
    assert "geheim123" not in stored  # Klartext kommt nicht vor


def test_register_rejects_bad_input():
    """Ungültige Eingaben ergeben verständliche Fehlermeldungen statt eines Kontos."""
    assert users.register_user("ab", "geheim123", "geheim123")  # Name zu kurz
    assert users.register_user("marc!", "geheim123", "geheim123")  # Unerlaubtes Zeichen
    assert users.register_user("marc", "kurz", "kurz")  # Passwort zu kurz
    assert users.register_user("marc", "geheim123", "geheim124")  # Passwörter verschieden
    assert not users.user_exists("marc")  # Es wurde kein Konto angelegt


def test_duplicate_username_rejected():
    """Ein Benutzername kann nur einmal vergeben werden."""
    users.register_user("marc", "geheim123", "geheim123")  # Erstes Konto
    assert users.register_user("MARC", "anders123", "anders123")  # Gleicher Name (andere Schreibweise) → Fehler


def test_currency_and_watchlist_are_saved_per_user():
    """Jede Person hat ihre eigenen Einstellungen."""
    users.register_user("marc", "geheim123", "geheim123")  # Konto 1
    users.register_user("giuliano", "geheim456", "geheim456")  # Konto 2
    users.set_currency("marc", "USD")  # Marc wählt Dollar
    users.set_watchlist("marc", ["solana", "bitcoin", "solana"])  # Doppelter Eintrag wird entfernt
    assert users.get_currency("marc") == "USD"  # Marc: Dollar
    assert users.get_currency("giuliano") == "EUR"  # Giuliano: unverändert Euro
    assert users.get_watchlist("marc") == ["solana", "bitcoin"]  # Reihenfolge bleibt, keine Doppelten
    assert users.get_watchlist("giuliano") == []  # Giulianos Liste ist leer


def test_watchlist_is_limited():
    """Es werden höchstens MAX_WATCHLIST Coins gespeichert."""
    users.register_user("marc", "geheim123", "geheim123")  # Konto anlegen
    users.set_watchlist("marc", [f"coin{i}" for i in range(15)])  # 15 Coins speichern wollen
    assert len(users.get_watchlist("marc")) == users.MAX_WATCHLIST  # Nur 10 gespeichert


def test_login_required_for_website():
    """Ohne Login leitet die Website zur Login-Seite um, nach dem Login ist sie erreichbar."""
    import app  # Die Website laden (erst hier, damit die Test-Datenbank schon eingestellt ist)

    client = app.server.test_client()  # Simulierter Browser
    response = client.get("/markt")  # Unterseite ohne Login aufrufen
    assert response.status_code == 302 and response.headers["Location"].endswith("/login")  # → Umleitung zum Login
    assert client.get("/login").status_code == 200  # Login-Seite ist öffentlich

    client.post("/register", data={"username": "marc", "password": "geheim123",  # Konto anlegen
                                   "password_repeat": "geheim123"})
    response = client.post("/login", data={"username": "marc", "password": "geheim123"})  # Anmelden
    assert response.status_code == 302 and response.headers["Location"].endswith("/")  # → zur Startseite
    assert client.get("/markt").status_code == 200  # Jetzt ist die Seite erreichbar

    client.get("/logout")  # Abmelden
    assert client.get("/markt").status_code == 302  # Wieder gesperrt
