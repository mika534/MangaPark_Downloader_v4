import os
from pathlib import Path

# App-Informationen
APP_NAME = "MangaPark Downloader"
APP_VERSION = "4.3.6"
AUTHOR = "Mika534"


# Pfade
BASE_DIR = Path(__file__).parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"
LOG_DIR = BASE_DIR / "logs"


# Download-Einstellungen
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
MAX_CONCURRENT_DOWNLOADS = 5
CHUNK_SIZE = 8192  # 8KB chunks for downloads

# Merge-Einstellungen
DEFAULT_MERGE_CHAPTERS = 1

# MangaPark-spezifisch
MANGA_BASE_URL = "https://mangapark.net/manga/"
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Standardmäßige Einstellungen
DEFAULT_SETTINGS = {
    "download_dir": str(DOWNLOADS_DIR),
    "temp_dir": str(TEMP_DIR),
    "max_concurrent_downloads": MAX_CONCURRENT_DOWNLOADS,
    "timeout": DEFAULT_TIMEOUT,
    "max_retries": MAX_RETRIES,
    "theme": "dark",  # Kann "light" oder "dark" sein
    "language": "de",  # Standardsprache
}