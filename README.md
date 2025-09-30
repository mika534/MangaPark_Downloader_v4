MangaPark Downloader v4
========================
Autor: Mika534
Senior Developer: ChatGPT, Claude AI
Version: 4.3.6
========================

Kurzbeschreibung
----------------
Der MangaPark Downloader ist ein Desktop-Tool für Windows, um Webtoon-/Manga-Kapitel von MangaPark.net herunterzuladen. 
Es unterstützt Einzel- und Bulk-Downloads, erstellt automatisch PDFs aus den heruntergeladenen Bildern und kann diese 
optional in größere PDF-Bundles zusammenführen.

Features
--------
- Single-Download: Mit nur einer URL den gesamten Manga herunterladen.
- Bulk-Download: Mehrere URL in eine Warteschlange hinzufügen und herunterladen.
- Download-Modus: Manuell (feste Anzahl an Kapiteln) oder Automatisch (bis das Ende des Manga erkannt wird).
- PDF-Erstellung: Erstellt aus den heruntergeladenen Bildern PDFs.
- Merge: Zusammenführen mehrerer PDFs in ein Bundle.

Systemvoraussetzungen
---------------------
- Windows mit Python 3.10 oder höher (getestet mit Python 3.13).
- Internetverbindung (für Paket-Installation und Playwright-Browser-Download erforderlich).

Installation
------------
1) Python installieren (erforderlich)
   - Falls noch nicht installiert: https://www.python.org/downloads/windows/
   - Empfohlene Version: Python 3.12 oder höher
   - Wichtig: Stelle sicher, dass Python zu PATH hinzugefügt wird (beim Installer aktivieren)

2) Dependencies installieren (empfohlen: automatisch)
   - Doppelklick auf `install_deps.bat` im Projektordner
   - Das Skript installiert automatisch alle erforderlichen Pakete und den Playwright-Browser
   - Alternative in CMD/PowerShell folgendes ausführen:
     ```
     python -m pip install --upgrade pip
     python -m pip install -r Data/requirements.txt
     python -m playwright install chromium
     ```

3) Manuelle Installation (falls auto nicht funktioniert)
   - CMD oder PowerShell im Projektordner öffnen
   - Nacheinander ausführen:
     - `python -m pip install --upgrade pip`
     - `python -m pip install -r Data/requirements.txt`
     - `python -m playwright install chromium`

Verwendung
----------
- `main.pyw` starten (Doppelklick) und GUI verwenden.
- Felder ausfüllen:
  - Start Chapter URL
  - Manga-Titel
  - Zielordner (oder Standardordner) verwenden
- Modus wählen: Manuell (Anzahl Kapitel) oder Automatisch.
- Optional: Nach Download Bilder löschen, PDFs später zusammenführen (Merge-Optionen).
- Download starten und Fortschritt abwarten.


Konfiguration & Umgebungsvariablen (optional)
---------------------------------------------
- `MPD_OPERA_PROFILE` – Pfad zum persistenten Chromium/Opera-Profil (für Playwright). Beispiel:
  - `C:\Users\<USER>\AppData\Roaming\Opera Software\Opera Stable\Default`
- `MPD_WAIT_AFTER_LOAD` – Wartezeit in Sekunden nach Seitenladen (Standard: 4).
- `MPD_DOWNLOAD_DELAY` – Verzögerung zwischen Bild-Downloads (Sekunden, Standard: 0.2).
- `MPD_CHAPTER_DELAY` – Verzögerung zwischen Kapiteln (Sekunden, Standard: 2.0).
- `MPD_KEEP_BROWSER_OPEN` – `1`, um Browser nach Ende offen zu lassen (Debug), sonst `0`.

Bekannte Hinweise/Tipps
-----------------------
- Playwright öffnet ein sichtbares Chromium-Fenster. Bitte während des Downloads nicht schließen.
- Bei Cookie-/Login-Problemen kann ein bestehendes Browser-Profil via `MPD_OPERA_PROFILE` helfen.
- Bei sehr langen Bildern reduziert die App automatisch die Anzahl Bilder pro PDF-Seite, um Limits zu vermeiden.

Troubleshooting
---------------
- "Downloader nicht verfügbar":
  - `install_deps.bat` ausführen oder manuell `pip install -r requirements.txt`.
- Playwright-Fehler (z. B. Browser fehlt):
  - `python -m playwright install chromium` erneut ausführen.
- Merge-Fehler oder keine PDFs erkannt:
  - Dateinamen müssen das Kapitel enthalten (z. B. `Chapter_001 - Titel.pdf`), damit sie erkannt werden.
- Batch-Datei schließt sich sofort:
  - Terminal manuell öffnen, in den Projektordner wechseln und `install_deps.bat` ausführen, um die Ausgabe zu sehen.

Lizenz
------
Dieses Projekt ist unter der MIT-Lizenz lizenziert. Siehe die Datei LICENSE für den vollständigen Lizenztext.
