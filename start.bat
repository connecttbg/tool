@echo off
REM === Automatyczny start aplikacji Flask ===

REM 1. Sprawdź, czy środowisko istnieje
if not exist .venv (
    echo Tworzenie srodowiska wirtualnego...
    python -m venv .venv
)

REM 2. Aktywacja środowiska
call .venv\Scripts\activate.bat

REM 3. Instalacja zależności (tylko pierwszym razem)
pip install -r requirements.txt

REM 4. Ustawienie hasła administratora (zmień poniżej)
set ADMIN_PASSWORD=TwojeHaslo

REM 5. Uruchomienie aplikacji
python app.py

REM 6. Pauza, aby okno się nie zamknęło
pause
