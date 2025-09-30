:: Erstelle eine einfache Batch-Datei zum Installieren der Dependencies
@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Install Dependencies - MangaPark Downloader
REM - Installiert Pakete aus requirements.txt
REM - Installiert Playwright Browser
REM ============================================

title Install Dependencies - MangaPark Downloader
color 0A

echo === Installation gestartet %date% %time% ===

REM Python-Interpreter suchen
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON (
  where python >nul 2>nul && set "PYTHON=python"
)

if not defined PYTHON (
  echo [FEHLER] Python nicht gefunden. Bitte installieren:
  echo https://www.python.org/downloads/windows/
  echo Alternativ: winget install -e --id Python.Python.3.12
  pause
  exit /b 1
)

echo Verwende Python: %PYTHON%

REM Pip aktualisieren
echo Aktualisiere pip...
%PYTHON% -m pip install --upgrade pip

REM Requirements installieren
if exist "Data\requirements.txt" (
  echo Installiere Pakete aus Data\requirements.txt...
  %PYTHON% -m pip install -r Data\requirements.txt
) else if exist "requirements.txt" (
  echo Installiere Pakete aus requirements.txt...
  %PYTHON% -m pip install -r requirements.txt
) else (
  echo [WARNUNG] Keine requirements.txt gefunden!
  echo Installiere nur grundlegende Pakete...
  %PYTHON% -m pip install playwright pyinstaller
)

REM Playwright Browser installieren
echo Installiere Playwright Browser (Chromium)...
%PYTHON% -m playwright install chromium

echo.
echo === Installation abgeschlossen! ===
echo.
echo Du kannst jetzt die App mit main.pyw starten.
pause
