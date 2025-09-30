"""
Hilfe-Texte und Tooltips für den MangaPark Downloader
"""

# Tooltip-Texte für alle UI-Elemente
TOOLTIP_TEXTS = {
    "single_downloader": {
        # URL-Eingabe
        "url_entry": "Die URL eines Manga-Kapitels einfügen.",
        
        # Download-Modus
        "manual_mode": "Ladet eine bestimmte Anzahl an Kapiteln herunter.",
        "auto_mode": "Ladet alle verfügbaren Kapitel vom Manga herunter.",
        
        # Erweiterte Funktionen
        "merge_after": "Erstellt, nach dem Download, PDFs aus den heruntergeladenen Kapiteln.",
        "chapters_per_pdf": "Anzahl der Kapitel die in eine PDF zusammengefasst werden sollen.",
        "merge_chapters": "Anzahl der Kapitel die in eine PDF zusammengefasst werden sollen.",
        "delete_originals": "Löscht die ursprünglichen Kapitel-PDFs nach dem Zusammenführen.",
        "only_new_manifest": "Fügt nur neu heruntergeladene Kapitel zusammen, ignoriert bereits vorhandene.",
        "delete_images": "Löscht die heruntergeladenen Bilder nach der PDF-Erstellung.",

    },
    
    "bulk_downloader": {
        # URL-Eingabe
        "url_entry": "Die URL eines Manga-Kapitels einfügen und auf 'Hinzufügen' klicken.",
                
        # Detail-Editor (gleiche wie Single-Downloader)
        "manual_mode": "Ladet eine bestimmte Anzahl an Kapiteln herunter.",
        "auto_mode": "Ladet alle verfügbaren Kapitel vom Manga herunter.",
        "merge_after": "Erstellt, nach dem Download, PDFs aus den heruntergeladenen Kapiteln.",
        "merge_chapters": "Anzahl der Kapitel die in eine PDF zusammengefasst werden sollen.",
        "delete_originals": "Löscht die ursprünglichen Kapitel-PDFs nach dem Zusammenführen.",
        "only_new_manifest": "Fügt nur neu heruntergeladene Kapitel zusammen, ignoriert bereits vorhandene.",
        "delete_images": "Löscht die heruntergeladenen Bilder nach der PDF-Erstellung.",
    
    },
    
    "pdf_merger": {
        # Export-Einstellungen
        "chapters_per_pdf": "Anzahl der Kapitel die in eine PDF zusammengefasst werden sollen.",
        "delete_originals": "Löscht die ursprünglichen PDF-Dateien nach dem Zusammenführen.",
    },
    
    "settings": {
        # Standard-Ordner
        "dir_entry": "Standard-Download-Ordner der für neue Downloads verwendet wird.",
        
        # Qualitäts-Einstellungen
        "jpeg_quality": "JPEG-Komprimierungsqualität. Höhere Werte = bessere Qualität aber größere Dateien.",
        "progressive_jpeg": "Progressive JPEGs sorgt für kleinere Dateien.",
        "grayscale": "Konvertiert alle Bilder zu Graustufen (Schwarz-Weiß). Spart Speicherplatz.",
        "max_width": "Maximale Bildbreite in Pixeln. Größere Bilder werden automatisch verkleinert.",
    },
}

IMPORTANT_CONTENT = {
    "important_tips": {
        "title": "Wichtige Hinweise",
        "description": "Ich habe (noch) keine Ahnung vom Programmieren mit Python, daher kann es zu Fehlern kommen. Wenn du einen Fehler findest, bitte melde es mir. Bis dahin gelten folgende Hinweise:",
        "steps": [
            "1. Du musst die Fragezeichen-Icons anklicken um die Hilfe und Anleitungen zu sehen",
            "2. Der Download startet ab dem Kapitel der URL die du eingibst und kann nicht die vorherigen Kapitel herunterladen",
            "3. Das Programm funktioniert aktuell nur mit MangaPark.net URLs",
            "4. Das scrollen mit dem Mausrad funktioniert im Bulk-Downloader-Panel nicht. Stattdessen den Scrollbalken verwenden",
            "5. Achte auf die Dateigrößen. Die PDFs sind trotz Qualitätseinschränkungen relativ groß, daher kann es zu Speicherplatz-Problemen kommen",
        ],
    },
}

# Detaillierte Hilfe-Texte für den Hilfe-Tab
HELP_CONTENT = {
    "single_downloader": {
        "title": "Single-Downloader",
        "description": "Lade einzelne Kapitel oder komplette Manga herunter",
        "steps": [
            "1. Gib die URL eines Manga-Kapitels in das URL-Feld ein",
            "2. Der Titel und Zielordner werden automatisch ausgefüllt, können aber manuell bearbeitet werden",
            "3. Wähle den Download-Modus (Manuell oder Automatisch)",
            "4. Konfiguriere erweiterte Optionen falls gewünscht",
            "5. Klick auf 'Download starten'",
            "6. Überwache den Fortschritt in den Statistiken"
        ],
        "tips": [
            "• Im manuellen Modus kannst du die Anzahl der heruntergeladenen Kapitel selbst bestimmen",
            "• Im automatischen Modus werden alle verfügbaren Kapitel des Mangas heruntergeladen",
            "• PDF-Zusammenführung ist optional und kann auch im PDF-Merger-Panel, nach dem Download, erfolgen",
            "• Downloads können jederzeit pausiert und fortgesetzt werden"
        ]
    },
    
    "bulk_downloader": {
        "title": "Bulk-Downloader",
        "description": "Lade mehrere Mangas nacheinander herunter",
        "steps": [
            "1. Füge die URL eines Manga-Kapitels über das URL-Feld hinzu und klick auf 'Hinzufügen'",
            "2. Konfiguriere jede URL im Editor",
            "3. Starte den Bulk-Download",
            "4. Überwache den Gesamtfortschritt in den Statistiken"
        ],
        "tips": [
            "• Du kannst auch während der Download läuft neue Manga-URLs hinzufügen",
            "• Du kannst die Manga-URLs, dessen Download noch nicht gestartet hat, immernoch im Editor bearbeiten",
            "• Du kannst URLs in der Liste neu anordnen",
            "• Fehlgeschlagene Downloads werden automatisch übersprungen"
        ]
    },
    
    "pdf_merger": {
        "title": "PDF-Merger",
        "description": "Füge mehrere PDF-Dateien zu größeren PDFs zusammen",
        "steps": [
            "1. Wähle PDF-Dateien über die Klick-Zone aus",
            "2. Der Zielordner wird automatisch erkannt, kann aber auch manuell ausgewählt werden",
            "3. Konfiguriere die Zusammenführungs-Einstellungen",
            "4. Starte das Zusammenführen",
        ],
        "tips": [
            "• Die Reihenfolge der Dateien bestimmt die Reihenfolge im Ergebnis",
            "• Die originalen PDF-Dateien können nach dem Zusammenführen automatisch gelöscht werden",
            "• Das Programm erstellt automatisch passende Dateinamen"
        ]
    },
    
    "settings": {
        "title": "Einstellungen",
        "description": "Konfiguriere die Standard-Einstellungen der Anwendung",
        "sections": [
            {
                "title": "Standard-Download-Ordner",
                "description": "Der Ordner in dem neue Downloads standardmäßig gespeichert werden"
            },
            {
                "title": "Qualitäts-Einstellungen",
                "description": "Einstellungen für die Bildqualität und -verarbeitung",
                "options": [
                    "JPEG-Qualität: Bestimmt die Komprimierung der Bilder",
                    "Progressive JPEG: Bessere Darstellung beim Laden und kleinere Dateien",
                    "Graustufen: Konvertiert Bilder zu Schwarz-Weiß",
                    "Maximale Breite: Begrenzt die Bildgröße, größere Bilder werden automatisch verkleinert"
                ]
            }
        ]
    }
}

# Allgemeine FAQ und Tipps
GENERAL_HELP = {
    "faq": [
        {
            "question": "Welche URLs werden unterstützt?",
            "answer": "Das Programm unterstützt aktuell nur MangaPark.net URLs. Gib eine Kapitel-URL ein, nicht die Hauptseite eines Mangas."
        },
        {
            "question": "Wie funktioniert der automatische Download-Modus?",
            "answer": "Das Programm erkennt automatisch alle verfügbaren Kapitel eines Mangas und lädt sie der Reihe nach herunter."
        },
        {
            "question": "Kann ich Downloads pausieren?",
            "answer": "Ja, du kannst Downloads jederzeit pausieren und später fortsetzen. Die bereits heruntergeladenen Kapitel bleiben erhalten."
        },
        {
            "question": "Was passiert mit den heruntergeladenen Bildern?",
            "answer": "Die Bilder werden zu PDFs zusammengefasst. Du kannst wählen, ob die Original-Bilder nach der PDF-Erstellung gelöscht werden sollen."
        },
        {
            "question": "Wie funktioniert der Bulk-Downloader?",
            "answer": "Der Bulk-Downloader ermöglicht es, mehrere Mangas nacheinander herunterzuladen. Jede URL kann individuelle Einstellungen haben."
        }
    ],
    
    "tips": [
        "• Lade die App 'ReadEra' aus dem App/PlayStore herunter um die PDF angenehmer zu lesen",
        "• PDF-Zusammenführung spart dir das lästige wechseln zwischen den Kapiteln",
        "• Graustufen-Modus reduziert die Dateigröße erheblich",
    ],
    
    "troubleshooting": [
        "• Bei Verbindungsproblemen: Pausiere den Download und versuche es später",
        "• Bei fehlenden Kapiteln: Überprüfe die URL und versuche es erneut",
        "• Bei fehlerhaften Dateinamen: Überprüfe die Kapitel-Nummer benennung in MangaPark.net",
        "• Bei Speicherplatz-Problemen: Verwende den Graustufen-Modus oder reduziere die JPEG-Qualität",
        "• Bei fehlerhaften Downloads: Starte das Programm/ den Download neu und öffne die PDFs während dem Download nicht",
        "• Bei langsamen Downloads: Das ist normal, da das Programm die Server nicht überlasten möchte"
    ]
}