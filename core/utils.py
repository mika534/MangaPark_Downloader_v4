import os
import re
import json
import logging
import hashlib
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

from .config import LOG_DIR, TEMP_DIR

def setup_logger(name: str) -> logging.Logger:
    """Konfiguriert einen Logger mit Datei- und Konsolenausgabe."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Format für die Logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Log-Datei
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Konsole
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Datei-Operationen
def ensure_directory(path: Union[str, Path]) -> Path:
    """Stellt sicher, dass ein Verzeichnis existiert und gibt den Path zurück."""
    path = Path(path) if isinstance(path, str) else path
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_valid_filename(name: str) -> str:
    """Konvertiert einen String in einen gültigen Dateinamen."""
    s = str(name).strip().replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    return s

def get_file_hash(file_path: Union[str, Path], block_size: int = 65536) -> str:
    """Berechnet den SHA-256 Hash einer Datei."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()

# URL-Helper
def is_valid_mangapark_url(url: str) -> bool:
    """Überprüft, ob die URL auf MangaPark verweist."""
    parsed = urllib.parse.urlparse(url)
    return bool(parsed.netloc and "mangapark.net" in parsed.netloc and "/manga/" in parsed.path)

def extract_manga_id(url: str) -> str:
    """Extrahiert die Manga-ID aus einer MangaPark-URL."""
    match = re.search(r'mangapark\.net/manga/([^/]+)', url)
    return match.group(1) if match else ""

# Einstellungen
def load_settings() -> Dict[str, Any]:
    """Lädt die Einstellungen aus der settings.json."""
    settings_file = Path(__file__).parent / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_settings(settings: Dict[str, Any]) -> None:
    """Speichert die Einstellungen in der settings.json."""
    settings_file = Path(__file__).parent / "settings.json"
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False, sort_keys=True)

# Fortschrittsanzeige
class ProgressTracker:
    """Hilfsklasse zum Verfolgen des Fortschritts von Downloads."""
    
    def __init__(self, total: int):
        self.total = total
        self.downloaded = 0
        self.start_time = datetime.now()
        
    def update(self, chunk_size: int) -> None:
        """Aktualisiert den Fortschritt."""
        self.downloaded += chunk_size
        
    def get_progress(self) -> float:
        """Gibt den Fortschritt als Wert zwischen 0 und 1 zurück."""
        return min(1.0, self.downloaded / self.total) if self.total > 0 else 0
    
    def get_speed(self) -> float:
        """Gibt die Download-Geschwindigkeit in Bytes pro Sekunde zurück."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return self.downloaded / elapsed if elapsed > 0 else 0
    
    def get_eta(self) -> float:
        """Gibt die voraussichtliche Restzeit in Sekunden zurück."""
        speed = self.get_speed()
        if speed <= 0:
            return 0
        remaining = self.total - self.downloaded
        return remaining / speed