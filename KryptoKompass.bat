@echo off
REM ===========================================================================
REM Was macht diese Datei?
REM ---------------------------------------------------------------------------
REM Die Startdatei für KryptoKompass unter Windows – einfach doppelklicken.
REM Sie zeigt ein Menü:
REM   [1] Website lokal starten   -> richtet beim ersten Mal alles ein, öffnet den Browser
REM   [2] Tests ausführen         -> prüft mit pytest, ob alle Berechnungen stimmen
REM   [3] Auf GitHub hochladen    -> Tests, dann commit + push; Render veröffentlicht automatisch
REM   [4] Beenden
REM Ihr braucht dafür nur: Python 3.12 und Git (beide schon installiert).
REM ===========================================================================

REM Zeichensatz auf UTF-8 stellen, damit Umlaute (ä, ö, ü) richtig angezeigt werden
chcp 65001 >nul
REM In den Ordner wechseln, in dem diese Datei liegt (egal, von wo sie gestartet wurde)
cd /d "%~dp0"
REM Fenstertitel setzen
title KryptoKompass

REM Git suchen: zuerst über den normalen Suchpfad, sonst am Standard-Installationsort
set "GIT=git"
where git >nul 2>nul || set "GIT=C:\Program Files\Git\cmd\git.exe"
REM Pfad zum Python der Projekt-Umgebung (.venv) merken
set "PY=.venv\Scripts\python.exe"

REM Abkürzung ohne Menü: "KryptoKompass.bat 1" startet direkt die Website, "... 2" die Tests usw.
set "DIRECT="
if not "%~1"=="" (
    set "DIRECT=1"
    set "choice=%~1"
    goto dispatch
)

:menu
REM Bildschirm leeren und Menü anzeigen
cls
echo.
echo   =============================================
echo     KryptoKompass – Startmenü
echo   =============================================
echo     [1] Website lokal starten
echo     [2] Tests ausführen
echo     [3] Änderungen auf GitHub hochladen
echo         (Render veröffentlicht danach automatisch)
echo     [4] Beenden
echo   =============================================
echo.
REM Eingabe lesen (vorher leeren, damit kein alter Wert stehen bleibt)
set "choice="
set /p "choice=  Auswahl (1-4): "

:dispatch
REM Je nach Eingabe zum passenden Abschnitt springen
if "%choice%"=="1" goto start_website
if "%choice%"=="2" goto run_tests
if "%choice%"=="3" goto upload
if "%choice%"=="4" goto :eof
REM Ungültige Eingabe: bei der Abkürzung beenden, sonst Menü neu anzeigen
if defined DIRECT goto :eof
goto menu


:start_website
REM Umgebung prüfen bzw. einrichten; bei Fehler zurück ins Menü
call :setup || goto back_to_menu
REM Hinweis, falls noch kein API-Key hinterlegt ist
if not exist "secrets.toml" echo   Hinweis: Keine secrets.toml gefunden – die Website läuft ohne API-Key (strengeres Limit).
echo.
echo   Website startet … der Browser öffnet sich gleich von selbst.
echo   Beenden mit Strg+C, danach die Frage mit J beantworten.
echo.
REM Website starten (läuft, bis Strg+C gedrückt wird)
"%PY%" app.py
goto back_to_menu


:run_tests
REM Umgebung prüfen bzw. einrichten
call :setup || goto back_to_menu
echo.
REM Alle Tests im Ordner tests/ ausführen
"%PY%" -m pytest
goto back_to_menu


:upload
REM Umgebung prüfen bzw. einrichten (für die Tests nötig)
call :setup || goto back_to_menu
echo.
echo   Diese Dateien wurden geändert:
REM Kurze Liste der geänderten Dateien anzeigen
"%GIT%" status --short
echo.
REM Vor dem Hochladen testen – kaputter Code soll nicht online gehen
echo   Prüfe zuerst die Tests …
"%PY%" -m pytest -q || (
    echo.
    echo   FEHLER: Mindestens ein Test schlägt fehl. Es wurde NICHTS hochgeladen.
    echo   Bitte erst den Fehler beheben (siehe Ausgabe oben^).
    goto back_to_menu
)
echo.
REM Beschreibung der Änderung abfragen (wird zur Commit-Nachricht)
set "msg="
set /p "msg=  Kurze Beschreibung der Änderung (z. B. Überschrift geändert): "
REM Ohne Eingabe eine Standard-Beschreibung verwenden
if not defined msg set "msg=Aktualisierung"
REM Anführungszeichen entfernen, sie würden den Befehl unten durcheinanderbringen
set "msg=%msg:"=%"
REM Alle Änderungen vormerken (secrets.toml und .venv bleiben dank .gitignore draußen)
"%GIT%" add -A
REM Zwischenstand speichern; wenn sich nichts geändert hat, nur einen Hinweis zeigen
"%GIT%" commit -m "%msg%" || echo   Keine neuen Änderungen zum Speichern – lade nur Ausstehendes hoch.
REM Zu GitHub hochladen
"%GIT%" push || (
    echo.
    echo   FEHLER beim Hochladen. Häufige Ursache: Anmeldung bei GitHub abgelaufen –
    echo   einfach nochmal [3] wählen und im Anmeldefenster "Sign in with your browser" klicken.
    goto back_to_menu
)
echo.
echo   Fertig! Der Code ist auf GitHub.
echo   GitHub prüft jetzt die Tests (Reiter "Actions"), Render veröffentlicht
echo   die neue Version in ca. 2-3 Minuten (Render-Dashboard, Bereich "Events").
goto back_to_menu


:back_to_menu
REM Bei der Abkürzung (ohne Menü) direkt beenden
if defined DIRECT goto :eof
REM Warten, damit man die Ausgabe lesen kann, dann zurück ins Menü
echo.
pause
goto menu


:setup
REM ---------------------------------------------------------------------------
REM Unterprogramm: Legt beim ersten Mal die Python-Umgebung (.venv) an und
REM installiert die Pakete aus requirements.txt. Bei jedem weiteren Start geht
REM das schnell, weil pip nur prüft, ob alles da ist.
REM ---------------------------------------------------------------------------
REM Ist Python überhaupt installiert?
where python >nul 2>nul || (
    echo   FEHLER: Python wurde nicht gefunden. Bitte Python 3.12 installieren.
    exit /b 1
)
REM Projekt-Umgebung anlegen, falls sie noch fehlt
if not exist "%PY%" (
    echo   Lege die Python-Umgebung an (nur beim ersten Mal^) …
    python -m venv .venv || (
        echo   FEHLER: Die Python-Umgebung konnte nicht angelegt werden.
        exit /b 1
    )
)
REM Pakete installieren bzw. prüfen
echo   Prüfe die Pakete (beim ersten Mal dauert das einige Minuten^) …
"%PY%" -m pip install --quiet --disable-pip-version-check -r requirements.txt || (
    echo   FEHLER: Die Pakete konnten nicht installiert werden. Besteht eine Internetverbindung?
    exit /b 1
)
exit /b 0
