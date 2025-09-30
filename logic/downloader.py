import contextlib
import math
import os
import re
import time
import json
from io import BytesIO
from datetime import datetime
from typing import Callable, Optional, Protocol, List

from PIL import Image
import playwright.sync_api
from playwright.sync_api import sync_playwright

from core.pdf_utils import images_to_pdf
from core.browser_manager import open_page as _open_page, KEEP_BROWSER_OPEN_FOR_DEBUG
from core.utils import load_settings

WAIT_AFTER_LOAD = float(os.environ.get("MPD_WAIT_AFTER_LOAD", 4))
DOWNLOAD_DELAY = float(os.environ.get("MPD_DOWNLOAD_DELAY", 0.2))
CHAPTER_DELAY = float(os.environ.get("MPD_CHAPTER_DELAY", 2.0))
MAX_CHAPTERS_LIMIT = int(os.environ.get("MPD_MAX_CHAPTERS_LIMIT", 200))
MAX_CHAPTER_FAILURES = int(os.environ.get("MPD_MAX_CHAPTER_FAILURES", 5))

# ---------------------------
# Types
# ---------------------------
UIUpdate = Callable[[str], None]
ProgressUpdate = Callable[[int], None]
StatsUpdate = Callable[[int, int, int, float, float, float], None]

# ---------------------------
# Controller (MODULE-LEVEL)
# ---------------------------
class DownloadController:
    def __init__(self):
        self.is_paused = False
        self.should_stop = False
        self.start_time: Optional[float] = None
        self.total_images = 0
        self.completed_chapters = 0
        self.estimated_time_per_chapter = 0.0
        self.pause_start_time = 0.0
        self.total_paused_duration = 0.0
        # Path to current session manifest (set by download_multiple_chapters)
        self.current_manifest_path: Optional[str] = None
        # Detected total number of chapters from page (auto mode)
        self.detected_total_chapters: int = 0
        # Sorted unique chapter numbers (floats) detected from the select (auto mode)
        self.chapter_values_sorted: list[float] = []
        # 1-based index of the current chapter within chapter_values_sorted for display (auto mode)
        self.display_index: int = 0

    def reset(self):
        self.is_paused = False
        self.should_stop = False
        self.start_time = None
        self.total_images = 0
        self.completed_chapters = 0
        self.estimated_time_per_chapter = 0.0
        self.pause_start_time = 0.0
        self.total_paused_duration = 0.0
        self.current_manifest_path = None
        self.detected_total_chapters = 0
        self.chapter_values_sorted = []
        self.display_index = 0


download_controller = DownloadController()

# ---------------------------
# Helpers
# ---------------------------

def extract_chapter_number_from_url(url: str) -> str:
    m = re.search(r"-ch-(\d+)", url)
    if m:
        return f"Chapter_{int(m.group(1)):03d}"
    m2 = re.search(r"(\d+)(?!.*\d)", url)
    if m2:
        return f"Chapter_{int(m2.group(1)):03d}"
    return "Chapter_000"


def extract_chapter_number(page, url: str) -> str:
    try:
        chapter_element = page.query_selector('span.opacity-80:has-text("Chapter")')
        if chapter_element:
            text_content = chapter_element.inner_text()
            match = re.search(r"Chapter\s+(\d+(\.\d+)?)", text_content, re.IGNORECASE)
            if match:
                chapter_num_str = match.group(1)
                if "." in chapter_num_str:
                    main_part, dec_part = chapter_num_str.split(".")
                    return f"Chapter_{int(main_part):03d}.{dec_part}"
                else:
                    return f"Chapter_{int(chapter_num_str):03d}"
    except Exception:
        pass
    return extract_chapter_number_from_url(url)


def clean_image_url(url: str) -> str:
    if not url:
        return url
    return url.split("?")[0].strip()


def log_error_to_file(error_msg: str, output_folder: str):
    try:
        os.makedirs(output_folder, exist_ok=True)
        log_path = os.path.join(output_folder, "error_log.txt")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {error_msg}\n")
    except Exception:
        pass


def format_time(seconds: float) -> str:
    seconds = max(0, seconds)
    if seconds < 3600:
        return f"{int(seconds//60):02d}:{int(seconds%60):02d}"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"




def find_next_chapter_url(page) -> Optional[str]:
    try:
        selectors = [
            'a.btn.btn-sm.btn-outline.btn-primary:has-text("Next Chapter")',
            'a.btn:has-text("Next Chapter")',
            'a.btn:has-text("Next")',
            'a[class*="btn"]:has-text("Next")',
            'a[href*="-ch-"]:has-text("Next")',
        ]
        for selector in selectors:
            try:
                next_btn = page.query_selector(selector)
                if next_btn:
                    href = next_btn.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            base_url = "/".join(page.url.split("/")[:3])
                            return base_url + href
                        elif href.startswith("http"):
                            return href
            except Exception:
                continue
        return None
    except Exception:
        return None


def detect_total_chapters_via_select(page) -> int:
    """Detect total chapters by analyzing <select><option> groups and extracting unique chapter numbers.
    Strategy:
    - Iterate all <select> elements
    - For each, collect options whose text or value matches chapter-like patterns
    - Extract chapter numbers, normalize (e.g., 'Chapter 12', '/...-chapter-12', '-ch-012')
    - Use the count of UNIQUE chapter numbers per select; choose the select with the highest unique count
    - Fallbacks: prefer selects with class names containing 'select' + 'primary' + 'bordered' if tie
    Returns 0 if not determinable.
    """
    try:
        import re as _re
        selects = page.query_selector_all("select") or []
        best_count = 0
        best_is_preferred = False
        best_values_sorted: list[float] = []
        for sel in selects:
            try:
                options = sel.query_selector_all("option") or []
                chapters: set = set()
                for opt in options:
                    try:
                        txt = (opt.inner_text() or "").strip()
                    except Exception:
                        txt = ""
                    try:
                        val = (opt.get_attribute("value") or "").strip()
                    except Exception:
                        val = ""
                    blob = f"{txt} {val}".lower()
                    # quick filter: must mention chapter-ish keywords
                    if ("chapter" not in blob) and ("kapitel" not in blob) and ("-ch-" not in blob):
                        continue
                    # extract number tokens from common patterns
                    num = None
                    for pat in (
                        r"chapter\s*([0-9]+(?:\.[0-9]+)?)",
                        r"kapitel\s*([0-9]+(?:\.[0-9]+)?)",
                        r"-ch-([0-9]+(?:\.[0-9]+)?)",
                        r"chapter-([0-9]+(?:\.[0-9]+)?)",
                    ):
                        m = _re.search(pat, blob)
                        if m:
                            num = m.group(1)
                            break
                    # fallback: trailing number
                    if num is None:
                        m2 = _re.search(r"(\d+(?:\.\d+)?)", blob)
                        if m2:
                            num = m2.group(1)
                    if num is None:
                        continue
                    try:
                        # normalize to float then to canonical token (e.g., 12 or 12.5)
                        f = float(num)
                        token = f"{f:.3f}".rstrip("0").rstrip(".")
                    except Exception:
                        token = num
                    chapters.add(token)
                uniq = len(chapters)
                if uniq <= 0:
                    continue
                # prefer selects that look like the example (primary/bordered) when tie
                cls = (sel.get_attribute("class") or "").lower()
                preferred = ("select" in cls and "primary" in cls and "bordered" in cls)
                if (uniq > best_count) or (uniq == best_count and preferred and not best_is_preferred):
                    best_count = uniq
                    best_is_preferred = preferred
                    # store sorted numeric values (ascending)
                    vals: list[float] = []
                    for t in chapters:
                        try:
                            vals.append(float(t))
                        except Exception:
                            pass
                    vals.sort()
                    best_values_sorted = vals
            except Exception:
                continue
        # sanity cap to avoid absurd values from unrelated selects
        if best_count > 0:
            # Store on controller for later display mapping
            try:
                download_controller.chapter_values_sorted = best_values_sorted
            except Exception:
                download_controller.chapter_values_sorted = []
            return int(best_count)
        return 0
    except Exception:
        return 0


def _download_single_chapter_internal(
    page,
    url: str,
    output_folder: str,
    manga_title: str,
    ui_update: UIUpdate,
    progress_update: Optional[ProgressUpdate] = None,
    delete_images_after_pdf: bool = False,
) -> bool:
    try:
        if download_controller.should_stop:
            return False

        page.goto(url, wait_until="domcontentloaded")
        ui_update(f"Warte {WAIT_AFTER_LOAD:.0f} Sek. bis Seite geladen hat…")
        waited = 0.0
        while waited < WAIT_AFTER_LOAD:
            if download_controller.should_stop:
                return False
            while download_controller.is_paused and not download_controller.should_stop:
                time.sleep(0.1)
            time.sleep(0.5)
            waited += 0.5

        chapter_name = extract_chapter_number(page, url)
        chapter_folder = os.path.join(output_folder, chapter_name)
        os.makedirs(chapter_folder, exist_ok=True)
        ui_update(f" Ordner: {chapter_name}")

        imgs = page.query_selector_all("img.w-full.h-full")
        if not imgs:
            imgs = page.query_selector_all("img")

        links: List[str] = []
        for img in imgs:
            src = img.get_attribute("src")
            if not src:
                for attr in ("data-src", "data-lazy-src", "data-original", "srcset"):
                    val = img.get_attribute(attr)
                    if val:
                        src = val
                        break
            if src:
                src = clean_image_url(src)
                if src.lower().startswith("http") and src not in links and (
                    any(src.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")) or "/media/" in src
                ):
                    links.append(src)

        if not links:
            error_msg = f"Keine Bilder in {chapter_name} gefunden! URL: {url}"
            ui_update(f" {error_msg}")
            log_error_to_file(error_msg, output_folder)
            if progress_update:
                try:
                    progress_update(0)
                except Exception:
                    pass
            return False

        ui_update(f" {len(links)} Bilder gefunden - Download startet…")
        image_paths: List[str] = []
        total = len(links)
        failed_images = 0

        # Progress-Start auf 10%
        if progress_update:
            try:
                progress_update(10)
            except Exception:
                pass

        # Einstellungen laden (mit Defaults)
        _settings = {}
        try:
            _settings = load_settings() or {}
        except Exception:
            _settings = {}
        JPEG_QUALITY = int(_settings.get("jpeg_quality", 75))
        JPEG_PROGRESSIVE = bool(_settings.get("jpeg_progressive", True))
        MAX_WIDTH = int(_settings.get("max_width", 1200))
        GRAYSCALE = bool(_settings.get("grayscale", False))

        for i, link in enumerate(links, start=1):
            if download_controller.should_stop:
                return False
            while download_controller.is_paused and not download_controller.should_stop:
                time.sleep(0.1)

            filename = os.path.join(chapter_folder, f"{i:03d}.jpg")
            success = False
            for attempt in range(2):
                try:
                    resp = page.request.get(link, headers={"Referer": page.url})
                    if resp.status == 200:
                        # Re-Encode mit Qualitäts-/Skalierungs-Settings
                        body = resp.body()
                        try:
                            im = Image.open(BytesIO(body))
                        except Exception:
                            # Fallback: direkt speichern, wenn Pillow nicht öffnen kann
                            with open(filename, "wb") as f:
                                f.write(body)
                            image_paths.append(filename)
                            download_controller.total_images += 1
                            ui_update(f" {i}/{total}: {os.path.basename(filename)}")
                            success = True
                            break

                        # Transparenz auf Weiß und Farbraum
                        if GRAYSCALE:
                            im = im.convert("L")
                        else:
                            if im.mode in ("RGBA", "LA"):
                                bg = Image.new("RGB", im.size, (255, 255, 255))
                                if im.mode == "RGBA":
                                    bg.paste(im, mask=im.split()[3])
                                else:
                                    tmp = im.convert("RGBA")
                                    bg.paste(tmp, mask=tmp.split()[3])
                                im = bg
                            else:
                                im = im.convert("RGB")

                        # Skalierung auf MAX_WIDTH
                        try:
                            if MAX_WIDTH and im.width > MAX_WIDTH:
                                im.thumbnail((MAX_WIDTH, 10_000_000), Image.Resampling.LANCZOS)
                        except Exception:
                            try:
                                if MAX_WIDTH and im.width > MAX_WIDTH:
                                    im.thumbnail((MAX_WIDTH, 10_000_000), Image.LANCZOS)
                            except Exception:
                                pass

                        save_kwargs = {
                            "format": "JPEG",
                            "quality": int(max(1, min(100, JPEG_QUALITY))),
                            "optimize": True,
                            "progressive": bool(JPEG_PROGRESSIVE),
                        }

                        # Schreiben als JPEG
                        try:
                            im.save(filename, **save_kwargs)
                        except Exception:
                            im.save(filename, format="JPEG", quality=int(max(1, min(100, JPEG_QUALITY))))

                        image_paths.append(filename)
                        download_controller.total_images += 1
                        ui_update(f" {i}/{total}: {os.path.basename(filename)}")
                        success = True
                        break
                    else:
                        ui_update(f" HTTP {resp.status} bei Bild {i} (Versuch {attempt+1})")
                except Exception as e:
                    ui_update(f" Fehler bei Bild {i} (Versuch {attempt+1}): {str(e)[:50]}")
                time.sleep(0.5)

            if not success:
                failed_images += 1
                error_msg = f"Bild {i} in {chapter_name} konnte nicht heruntergeladen werden: {link}"
                log_error_to_file(error_msg, output_folder)
                ui_update(f" Bild {i} übersprungen")

            # linearer Fortschritt zwischen 10% und 90%
            if progress_update and total > 0:
                pct = 10 + int(80 * (i / total))
                pct = min(90, max(10, pct))
                try:
                    progress_update(pct)
                except Exception:
                    pass

            time.sleep(DOWNLOAD_DELAY)

        if not image_paths:
            error_msg = f"Alle Bilder in {chapter_name} fehlgeschlagen! URL: {url}"
            ui_update(f" {error_msg}")
            log_error_to_file(error_msg, output_folder)
            if progress_update:
                try:
                    progress_update(0)
                except Exception:
                    pass
            return False

        if failed_images > 0:
            ui_update(f" {failed_images} von {total} Bildern fehlgeschlagen")

        # Dynamische Bilder/Seite bestimmen (Sicherheitslimit für PDF-Höhen)
        max_height = 0
        for path in image_paths:
            try:
                with Image.open(path) as img:
                    if img.height > max_height:
                        max_height = img.height
            except Exception:
                pass

        SAFE_PAGE_HEIGHT_LIMIT = 20000
        dynamic_images_per_page = 10
        if max_height > 0:
            if max_height > 20000:
                dynamic_images_per_page = 1
            elif max_height > 10000:
                calculated_safe_amount = SAFE_PAGE_HEIGHT_LIMIT // max_height
                dynamic_images_per_page = max(1, min(4, calculated_safe_amount))
            elif max_height > 5000:
                calculated_safe_amount = SAFE_PAGE_HEIGHT_LIMIT // max_height
                dynamic_images_per_page = max(1, min(8, calculated_safe_amount))
            else:
                calculated_safe_amount = SAFE_PAGE_HEIGHT_LIMIT // max_height
                dynamic_images_per_page = max(1, min(10, calculated_safe_amount))

        ui_update(
            f" PDF-Anpassung: {dynamic_images_per_page} Bilder/Seite (höchstes Bild: {max_height}px)"
        )

        # PDF-Erstellung (ca. 10%)
        if progress_update:
            try:
                progress_update(92)
            except Exception:
                pass

        pdf_name = f"{chapter_name} - {manga_title}.pdf"
        pdf_path = os.path.join(output_folder, pdf_name)
        ui_update(" Erstelle PDF…")

        images_to_pdf(
            image_paths,
            pdf_path,
            jpeg_quality=JPEG_QUALITY,
            images_per_page=dynamic_images_per_page,
            grayscale=GRAYSCALE,
            max_width=MAX_WIDTH,
            progressive=JPEG_PROGRESSIVE,
        )

        # Append to session manifest (if available)
        try:
            if download_controller.current_manifest_path:
                manifest_path = download_controller.current_manifest_path
                # Load existing manifest JSON
                data = {}
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r", encoding="utf-8") as mf:
                        try:
                            data = json.load(mf) or {}
                        except Exception:
                            data = {}
                if "chapters" not in data:
                    data["chapters"] = []
                data["chapters"].append(
                    {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "chapter_name": chapter_name,
                        "pdf_path": pdf_path,
                    }
                )
                # Update summary info (best effort)
                data.setdefault("output_folder", output_folder)
                data.setdefault("manga_title", manga_title)
                with open(manifest_path, "w", encoding="utf-8") as mf:
                    json.dump(data, mf, ensure_ascii=False, indent=2)
        except Exception:
            # Non-fatal: manifest failures should not break the download
            pass

        if progress_update:
            try:
                progress_update(100)
            except Exception:
                pass

        ui_update(f" {chapter_name} fertig! ({len(image_paths)} Bilder)")

        # Option: Bild-Ordner nach erfolgreicher PDF-Erstellung löschen
        if delete_images_after_pdf:
            try:
                import shutil as _shutil
                _shutil.rmtree(chapter_folder, ignore_errors=True)
                ui_update("🧹 Kapitel-Bilder gelöscht (nach PDF)")
            except Exception as _e:
                log_error_to_file(f"Konnte Kapitel-Ordner nicht löschen: {chapter_folder} -> {_e}", output_folder)

        download_controller.completed_chapters += 1
        if download_controller.completed_chapters >= 1 and download_controller.start_time:
            elapsed_running_time = (time.time() - download_controller.start_time) - download_controller.total_paused_duration
            download_controller.estimated_time_per_chapter = (
                elapsed_running_time / max(1, download_controller.completed_chapters)
            )

        return True

    except Exception as e:
        error_msg = f"Chapter Download Fehler für {url}: {str(e)}"
        ui_update(f" Chapter-Fehler: {str(e)[:50]}")
        log_error_to_file(error_msg, output_folder)
        if progress_update:
            try:
                progress_update(0)
            except Exception:
                pass
        return False


# ---------------------------
# Core download logic
# ---------------------------



# Public API

def download_single_chapter(url: str, output_folder: str, manga_title: str, ui_update: UIUpdate, delete_images_after_pdf: bool = False) -> bool:
    """Launch a browser, download one chapter, close browser. GUI-agnostisch."""
    download_controller.reset()
    download_controller.start_time = time.time()

    p, browser_like, page = _open_page(ui_update)
    if not page:
        return False
    try:
        return _download_single_chapter_internal(
            page,
            url,
            output_folder,
            manga_title,
            ui_update,
            None,
            delete_images_after_pdf,
        )
    finally:
        if not KEEP_BROWSER_OPEN_FOR_DEBUG and browser_like:
            try:
                browser_like.close()
                ui_update("🔒 Browser geschlossen")
            except Exception:
                pass
        if p:
            try:
                p.stop()
            except Exception:
                pass


def download_multiple_chapters(
    start_url: str,
    output_folder: str,
    manga_title: str,
    max_chapters: int,
    auto_detect: bool,
    ui_update: UIUpdate,
    progress_update: Optional[ProgressUpdate] = None,
    stats_update: Optional[StatsUpdate] = None,
    delete_images_after_pdf: bool = False,
    keep_manifest: bool = False,
) -> None:
    download_controller.reset()
    download_controller.start_time = time.time()

    downloaded_chapters = 0
    current_url = start_url
    failed_chapters = 0
    total_chapters_display = max_chapters if not auto_detect else "Auto"

    os.makedirs(output_folder, exist_ok=True)

    # Initialize session manifest
    try:
        manifests_dir = os.path.join(output_folder, "_manifests")
        os.makedirs(manifests_dir, exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        manifest_path = os.path.join(manifests_dir, f"session-{session_ts}.json")
        manifest_data = {
            "session_start": datetime.now().isoformat(timespec="seconds"),
            "manga_title": manga_title,
            "output_folder": output_folder,
            "start_url": start_url,
            "auto_detect": bool(auto_detect),
            "max_chapters": int(max_chapters),
            "chapters": [],
        }
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, ensure_ascii=False, indent=2)
        # Set current manifest on controller and write a pointer file for easy discovery
        download_controller.current_manifest_path = manifest_path
        with open(os.path.join(output_folder, "latest_manifest.txt"), "w", encoding="utf-8") as lf:
            lf.write(manifest_path)
        ui_update(" ✍️ Manifest für diese Session erstellt")
    except Exception:
        # Proceed without manifest if something goes wrong
        download_controller.current_manifest_path = None

    p, browser_like, page = _open_page(ui_update)
    if not page:
        return

    # Pre-load start page to detect total chapters when in auto mode
    if auto_detect:
        try:
            page.goto(start_url, wait_until="domcontentloaded")
            ui_update(f"Warte {WAIT_AFTER_LOAD:.0f} Sek. für Kapitelerkennung…")
            waited = 0.0
            while waited < WAIT_AFTER_LOAD and not download_controller.should_stop:
                while download_controller.is_paused and not download_controller.should_stop:
                    time.sleep(0.1)
                time.sleep(0.2)
                waited += 0.2
            detected = detect_total_chapters_via_select(page)
            download_controller.detected_total_chapters = int(detected or 0)
            if download_controller.detected_total_chapters > 0:
                total_chapters_display = download_controller.detected_total_chapters
                ui_update(f" Kapitel gesamt erkannt: {download_controller.detected_total_chapters}")
            else:
                ui_update(" Kapitelanzahl nicht automatisch erkennbar")
        except Exception:
            ui_update(" Kapitelanzahl-Erkennung übersprungen")

    # Try to compute display index (current starting chapter position) from page
    try:
        current_ch_name = extract_chapter_number(page, start_url)  # e.g., 'Chapter_020' or 'Chapter_020.5'
        # parse float from name
        import re as _re
        mnum = _re.search(r"(\d+(?:[\._]\d+)?)", current_ch_name)
        cur_val = None
        if mnum:
            token = mnum.group(1).replace("_", ".")
            try:
                cur_val = float(token)
            except Exception:
                cur_val = None
        if cur_val is not None and download_controller.chapter_values_sorted:
            # find exact match index; if not found, approximate by nearest
            vals = download_controller.chapter_values_sorted
            idx = None
            for i, v in enumerate(vals):
                if abs(v - cur_val) < 1e-6:
                    idx = i + 1  # 1-based
                    break
            if idx is None:
                # nearest
                nearest_i = min(range(len(vals)), key=lambda i: abs(vals[i] - cur_val))
                idx = nearest_i + 1
            download_controller.display_index = idx
    except Exception:
        pass

    ui_update(" Multi-Chapter Download gestartet")
    ui_update(
        f" Modus: {'Automatisch' if auto_detect else f'Manuell ({max_chapters} Chapters)'}"
    )

    try:
        while True:
            if download_controller.should_stop:
                ui_update(" Download abgebrochen")
                break

            while download_controller.is_paused and not download_controller.should_stop:
                time.sleep(0.1)

            if not auto_detect and downloaded_chapters >= max_chapters:
                ui_update(f" Ziel erreicht: {max_chapters} Chapters")
                break

            if downloaded_chapters >= MAX_CHAPTERS_LIMIT:
                ui_update(f" Sicherheits-Limit erreicht: {MAX_CHAPTERS_LIMIT}")
                break

            if failed_chapters >= MAX_CHAPTER_FAILURES:
                ui_update(f" Zu viele Fehler: {failed_chapters}")
                break

            try:
                current_chapter = downloaded_chapters + 1
                ui_update(f" Chapter {current_chapter}/{total_chapters_display}")
                ui_update(f" {current_url}")

                # Overall progress update before starting this chapter
                if progress_update:
                    try:
                        if not auto_detect and max_chapters > 0:
                            progress = int((downloaded_chapters / max(1, max_chapters)) * 100)
                            progress_update(progress)
                        elif auto_detect and download_controller.detected_total_chapters > 0:
                            progress = int((downloaded_chapters / max(1, download_controller.detected_total_chapters)) * 100)
                            progress_update(progress)
                    except Exception:
                        pass

                avg_images = download_controller.total_images / max(
                    1, download_controller.completed_chapters
                )
                elapsed_time = (
                    (time.time() - download_controller.start_time)
                    - download_controller.total_paused_duration
                    if download_controller.start_time
                    else 0
                )
                chapters_per_min = (
                    (download_controller.completed_chapters / max(1e-9, elapsed_time)) * 60
                    if elapsed_time > 0
                    else 0
                )

                remaining_chapters = (
                    max_chapters - downloaded_chapters if not auto_detect else (
                        max(0, download_controller.detected_total_chapters - downloaded_chapters)
                        if download_controller.detected_total_chapters > 0 else 0
                    )
                )
                eta_seconds = (
                    remaining_chapters * download_controller.estimated_time_per_chapter
                    if download_controller.estimated_time_per_chapter > 0
                    else (
                        remaining_chapters / max(1e-9, chapters_per_min) * 60
                        if chapters_per_min > 0 and remaining_chapters > 0
                        else 0
                    )
                )

                if stats_update:
                    # Compute a display-completed value: in auto mode prefer display_index (current position)
                    completed_display = downloaded_chapters
                    if auto_detect and download_controller.display_index > 0:
                        completed_display = download_controller.display_index
                    stats_update(
                        completed_display,
                        (max_chapters if not auto_detect else download_controller.detected_total_chapters),
                        download_controller.total_images,
                        float(avg_images),
                        float(chapters_per_min),
                        float(eta_seconds),
                    )

                # Build progress adapter to map per-chapter progress into overall when auto total is known
                def _progress_adapter(pct: int) -> None:
                    if not progress_update:
                        return
                    try:
                        if auto_detect and download_controller.detected_total_chapters > 0:
                            base = (downloaded_chapters / max(1, download_controller.detected_total_chapters)) * 100.0
                            next_base = ((downloaded_chapters + 1) / max(1, download_controller.detected_total_chapters)) * 100.0
                            mapped = int(base + (max(0, min(100, pct)) / 100.0) * (next_base - base))
                            progress_update(mapped)
                        else:
                            progress_update(int(pct))
                    except Exception:
                        pass

                chapter_success = _download_single_chapter_internal(
                    page,
                    current_url,
                    output_folder,
                    manga_title,
                    ui_update,
                    (_progress_adapter if progress_update else None),
                    delete_images_after_pdf,
                )

                if chapter_success:
                    downloaded_chapters += 1
                    failed_chapters = 0
                    # advance display index if available
                    if auto_detect and download_controller.display_index > 0:
                        download_controller.display_index = min(
                            download_controller.display_index + 1,
                            max(1, download_controller.detected_total_chapters)
                        )
                    # advance to next chapter on success
                    next_url = find_next_chapter_url(page)
                    if next_url:
                        current_url = next_url
                        ui_update(" Wechsle zum nächsten Chapter…")
                        time.sleep(CHAPTER_DELAY)
                    else:
                        ui_update(" Kein weiteres Chapter gefunden – beende.")
                        break
                else:
                    failed_chapters += 1
                    ui_update(
                        f" Chapter {current_chapter} fehlgeschlagen ({failed_chapters}/{MAX_CHAPTER_FAILURES})"
                    )

                    if failed_chapters < MAX_CHAPTER_FAILURES:
                        next_url = find_next_chapter_url(page)
                        if next_url:
                            current_url = next_url
                            ui_update(" Überspringe zu nächstem Chapter…")
                        else:
                            break
            except Exception as e:
                error_msg = f"Unerwarteter Fehler bei Chapter {downloaded_chapters + 1}: {str(e)}"
                ui_update(f" {error_msg[:80]}")
                log_error_to_file(error_msg, output_folder)
                failed_chapters += 1
                continue

        final_elapsed_time = (
            (time.time() - download_controller.start_time)
            - download_controller.total_paused_duration
            if download_controller.start_time
            else 0
        )
        # Emit a final stats update to ensure UI shows full completion (e.g., 2/2 instead of 1/2)
        try:
            if stats_update:
                avg_images = download_controller.total_images / max(1, download_controller.completed_chapters)
                elapsed_time = final_elapsed_time
                chapters_per_min = (
                    (download_controller.completed_chapters / max(1e-9, elapsed_time)) * 60
                    if elapsed_time > 0
                    else 0
                )
                completed_display = downloaded_chapters
                total_display = (max_chapters if not auto_detect else download_controller.detected_total_chapters)
                stats_update(
                    int(completed_display),
                    int(total_display) if isinstance(total_display, int) else 0,
                    int(download_controller.total_images),
                    float(avg_images),
                    float(chapters_per_min),
                    0.0,
                )
        except Exception:
            pass
        ui_update("")
        ui_update("-" * 60)
        ui_update(" DOWNLOAD ABGESCHLOSSEN")
        ui_update(f" Erfolgreich: {downloaded_chapters} Chapters")
        ui_update(f" Bilder gesamt: {download_controller.total_images}")
        ui_update(f" Gesamtzeit: {format_time(final_elapsed_time)}")
        ui_update(f" Fehlgeschlagen: {failed_chapters} Chapters")
        ui_update(f" Zielordner: {output_folder}")
        if os.path.exists(os.path.join(output_folder, "error_log.txt")):
            ui_update(" Fehler-Log: error_log.txt erstellt")
        # Clean up manifest artifacts after successful download (unless explicitly kept for merging)
        if not keep_manifest:
            try:
                manifest_pointer = os.path.join(output_folder, "latest_manifest.txt")
                if os.path.exists(manifest_pointer):
                    with contextlib.suppress(Exception):
                        os.remove(manifest_pointer)
                manifests_dir = os.path.join(output_folder, "_manifests")
                if os.path.isdir(manifests_dir):
                    import shutil as _shutil
                    with contextlib.suppress(Exception):
                        _shutil.rmtree(manifests_dir)
            except Exception:
                pass
        ui_update("-" * 60)

    finally:
        if not KEEP_BROWSER_OPEN_FOR_DEBUG and browser_like:
            try:
                browser_like.close()
                ui_update("🔒 Browser geschlossen")
            except Exception:
                pass
        if p:
            try:
                p.stop()
            except Exception:
                pass