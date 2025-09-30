"""PDF utility functions for the MangaPark Downloader.

This module provides functionality for converting images to PDF files.
"""

import os
import time
from typing import List

from PIL import Image
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas


def images_to_pdf(
    image_paths: List[str],
    pdf_path: str,
    jpeg_quality: int = 75,
    images_per_page: int = 9,
    grayscale: bool = False,
    max_width: int = 1200,
    progressive: bool = True,
) -> None:
    """Konvertiert eine Liste von Bilddateien in eine einzelne PDF.

    Args:
        image_paths: Liste der Bildpfade
        pdf_path: Zielpfad der PDF-Datei
        jpeg_quality: JPEG-Qualität für temporäre Seiten (1-100)
        images_per_page: Anzahl Bilder pro PDF-Seite (werden vertikal kombiniert)
        grayscale: Bilder in Graustufen konvertieren
        max_width: Maximale Bildbreite (px) vor dem Zusammenfügen
        progressive: Progressive JPEGs schreiben
    """
    if not image_paths:
        return

    c = canvas.Canvas(pdf_path)

    for page_start in range(0, len(image_paths), images_per_page):
        page_end = min(page_start + images_per_page, len(image_paths))
        page_image_paths = image_paths[page_start:page_end]

        page_images = []
        for path in page_image_paths:
            img = None
            for attempt in range(3):
                try:
                    # Öffnen und in gewünschte Farbtiefe konvertieren
                    _img = Image.open(path)
                    if grayscale:
                        _img = _img.convert("L")
                    else:
                        # Transparenz (falls vorhanden) auf Weiß setzen und in RGB konvertieren
                        if _img.mode in ("RGBA", "LA"):
                            bg = Image.new("RGB", _img.size, (255, 255, 255))
                            if _img.mode == "RGBA":
                                bg.paste(_img, mask=_img.split()[3])
                            else:
                                bg.paste(_img.convert("RGBA"), mask=_img.convert("RGBA").split()[3])
                            _img = bg
                        else:
                            _img = _img.convert("RGB")

                    # Skalierung auf maximale Breite
                    try:
                        if max_width and _img.width > max_width:
                            _img.thumbnail((max_width, 10_000_000), Image.Resampling.LANCZOS)
                    except Exception:
                        # Fallback für ältere Pillow-Versionen
                        try:
                            if max_width and _img.width > max_width:
                                _img.thumbnail((max_width, 10_000_000), Image.LANCZOS)
                        except Exception:
                            pass

                    img = _img
                    break
                except Exception as e:
                    if "broken data stream" in str(e) and attempt < 2:
                        time.sleep(0.2)
                        continue
                    else:
                        img = None
                        break
            if img:
                page_images.append(img)

        if not page_images:
            continue

        max_w = max(img.width for img in page_images)
        total_height = sum(img.height for img in page_images)

        # Kombinierte Seite erzeugen (RGB, Weiß)
        mode = "L" if grayscale else "RGB"
        bg_color = 255 if grayscale else (255, 255, 255)
        combined_image = Image.new(mode, (max_w, total_height), bg_color)
        y_offset = 0
        for img in page_images:
            combined_image.paste(img, (0, y_offset))
            y_offset += img.height

        temp_filename = f"temp_page_{page_start}.jpg"
        save_kwargs = {
            "format": "JPEG",
            "quality": int(max(1, min(100, jpeg_quality))),
            "optimize": True,
            "progressive": bool(progressive),
        }
        try:
            combined_image.save(temp_filename, **save_kwargs)
        except Exception:
            # Fallback ohne optimize/progressive/subsampling
            combined_image.save(temp_filename, format="JPEG", quality=int(max(1, min(100, jpeg_quality))))

        c.setPageSize(portrait((max_w, total_height)))
        c.drawImage(temp_filename, 0, 0, width=max_w, height=total_height)
        c.showPage()

        try:
            os.remove(temp_filename)
        except Exception:
            pass

    c.save()