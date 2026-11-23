"""
Was macht diese Datei?
----------------------
Sie kümmert sich um Anmelden, Registrieren und Abmelden.

So funktioniert es:
- Unter Dash läuft ein Flask-Webserver. Diesem geben wir drei zusätzliche Adressen:
  /login (Anmelden), /register (Konto anlegen) und /logout (Abmelden).
- Nach erfolgreichem Login merkt sich Flask in einem verschlüsselten Cookie
  ("Sitzung"), wer angemeldet ist. Der Schlüssel dafür ist SECRET_KEY.
- Vor JEDER Anfrage prüft eine "Türsteher"-Funktion, ob jemand angemeldet ist.
  Wenn nicht, geht es zur Login-Seite.

Die Login-Seiten sind einfaches HTML (keine Dash-Seiten), damit man sie auch
ohne Anmeldung aufrufen kann.
"""

import os  # os: prüfen, ob die Website auf Render läuft
from datetime import timedelta  # timedelta: Zeitspanne (wie lange man angemeldet bleibt)

import flask  # flask: der Webserver unter Dash (Sitzung, Weiterleitungen, Formulare)

from src import config, users  # Einstellungen und Benutzerdatenbank

PUBLIC_PATHS = ("/login", "/register", "/assets/", "/_favicon.ico")  # Adressen, die man ohne Login sehen darf
DEV_SECRET_KEY = "nur-lokal-zum-testen-nicht-online-verwenden"  # Ersatz-Schlüssel, NUR für lokale Tests

PAGE_TEMPLATE = """
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · KryptoKompass</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <div class="auth-page">
    <form class="auth-card" method="post">
      <h1>🧭 KryptoKompass</h1>
      <h2>{{ title }}</h2>
      {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
      {% if message %}<div class="alert alert-info">{{ message }}</div>{% endif %}
      <label for="username">Benutzername</label>
      <input id="username" name="username" value="{{ username }}" autocomplete="username" required>
      <label for="password">Passwort</label>
      <input id="password" name="password" type="password" required
             autocomplete="{{ 'new-password' if register else 'current-password' }}">
      {% if register %}
        <label for="password_repeat">Passwort wiederholen</label>
        <input id="password_repeat" name="password_repeat" type="password" autocomplete="new-password" required>
        <p class="hint">3–30 Zeichen (a–z, 0–9, _ und -), Passwort mindestens 8 Zeichen.</p>
        <button class="button button-primary" type="submit">Konto anlegen</button>
        <p>Schon ein Konto? <a href="/login">Zum Login</a></p>
      {% else %}
        <button class="button button-primary" type="submit">Anmelden</button>
        <p>Noch kein Konto? <a href="/register">Jetzt registrieren</a></p>
      {% endif %}
      <p class="hint">Keine Anlageberatung – nur zu Lern- und Informationszwecken.</p>
    </form>
  </div>
</body>
</html>
"""  # HTML-Vorlage für Login und Registrierung; {{ … }} wird von Flask ausgefüllt (und sicher "escaped")


def current_user() -> str | None:
    """Gibt den Namen der angemeldeten Person zurück.

    Returns:
        Benutzername oder None, wenn niemand angemeldet ist (oder gerade keine Anfrage läuft).
    """
    if not flask.has_request_context():  # Außerhalb einer Anfrage (z. B. beim Programmstart)?
        return None  # Dann gibt es keine Sitzung
    return flask.session.get("username")  # Namen aus der Sitzung lesen


def _render(title: str, register: bool, error: str = "", message: str = "", username: str = "") -> str:
    """Baut die Login- bzw. Registrierungsseite aus der Vorlage.

    Args:
        title: Überschrift, z. B. "Anmelden".
        register: True = Registrierungsformular, False = Login-Formular.
        error: Rote Fehlermeldung (optional).
        message: Blaue Hinweismeldung (optional).
        username: Vorausgefüllter Benutzername (damit man ihn nicht neu tippen muss).

    Returns:
        Fertiges HTML.
    """
    return flask.render_template_string(  # Vorlage ausfüllen; Sonderzeichen werden automatisch entschärft
        PAGE_TEMPLATE, title=title, register=register, error=error, message=message, username=username
    )


def login_page():
    """Adresse /login: zeigt das Formular (GET) oder prüft die Eingaben (POST).

    Returns:
        HTML-Seite oder Weiterleitung zur Startseite.
    """
    if flask.request.method == "GET":  # Seite nur aufrufen
        return _render("Anmelden", register=False, message=flask.request.args.get("message", ""))  # Formular zeigen
    username = users.normalize_username(flask.request.form.get("username"))  # Eingabe lesen und vereinheitlichen
    if users.check_login(username, flask.request.form.get("password")):  # Name und Passwort korrekt?
        flask.session.clear()  # Alte Sitzungsdaten verwerfen (Sicherheit)
        flask.session["username"] = username  # Angemeldete Person merken
        flask.session.permanent = True  # Sitzung bleibt auch nach Schließen des Browsers bestehen
        return flask.redirect("/")  # Zur Startseite
    return _render("Anmelden", register=False, username=username,  # Formular mit Fehlermeldung erneut zeigen
                   error="Benutzername oder Passwort ist falsch.")


def register_page():
    """Adresse /register: zeigt das Formular (GET) oder legt ein Konto an (POST).

    Returns:
        HTML-Seite oder Weiterleitung zur Login-Seite.
    """
    if flask.request.method == "GET":  # Seite nur aufrufen
        return _render("Konto anlegen", register=True)  # Leeres Formular zeigen
    form = flask.request.form  # Formulardaten
    error = users.register_user(form.get("username"), form.get("password"), form.get("password_repeat"))  # Anlegen
    if error:  # Hat etwas nicht gepasst?
        return _render("Konto anlegen", register=True, error=error,  # Formular mit Fehlermeldung zeigen
                       username=users.normalize_username(form.get("username")))
    return flask.redirect("/login?message=Konto+angelegt+%E2%80%93+bitte+jetzt+anmelden.")  # Weiter zum Login


def logout_page():
    """Adresse /logout: meldet ab und führt zur Login-Seite.

    Returns:
        Weiterleitung zur Login-Seite.
    """
    flask.session.clear()  # Sitzung löschen = abgemeldet
    return flask.redirect("/login?message=Du+bist+abgemeldet.")  # Zur Login-Seite mit Hinweis


def require_login():
    """Türsteher: läuft vor JEDER Anfrage und lässt nur Angemeldete durch.

    Returns:
        None (= durchlassen), eine Weiterleitung zur Login-Seite oder einen 401-Fehler.
    """
    path = flask.request.path  # Aufgerufene Adresse, z. B. "/markt"
    if current_user() or path.startswith(PUBLIC_PATHS):  # Angemeldet oder öffentliche Adresse?
        return None  # Durchlassen
    if path.startswith("/_dash"):  # Interne Dash-Anfrage (z. B. ein Callback) ohne Login?
        return "Nicht angemeldet", 401  # Ablehnen (die Seite selbst leitet beim Neuladen zum Login)
    return flask.redirect("/login")  # Alle anderen Seiten → zum Login


def setup_auth(server: flask.Flask) -> None:
    """Richtet Sitzung, Login-Adressen und Türsteher am Flask-Server ein.

    Args:
        server: Der Flask-Server unter Dash (app.server).

    Raises:
        RuntimeError: Wenn auf Render kein SECRET_KEY gesetzt ist (sonst wären Sitzungen unsicher).
    """
    secret_key = config.get_secret("SECRET_KEY")  # Schlüssel für die Sitzungs-Cookies
    running_on_render = bool(os.environ.get("RENDER"))  # Render setzt diese Variable automatisch
    if not secret_key and running_on_render:  # Online ohne Schlüssel?
        raise RuntimeError("SECRET_KEY fehlt! Bitte bei Render unter Environment eintragen.")  # Lieber gar nicht starten
    server.secret_key = secret_key or DEV_SECRET_KEY  # Schlüssel setzen (lokal notfalls den Test-Schlüssel)
    server.config.update(  # Sicherheits-Einstellungen für das Sitzungs-Cookie
        SESSION_COOKIE_HTTPONLY=True,  # JavaScript darf das Cookie nicht lesen
        SESSION_COOKIE_SAMESITE="Lax",  # Schutz davor, dass fremde Seiten Formulare in eurem Namen absenden
        SESSION_COOKIE_SECURE=running_on_render,  # Online nur über HTTPS senden
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # Nach 7 Tagen muss man sich neu anmelden
    )
    users.init_db()  # Benutzer-Tabellen anlegen, falls nötig
    server.add_url_rule("/login", "login", login_page, methods=["GET", "POST"])  # Adresse /login
    server.add_url_rule("/register", "register", register_page, methods=["GET", "POST"])  # Adresse /register
    server.add_url_rule("/logout", "logout", logout_page)  # Adresse /logout
    server.before_request(require_login)  # Türsteher vor jede Anfrage stellen
