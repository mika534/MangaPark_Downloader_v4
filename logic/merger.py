import os
import re
import shutil
from typing import Callable, List, Tuple, Optional
import json

from pypdf import PdfWriter

StatusCallback = Callable[[str], None]


def _is_already_merged(filename: str) -> bool:
    """Heuristic: filenames like 'Chapter_001-005 - Title.pdf' are considered merged outputs."""
    return bool(re.search(r"Chapter_\d{3}(?:_\d+)?-\d{3}(?:_\d+)?\s*-\s*.+\.pdf$", filename, re.IGNORECASE))


_single_re = re.compile(r"Chapter_(\d{3}(?:_\d+)?|\d+(?:\.\d+)?)", re.IGNORECASE)
_range_re = re.compile(r"Chapter_(\d{3}(?:_\d+)?|\d+(?:\.\d+)?)-(\d{3}(?:_\d+)?|\d+(?:\.\d+)?)", re.IGNORECASE)


def _token_to_float(tok: str) -> float:
    """Convert '012' -> 12.0, '012_5' -> 12.5, '12.5' -> 12.5."""
    tok = tok.replace("_", ".")
    try:
        return float(tok)
    except Exception:
        # Fallback: extract trailing number
        m = re.search(r"(\d+(?:\.\d+)?)", tok)
        return float(m.group(1)) if m else 0.0


def _parse_bounds_from_name(name: str) -> Optional[Tuple[float, float]]:
    """Return (start, end) chapter numbers from filename. For single chapters, start==end."""
    m = _range_re.search(name)
    if m:
        a, b = m.group(1), m.group(2)
        return _token_to_float(a), _token_to_float(b)
    m2 = _single_re.search(name)
    if m2:
        v = _token_to_float(m2.group(1))
        return v, v
    return None


def _format_bound(val: float) -> str:
    """Format float chapter to output token: 12 -> '012', 12.5 -> '012_5'."""
    if abs(val - round(val)) < 1e-9:
        return f"{int(round(val)):03d}"
    # Keep one decimal place (common for .5); adapt if needed
    frac = str(val).split(".")[1]
    return f"{int(val):03d}_{frac}"


def _find_and_sort_chapter_pdfs(folder_path: str, ignore_merged: bool = True) -> List[Tuple[float, str]]:
    """Find chapter PDFs (single or merged). Sort by start bound."""
    items: List[Tuple[float, str]] = []
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".pdf"):
            continue
        if ignore_merged and _is_already_merged(filename):
            continue
        bounds = _parse_bounds_from_name(filename)
        if bounds:
            start, _ = bounds
            items.append((start, os.path.join(folder_path, filename)))
    items.sort(key=lambda x: x[0])
    return items


def _load_manifest_list(folder_path: str, status: StatusCallback) -> Optional[List[str]]:
    """Try to read latest_manifest.txt and load the JSON manifest's chapter pdf_path list."""
    try:
        ptr = os.path.join(folder_path, "latest_manifest.txt")
        if not os.path.isfile(ptr):
            return None
        with open(ptr, "r", encoding="utf-8") as f:
            manifest_path = f.read().strip()
        if not manifest_path or not os.path.isfile(manifest_path):
            status("⚠️ Manifest-Pointer zeigt auf nicht vorhandene Datei.")
            return None
        with open(manifest_path, "r", encoding="utf-8") as mf:
            data = json.load(mf)
        chapters = data.get("chapters", [])
        pdfs = [c.get("pdf_path") for c in chapters if c.get("pdf_path") and os.path.isfile(c.get("pdf_path"))]
        if not pdfs:
            status("ℹ️ Manifest enthält keine vorhandenen PDFs.")
            return None
        return pdfs
    except Exception as e:
        status(f"⚠️ Konnte Manifest nicht lesen: {e}")
        return None


def merge_pdfs(
    folder_path: str,
    chapters_per_pdf: int,
    status: StatusCallback,
    selected_files: Optional[List[str]] = None,
    use_session_manifest: bool = False,
    ignore_merged: bool = True,
) -> None:
    """Merge chapter PDFs in `folder_path` into bundles of size `chapters_per_pdf`.

    - Accepts both single chapter files (Chapter_001 - Title.pdf) and already-merged bundles (Chapter_001-005 - Title.pdf)
    - Output naming based on min and max bounds across the chunk: 'Chapter_{min}-{max} - <Title>.pdf'
    - Originals are moved to '_originals' subfolder after each bundle is written
    - Progress and messages are reported via `status(str)`
    """
    try:
        if not os.path.isdir(folder_path):
            status("❌ Fehler: Ordner nicht gefunden!")
            return

        # Determine source list
        sorted_paths: List[str] = []
        if selected_files:
            # Use files provided by UI, keep order, accept both single and merged
            for path in selected_files:
                name = os.path.basename(path)
                if ignore_merged and _is_already_merged(name):
                    continue
                if name.lower().endswith(".pdf") and _parse_bounds_from_name(name):
                    sorted_paths.append(path)
            status(f"🔍 {len(sorted_paths)} ausgewählte Kapitel-PDFs übernommen.")
        elif use_session_manifest:
            manifest_list = _load_manifest_list(folder_path, status)
            if manifest_list:
                sorted_paths = manifest_list
                status(f"🔍 {len(sorted_paths)} Kapitel-PDFs aus Manifest.")
            else:
                # Wenn explizit nur neue (Manifest) gewünscht ist und Manifest leer/nicht vorhanden ist,
                # KEIN Fallback auf alle PDFs im Ordner – sofort beenden.
                status("ℹ️ Keine neuen Kapitel in dieser Session gefunden (Manifest leer oder fehlt).")
                return
        if not sorted_paths:
            status("🔍 Suche nach PDF-Dateien…")
            found = _find_and_sort_chapter_pdfs(folder_path, ignore_merged=ignore_merged)
            if not found:
                status("ℹ️ Keine passenden Kapitel-PDFs gefunden.")
                return
            sorted_paths = [p for _n, p in found]
        status(f"✅ {len(sorted_paths)} Kapitel-PDFs gefunden. Starte Zusammenführung...")

        originals = os.path.join(folder_path, "_originals")
        os.makedirs(originals, exist_ok=True)

        merged_count = 0
        for i in range(0, len(sorted_paths), chapters_per_pdf):
            chunk = sorted_paths[i : i + chapters_per_pdf]
            if not chunk:
                continue

            merger = PdfWriter()

            # Determine title from first file
            first_name = os.path.basename(chunk[0])
            title_match = re.search(r" - (.*)\.pdf", first_name, re.IGNORECASE)
            manga_title = title_match.group(1) if title_match else "Webtoon"

            # Compute min/max bounds across chunk
            mins: List[float] = []
            maxs: List[float] = []
            valid_chunk: List[str] = []
            for pdf in chunk:
                b = _parse_bounds_from_name(os.path.basename(pdf))
                if not b:
                    continue
                a, c = b
                mins.append(min(a, c))
                maxs.append(max(a, c))
                valid_chunk.append(pdf)
                merger.append(pdf)

            if not valid_chunk:
                merger.close()
                continue

            # If only one file in this chunk, keep it as is (avoid rename/overwrite and moving)
            if len(valid_chunk) == 1:
                merger.close()
                status(f"↪️ Einzel-PDF belassen: {os.path.basename(valid_chunk[0])}")
                continue

            start_fmt = _format_bound(min(mins))
            end_fmt = _format_bound(max(maxs))

            out_name = f"Chapter_{start_fmt}-{end_fmt} - {manga_title}.pdf"
            out_path = os.path.join(folder_path, out_name)

            status(f"⚙️ Verarbeite: {out_name}")

            with open(out_path, "wb") as f_out:
                merger.write(f_out)
            merger.close()
            merged_count += 1

            # Move originals
            for pdf in valid_chunk:
                shutil.move(pdf, os.path.join(originals, os.path.basename(pdf)))

        status(f"🎉 Fertig! {merged_count} PDF(s) erfolgreich erstellt.")

    except Exception as e:
        status(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}")