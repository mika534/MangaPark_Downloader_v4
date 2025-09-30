"""
UI und Logik für den Bulk-Downloader
"""
from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict, Any, List
from .components import (
    create_button,
    create_flat_button,
    create_progress_bar,
    create_detail_editor,
    create_scrollbar,
    extract_title_from_url,
    suggest_output_folder,
)
from .theme import (
    BG_COLOR,
    ENTRY_BG,
    ENTRY_FG,
    LABEL_FG,
    TABLE_ROW_HEIGHT,
    DOWNLOAD_BORDER_COLOR,
)
from core.utils import load_settings

# Guarded import for download logic
IMPORT_ERROR_DOWNLOADER: Optional[Exception] = None
try:
    from logic.downloader import download_multiple_chapters, download_controller
except Exception as e:  # pragma: no cover
    download_multiple_chapters = None  # type: ignore
    download_controller = None  # type: ignore
    IMPORT_ERROR_DOWNLOADER = e

# Guarded import for PDF merger
IMPORT_ERROR_MERGER: Optional[Exception] = None
try:
    from logic.merger import merge_pdfs
except Exception as e:  # pragma: no cover
    merge_pdfs = None  # type: ignore
    IMPORT_ERROR_MERGER = e

class BulkDownloaderPanel:
    """Panel für den Bulk-Download"""

    def __init__(self, parent: tk.Widget, context: Optional[object] = None):
        """Initialisiert das Panel mit den geforderten Bereichen und Verhalten."""
        self.parent = parent
        self.context = context
        self.state = "idle"  # idle | running | done
        self.bulk_items: List[Dict[str, Any]] = []
        self._current_editor_index: Optional[int] = None
        self._paused = False
        self._is_populating_editor: bool = False
        self._flags = {"running": False, "stop": False, "skip": False}
        # flag to allow opening the editor on explicit user click while running
        self._editor_user_select = False
        # timestamp of the last mouse click in the tree (to detect user-initiated selection)
        self._last_tree_click_ts = 0.0
        # pinned editor index while running (keeps selection/editor on user-chosen row)
        self._editor_pinned_index: Optional[int] = None
        # current manga title for timer display
        self._current_manga_title: str = ""

        # Resolve standard download directory from settings
        settings = load_settings() or {}
        default_dir = settings.get("standard_dir") or os.path.expanduser("~")
        if self.context and hasattr(self.context, "standard_dir"):
            default_dir = getattr(self.context, "standard_dir", default_dir)
        self.standard_dir = default_dir
        if self.context and hasattr(self.context, "register"):
            self.context.register(self._on_standard_dir_changed)

        # Root
        self.frame = tk.Frame(parent, bg=BG_COLOR)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)

        # Scrollbarer Canvas + Content-Container
        self._canvas = tk.Canvas(self.frame, bg=BG_COLOR, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        # Scrollbar setup
        self._vbar = create_scrollbar(self.frame, orient="vertical", command=self._canvas.yview)
        self._vbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._vbar.set)
        # Content frame setup
        self.content = tk.Frame(self._canvas, bg=BG_COLOR)
        self._content_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.grid_columnconfigure(0, weight=1)

        # Scroll region and canvas configuration
        def _on_content_config(_evt=None):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        
        def _on_canvas_config(event):
            self._canvas.itemconfigure(self._content_window, width=event.width)
        
        self.content.bind("<Configure>", _on_content_config)
        self._canvas.bind("<Configure>", _on_canvas_config)

        # Y-scroll wrapper for fixed thumb height
        def _yset(first, last):
            f, l = float(first), float(last)
            sb_h = max(1, self._vbar.winfo_height())
            desired_px = 100
            desired_frac = min(1.0, max(0.02, desired_px / float(sb_h)))
            nf = max(0.0, min(1.0 - desired_frac, f))
            nl = nf + desired_frac
            self._vbar.set(nf, nl)
        
        self._canvas.configure(yscrollcommand=_yset)
        self._canvas.yview_moveto(0.0)
        # Scroll-Funktionalität entfernt: nur UI und Thumb-Optik bleiben erhalten

        # URL input section
        url_row = tk.Frame(self.content, bg=BG_COLOR)
        url_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        url_row.grid_columnconfigure(1, weight=1)
        
        tk.Label(url_row, text=" Chapter URL:", bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 11, "bold")).grid(row=0, column=0, padx=(0, 8))
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG, relief="flat", bd=5)
        self.url_entry.grid(row=0, column=1, sticky="ew")
        
        add_btn = create_flat_button(url_row, " Hinzufügen", command=self._add_url)
        add_btn.grid(row=0, column=2, padx=(8, 0))

        # 2) URL-Tabelle + Tabellen-Aktionen
        table_outer = tk.Frame(self.content, bg=BG_COLOR)
        table_outer.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 3)) # Abstand nach oben und unten
        # Do not expand this row; height is controlled explicitly
        self.frame.grid_rowconfigure(1, weight=0)
        self.table_wrap = tk.Frame(table_outer, bg=BG_COLOR, height=65)
        self.table_wrap.grid(row=0, column=0, sticky="ew")
        self.table_wrap.grid_propagate(False)
        self.table_wrap.grid_columnconfigure(0, weight=1)

        # URL-Tabelle Spalten
        columns = ("#", "Titel", "URL", "Ordner", "Modus", "Status", "%")
        self.tree = ttk.Treeview(self.table_wrap, columns=columns, show="headings", height=1, style="MPD.Treeview")
        column_defs = {
            "#": {"text": "#", "width": 30, "minwidth": 30, "anchor": "center", "stretch": False},
            "Titel": {"text": "Titel", "width": 120, "minwidth": 60, "anchor": "w", "stretch": True},
            "URL": {"text": "URL", "width": 180, "minwidth": 50, "anchor": "w", "stretch": True},
            "Ordner": {"text": "Ordner", "width": 180, "minwidth": 50, "anchor": "w", "stretch": True},
            "Modus": {"text": "Modus", "width": 100, "minwidth": 60, "anchor": "center", "stretch": True},
            "Status": {"text": "Status", "width": 100, "minwidth": 60, "anchor": "center", "stretch": True},
            "%": {"text": "%", "width": 50, "minwidth": 30, "anchor": "e", "stretch": False},
        }
        for col in columns:
            conf = column_defs[col]
            self.tree.heading(col, text=conf["text"], anchor=conf["anchor"])
            self.tree.column(
                col,
                width=conf["width"],
                minwidth=conf["minwidth"],
                anchor=conf["anchor"],
                stretch=conf["stretch"],
            )
        self.tree.grid(row=0, column=0, sticky="nsew")
        table_outer.grid_columnconfigure(0, weight=1)
        self.tree.configure(show="headings")
        self.table_wrap.bind("<Configure>", self._on_table_wrap_configure)
        self._resize_columns()
        # Scroll-Bindings entfernt

        # Table actions
        actions = tk.Frame(table_outer, bg=BG_COLOR)
        actions.grid(row=1, column=0, sticky="w", pady=(5, 5))
        
        create_button(actions, " Entfernen", variant="small-alert", command=self._remove_selected).grid(row=0, column=0, padx=(0, 4))
        create_button(actions, " ▲ Nach oben", variant="small", command=self._move_up).grid(row=0, column=1, padx=(0, 4))
        create_button(actions, " ▼ Nach unten", variant="small", command=self._move_down).grid(row=0, column=2, padx=(0, 4))
        create_button(actions, " Liste leeren", variant="small", command=self._clear_list).grid(row=0, column=3, padx=(0, 4))
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select_row)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")

        # Detail editor section
        self.editor_outer = tk.Frame(self.content, bg=BG_COLOR)
        self.editor_outer.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.editor_outer.grid_columnconfigure(0, weight=1)
        
        self.editor = create_detail_editor(self.editor_outer, standard_dir=self.standard_dir, browse_command=lambda: filedialog.askdirectory(), url_entry=None)
        self.editor["frame"].grid(row=0, column=0, sticky="ew")
        self.editor_outer.grid_remove()  # hidden by default
        self._bind_editor_change_events()

        # Progress and stats section
        self.run_border = tk.Frame(self.content, bg=BG_COLOR, highlightbackground=DOWNLOAD_BORDER_COLOR, highlightthickness=1, bd=0)
        self.run_border.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.run_border.grid_columnconfigure(0, weight=1)
        
        self.run_outer = tk.Frame(self.run_border, bg=BG_COLOR)
        self.run_outer.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.run_outer.grid_columnconfigure(0, weight=1)
        
        run_inner = tk.Frame(self.run_outer, bg=BG_COLOR)
        run_inner.grid(row=0, column=0, sticky="ew")
        run_inner.grid_columnconfigure(0, weight=1)

        # Overall progress section
        self.timer_var = tk.StringVar(value="Gesamte Laufzeit: 00:00")
        tk.Label(run_inner, textvariable=self.timer_var, bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 14, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        
        self.overall_stat_var = tk.StringVar(value="Manga 0/0 heruntergeladen")
        tk.Label(run_inner, textvariable=self.overall_stat_var, bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 9)).grid(row=1, column=0, sticky="ew")
        
        self.progress = create_progress_bar(run_inner, mode="determinate")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(4, 4))
        
        self.status_var = tk.StringVar(value=" Bereit…")


        # Per-URL progress section
        self.url_inner = tk.Frame(run_inner, bg=BG_COLOR)
        self.url_inner.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.url_inner.grid_columnconfigure(0, weight=1)
        
        self.url_timer_var = tk.StringVar(value="Laufzeit: 00:00")
        tk.Label(self.url_inner, textvariable=self.url_timer_var, bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 12, "bold"), anchor="center").grid(row=0, column=0, sticky="ew", pady=(5, 4))
        
        self.url_progress = create_progress_bar(self.url_inner, mode="determinate")
        self.url_progress.grid(row=1, column=0, sticky="ew")
        
        tk.Label(self.url_inner, textvariable=self.status_var, bg=BG_COLOR, fg=LABEL_FG).grid(row=2, column=0, sticky="w", pady=(6, 0))

        # Per-URL statistics
        self.url_stats = tk.Frame(self.url_inner, bg=BG_COLOR)
        self.url_stats.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.url_stats.grid_columnconfigure(0, weight=1)
        
        self.stat_chapters = tk.StringVar(value="Kapitel: 0/0 abgeschlossen")
        self.stat_images = tk.StringVar(value="Bilder gesamt: 0 heruntergeladen")
        self.stat_avg = tk.StringVar(value="Durchschnitt: 0.0 Bilder/Chapter")
        self.stat_rate = tk.StringVar(value="Geschwindigkeit: 0.0 Chapters/Min")
        self.stat_eta = tk.StringVar(value="Geschätzte Restzeit: 00:00")
        
        for r, var in enumerate([self.stat_chapters, self.stat_images, self.stat_avg, self.stat_rate, self.stat_eta]):
            tk.Label(self.url_stats, textvariable=var, bg=BG_COLOR, fg=LABEL_FG).grid(row=r, column=0, sticky="w")

        # Button section
        self.btn_bar = tk.Frame(self.content, bg=BG_COLOR)
        self.btn_bar.grid(row=5, column=0, pady=(15, 10))
        
        self.btn_reset = create_button(self.btn_bar, " Reset", variant="reset", command=self._on_reset)
        self.btn_start = create_button(self.btn_bar, " Bulk-Download starten", variant="primary", command=self._on_start)
        self.btn_pause = create_button(self.btn_bar, " Pausieren", variant="pause", command=self._on_pause_resume)
        self.btn_skip = create_button(self.btn_bar, " Diese URL überspringen", variant="skip", command=self._on_skip)
        self.btn_stop = create_button(self.btn_bar, " Stoppen", variant="alert", command=self._on_stop)
        self.btn_restart = create_button(self.btn_bar, " Neuen Download beginnen", variant="primary", command=self._on_restart)

        # State init
        self._apply_state_idle()
        # Initial Fokus auf Canvas setzen
        try:
            self._canvas.focus_set()
        except Exception:
            pass

    def _start_url_timer(self, manga_title: str = "") -> None:
        """Start the per-URL timer with manga title."""
        self.url_progress.configure(value=0)
        self._current_manga_title = manga_title.strip() or "Unbekannt"
        self.url_timer_var.set(f"{self._current_manga_title} - Laufzeit: 00:00")
        
        # Initialize timer bookkeeping
        self._url_timer_running = True
        self._url_timer_start = __import__("time").time()
        self._url_timer_pause_start = 0.0
        self._url_timer_total_paused = 0.0

        def _tick_url():
            if not getattr(self, "_url_timer_running", False):
                return
            now = __import__("time").time()
            elapsed = now - self._url_timer_start - self._url_timer_total_paused
            if getattr(self, "_paused", False) and getattr(self, "_url_timer_pause_start", 0.0) > 0:
                elapsed -= (now - self._url_timer_pause_start)
            elapsed = int(max(0, elapsed))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            ss = elapsed % 60
            
            title = getattr(self, "_current_manga_title", "") or "Unbekannt"
            txt = f"{title} - Laufzeit: {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"{title} - Laufzeit: {mm:02d}:{ss:02d}"
            self.url_timer_var.set(txt)
            self.frame.after(1000, _tick_url)

        self.frame.after(1000, _tick_url)

    def _stop_url_timer(self, success: bool) -> None:
        """Stop the per-URL timer and show final time."""
        self._url_timer_running = False
        now = __import__("time").time()
        elapsed = now - getattr(self, "_url_timer_start", now) - getattr(self, "_url_timer_total_paused", 0.0)
        if getattr(self, "_paused", False) and getattr(self, "_url_timer_pause_start", 0.0) > 0:
            elapsed -= (now - self._url_timer_pause_start)
        elapsed = int(max(0, elapsed))
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        ss = elapsed % 60
        title = getattr(self, "_current_manga_title", "") or "Unbekannt"
        txt = f"{title} - Laufzeit: {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"{title} - Laufzeit: {mm:02d}:{ss:02d}"
        self.url_timer_var.set(txt)

    def _start_overall_timer(self) -> None:
        """Start the overall bulk download timer."""
        self._timer_running = True
        self._timer_start = __import__("time").time()
        self._timer_pause_start = 0.0
        self._timer_total_paused = 0.0

        def _tick():
            if not getattr(self, "_timer_running", False):
                return
            now = __import__("time").time()
            elapsed = now - self._timer_start - self._timer_total_paused
            if self._paused and self._timer_pause_start > 0:
                elapsed -= (now - self._timer_pause_start)
            elapsed = int(max(0, elapsed))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            ss = elapsed % 60
            txt = f"Gesamte Laufzeit: {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"Gesamte Laufzeit: {mm:02d}:{ss:02d}"
            self.timer_var.set(txt)
            self.frame.after(1000, _tick)

        self.frame.after(1000, _tick)

    def _stop_overall_timer(self) -> None:
        """Stop the overall bulk download timer."""
        self._timer_running = False

    # --- Per-URL Timer helpers

    # --- Table helpers
    def _refresh_table(self, keep_index: Optional[int] = None) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for i, it in enumerate(self.bulk_items, start=1):
            mode_text = "Auto" if it.get("mode") == "auto" else f"Manuell({it.get('max_chapters', 0)})"
            self.tree.insert("", "end", values=(i, it.get("title", ""), it.get("url", ""), it.get("folder", ""), mode_text, it.get("state", "pending"), int(it.get("progress", 0))))
        if keep_index is not None and 0 <= keep_index < len(self.bulk_items):
            iid = self.tree.get_children()[keep_index]
            self.tree.selection_set(iid)
            self.tree.see(iid)
        # Update table pixel height and columns after data changes
        self._update_table_height()
        self._schedule_resize_columns()
        # Update overall total in idle state so it shows e.g. 0/N at start
        self._update_overall_label_idle()

    def _add_url(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            return
        # Ableitung von Titel/Ordner direkt beim Hinzufügen
        derived_title = extract_title_from_url(url) or ""
        if derived_title:
            derived_folder = suggest_output_folder(self.standard_dir, derived_title)
        else:
            derived_folder = self.standard_dir
        item = {
            "url": url,
            "title": derived_title,
            "folder": derived_folder,
            "mode": "manual",
            "max_chapters": 5,
            "merge_after": False,
            "merge_chapters": 3,
            "delete_originals": False,
            "only_new_manifest": False,
            "delete_images": False,
            "state": "pending",
            "progress": 0,
        }
        self.bulk_items.append(item)
        self._refresh_table(keep_index=len(self.bulk_items) - 1)
        self.url_var.set("")

    def _remove_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        indices = sorted([self.tree.index(i) for i in sel], reverse=True)
        for idx in indices:
            if 0 <= idx < len(self.bulk_items):
                del self.bulk_items[idx]
        self._refresh_table()
        self.editor_outer.grid_remove()

    def _move_up(self) -> None:
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        idx = self.tree.index(sel[0])
        if idx > 0:
            # Save current editor state to the current item before reorder
            self._save_editor_to_item(idx)
            # Reorder list items (no data overwrite beyond swapping order)
            self.bulk_items[idx - 1], self.bulk_items[idx] = self.bulk_items[idx], self.bulk_items[idx - 1]
            new_idx = idx - 1
            self._refresh_table(keep_index=new_idx)
            # Update editor mapping and content
            self._current_editor_index = new_idx
            # keep pin in sync if necessary
            if self._editor_pinned_index is not None and self._editor_pinned_index == idx:
                self._editor_pinned_index = new_idx
            try:
                self._populate_editor(self.bulk_items[new_idx])
                if self.state != "running":
                    self.editor_outer.grid()
            except Exception:
                pass

    def _move_down(self) -> None:
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        idx = self.tree.index(sel[0])
        if idx < len(self.bulk_items) - 1:
            # Save current editor state to the current item before reorder
            self._save_editor_to_item(idx)
            # Reorder list items
            self.bulk_items[idx + 1], self.bulk_items[idx] = self.bulk_items[idx], self.bulk_items[idx + 1]
            new_idx = idx + 1
            self._refresh_table(keep_index=new_idx)
            # Update editor mapping and content
            self._current_editor_index = new_idx
            # keep pin in sync if necessary
            if self._editor_pinned_index is not None and self._editor_pinned_index == idx:
                self._editor_pinned_index = new_idx
            try:
                self._populate_editor(self.bulk_items[new_idx])
                if self.state != "running":
                    self.editor_outer.grid()
            except Exception:
                pass

    def _clear_list(self) -> None:
        self.bulk_items.clear()
        self._refresh_table()
        self.editor_outer.grid_remove()

    def _on_select_row(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            self.editor_outer.grid_remove()
            self._editor_user_select = False
            return
        # During running, only open on explicit user click; otherwise ignore programmatic selections
        if self.state == "running" and not getattr(self, "_editor_user_select", False):
            return
        # reset the flag for subsequent events
        self._editor_user_select = False
        idx = self.tree.index(sel[0])
        # Save previous editor values to its item before switching
        if self._current_editor_index is not None and 0 <= self._current_editor_index < len(self.bulk_items):
            self._save_editor_to_item(self._current_editor_index)
        self._current_editor_index = idx
        # pin the editor to this row while running
        if self.state == "running":
            self._editor_pinned_index = idx
        it = self.bulk_items[idx]
        self._populate_editor(it)
        self.editor_outer.grid()

    def _populate_editor(self, it: Dict[str, Any]) -> None:
        e = self.editor
        # Fill fields without triggering additional logic
        try:
            self._is_populating_editor = True
            # Derive title/folder from URL when missing
            title_val = (it.get("title") or "").strip()
            if not title_val:
                title_from_url = extract_title_from_url(it.get("url", ""))
                if title_from_url:
                    title_val = title_from_url
                    it["title"] = title_val
            folder_val = (it.get("folder") or "").strip()
            if not folder_val or folder_val.startswith(self.standard_dir):
                if title_val:
                    folder_suggest = suggest_output_folder(self.standard_dir, title_val)
                    folder_val = folder_suggest
                    it["folder"] = folder_val

            e["title_entry"].delete(0, tk.END)
            e["title_entry"].insert(0, title_val)
            e["folder_entry"].delete(0, tk.END)
            e["folder_entry"].insert(0, folder_val or self.standard_dir)
            manual = it.get("mode", "manual") != "auto"
            e["manual_var"].set(bool(manual))
            e["auto_var"].set(not manual)
            e["manual_count_var"].set(str(int(it.get("max_chapters", 5))))
            e["merge_var"].set(bool(it.get("merge_after", False)))
            e["merge_chapters_var"].set(str(int(it.get("merge_chapters", 3))))
            e["delete_originals_var"].set(bool(it.get("delete_originals", False)))
            e["only_new_manifest_var"].set(bool(it.get("only_new_manifest", False)))
            e["delete_images_var"].set(bool(it.get("delete_images", False)))
            # toggle merge options frame
            if e["merge_var"].get():
                try:
                    e["merge_opts_frame"].grid()
                except Exception:
                    pass
            else:
                try:
                    e["merge_opts_frame"].grid_remove()
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._is_populating_editor = False

    def _bind_editor_change_events(self) -> None:
        """Bindet Änderungen im Detail-Editor, sodass sie dem aktuell ausgewählten Item zugewiesen werden."""
        e = self.editor
        def _save_current(_evt=None):
            if self._is_populating_editor:
                return
            if self._current_editor_index is not None:
                self._save_editor_to_item(self._current_editor_index)
                # Live-update the corresponding table row
                self._update_tree_row(self._current_editor_index)
        try:
            e["title_entry"].bind("<KeyRelease>", _save_current)
            e["folder_entry"].bind("<KeyRelease>", _save_current)
        except Exception:
            pass
        # Trace variables
        try:
            e["manual_var"].trace_add("write", lambda *a: _save_current())
            e["auto_var"].trace_add("write", lambda *a: _save_current())
            e["manual_count_var"].trace_add("write", lambda *a: _save_current())
            e["merge_var"].trace_add("write", lambda *a: _save_current())
            e["merge_chapters_var"].trace_add("write", lambda *a: _save_current())
            e["delete_originals_var"].trace_add("write", lambda *a: _save_current())
            e["only_new_manifest_var"].trace_add("write", lambda *a: _save_current())
            e["delete_images_var"].trace_add("write", lambda *a: _save_current())
        except Exception:
            pass

    def _update_tree_row(self, idx: int) -> None:
        """Aktualisiert die Werte der Tabellenzeile idx anhand der gespeicherten Item-Daten."""
        try:
            if idx < 0 or idx >= len(self.bulk_items):
                return
            it = self.bulk_items[idx]
            mode_text = "Auto" if it.get("mode") == "auto" else f"Manuell({int(it.get('max_chapters', 0))})"
            values = (
                idx + 1,
                it.get("title", ""),
                it.get("url", ""),
                it.get("folder", ""),
                mode_text,
                it.get("state", "pending"),
                int(it.get("progress", 0)),
            )
            children = self.tree.get_children()
            if idx < len(children):
                self.tree.item(children[idx], values=values)
        except Exception:
            pass

    def _on_tree_click(self, event) -> None:
        """Wenn in leeren Bereich geklickt wird: Auswahl löschen und Editor ausblenden."""
        try:
            row = self.tree.identify_row(event.y)
        except Exception:
            row = ""
        if not row:
            try:
                self.tree.selection_remove(self.tree.selection())
            except Exception:
                pass
            self._current_editor_index = None
            self.editor_outer.grid_remove()
            # clear pin when user clicks empty area
            self._editor_pinned_index = None
        else:
            # mark this as a user-initiated selection so _on_select_row may open during running
            self._editor_user_select = True
            try:
                self._last_tree_click_ts = __import__("time").time()
            except Exception:
                self._last_tree_click_ts = 0.0

    def _save_editor_to_item(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.bulk_items):
            return
        it = self.bulk_items[idx]
        e = self.editor
        it["title"] = e["title_entry"].get().strip() or it.get("title", "")
        it["folder"] = e["folder_entry"].get().strip() or it.get("folder", self.standard_dir)
        manual = bool(e["manual_var"].get())
        it["mode"] = "manual" if manual else "auto"
        try:
            it["max_chapters"] = int(e["manual_count_var"].get()) if manual else 0
        except Exception:
            it["max_chapters"] = 0
        it["merge_after"] = bool(e["merge_var"].get())
        try:
            it["merge_chapters"] = int(e["merge_chapters_var"].get())
        except Exception:
            it["merge_chapters"] = 3
        it["delete_originals"] = bool(e["delete_originals_var"].get())
        it["only_new_manifest"] = bool(e["only_new_manifest_var"].get())
        it["delete_images"] = bool(e["delete_images_var"].get())

    def _clear_btn_bar(self) -> None:
        for w in self.btn_bar.grid_slaves():
            w.grid_forget()

    def _apply_state_idle(self) -> None:
        self.state = "idle"
        # hide progress container and border in idle
        try:
            self.run_outer.grid_remove()
        except Exception:
            pass
        try:
            self.run_border.grid_remove()
        except Exception:
            pass
        self._clear_btn_bar()
        self.btn_reset.grid(row=0, column=0, padx=(0, 10))
        self.btn_start.grid(row=0, column=1)
        if download_multiple_chapters is None:
            self.btn_start.configure(state="disabled")
            self.status_var.set("❌ Downloader nicht verfügbar")
        else:
            self.btn_start.configure(state="normal")
            self.status_var.set(" Bereit…")
        self.progress.configure(value=0)
        self.timer_var.set("Gesamte Laufzeit: 00:00")
        # show current queue size right away
        try:
            total = len(self.bulk_items)
        except Exception:
            total = 0
        self.overall_stat_var.set(f"Manga 0/{total} heruntergeladen")

    def _apply_state_running(self) -> None:
        self.state = "running"
        # show the border and container when running
        try:
            self.run_border.grid()
        except Exception:
            pass
        try:
            self.run_outer.grid()
        except Exception:
            pass
        self._clear_btn_bar()
        self.btn_pause.grid(row=0, column=0, padx=(0, 8))
        self.btn_skip.grid(row=0, column=1, padx=(0, 8))
        self.btn_stop.grid(row=0, column=2)
        # ensure per-URL sections are visible when a run starts
        try:
            self.url_inner.grid()
        except Exception:
            pass
        try:
            self.url_stats.grid()
        except Exception:
            pass

    def _apply_state_done(self) -> None:
        self.state = "done"
        # keep the border and container visible to show final summary
        try:
            self.run_border.grid()
        except Exception:
            pass
        try:
            self.run_outer.grid()
        except Exception:
            pass
        self._clear_btn_bar()
        self.btn_restart.grid(row=0, column=0)
        # hide per-URL progress and stats after completion
        try:
            self.url_inner.grid_remove()
        except Exception:
            pass
        try:
            self.url_stats.grid_remove()
        except Exception:
            pass

    # --- Buttons
    def _on_start(self) -> None:
        if not self.bulk_items:
            messagebox.showerror("Leere Warteschlange", "Bitte mindestens eine URL hinzufügen.")
            return
        if download_multiple_chapters is None:
            messagebox.showerror("Fehlende Abhängigkeit", f"Downloader-Logik nicht verfügbar: {IMPORT_ERROR_DOWNLOADER}")
            return
        # ensure current selection edits saved
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            self._save_editor_to_item(idx)

        self._flags.update({"running": True, "stop": False, "skip": False})
        self._apply_state_running()
        # keep detail editor hidden during run
        try:
            self.editor_outer.grid_remove()
        except Exception:
            pass
        # prevent programmatic selection from opening the editor
        try:
            self.tree.selection_remove(self.tree.selection())
        except Exception:
            pass
        self._editor_user_select = False
        self._last_tree_click_ts = 0.0
        self._editor_pinned_index = None
        self.progress.configure(value=0)
        self.timer_var.set("Gesamte Laufzeit: 00:00")
        self._start_overall_timer()

        def worker():
            total = len(self.bulk_items)
            completed = 0
            for idx, it in enumerate(self.bulk_items):
                if self._flags["stop"]:
                    break
                if it.get("state") not in ("pending", "failed", "skipped"):
                    completed += 1
                    continue

                # persist last selection edits if current row
                try:
                    sel = self.tree.selection()
                    if sel and self.tree.index(sel[0]) == idx:
                        self._save_editor_to_item(idx)
                except Exception:
                    pass

                url = it.get("url", "").strip()
                title = it.get("title", "").strip()
                folder = it.get("folder", self.standard_dir).strip() or self.standard_dir
                auto = it.get("mode") == "auto"
                max_chapters = 0 if auto else int(it.get("max_chapters", 0))
                os.makedirs(folder, exist_ok=True)

                it["state"] = "in_progress"
                it["progress"] = 0
                self.frame.after(0, self._refresh_table)
                # Prepare per-URL UI: reset bar, start timer
                self.frame.after(0, lambda: self._start_url_timer(title))
                self.frame.after(0, self.status_var.set, f"[{idx+1}/{total}] {title or url}…")

                # pause loop before starting
                while self._paused and not self._flags["stop"]:
                    __import__("time").sleep(0.1)

                # Run one item
                try:
                    # Merke den Modus für die per-URL Progress-Logik
                    try:
                        self._url_run_auto_mode = bool(auto)
                    except Exception:
                        self._url_run_auto_mode = False
                    download_multiple_chapters(
                        start_url=url,
                        output_folder=folder,
                        manga_title=title,
                        max_chapters=max_chapters,
                        auto_detect=auto,
                        ui_update=lambda m, i=idx, t=total: self.frame.after(0, self._update_status_line, i, t, m),
                        progress_update=lambda p, i=idx: self.frame.after(0, self._update_progress_item, i, int(p)),
                        stats_update=lambda d, t, imgs, avg, cpm, eta, i=idx: self.frame.after(0, self._on_stats, i, d, t, imgs, avg, cpm, eta),
                        delete_images_after_pdf=bool(it.get("delete_images", False)),
                        keep_manifest=bool(it.get("merge_after", False) and it.get("only_new_manifest", False)),
                    )
                    # Optional: merge PDFs after this item, if requested
                    if bool(it.get("merge_after", False)) and merge_pdfs is not None:
                        try:
                            merge_chapters = int(it.get("merge_chapters", 3))
                        except Exception:
                            merge_chapters = 3
                        only_new_manifest = bool(it.get("only_new_manifest", False))
                        # Status update before merge
                        try:
                            self.frame.after(0, self.status_var.set, "🧩 Starte PDF-Merge…")
                        except Exception:
                            pass
                        try:
                            merge_pdfs(
                                folder,
                                merge_chapters,
                                lambda m: self.frame.after(0, self.status_var.set, m),
                                selected_files=None,
                                use_session_manifest=only_new_manifest,
                                ignore_merged=True,
                            )
                            # Optional: delete _originals folder after merge if selected
                            if bool(it.get("delete_originals", False)):
                                try:
                                    import shutil as _shutil
                                    _shutil.rmtree(os.path.join(folder, "_originals"), ignore_errors=True)
                                except Exception:
                                    pass
                            # Cleanup manifest pointer if only_new_manifest was used
                            if only_new_manifest:
                                try:
                                    pointer = os.path.join(folder, "latest_manifest.txt")
                                    manifests_dir = os.path.join(folder, "_manifests")
                                    with __import__("contextlib").suppress(Exception):
                                        if os.path.exists(pointer):
                                            os.remove(pointer)
                                    with __import__("contextlib").suppress(Exception):
                                        if os.path.isdir(manifests_dir):
                                            import shutil as _shutil
                                            _shutil.rmtree(manifests_dir)
                                except Exception:
                                    pass
                        except Exception as me:
                            self.frame.after(0, self._append_log, f"❌ Merge-Fehler: {me}\n")
                    it["state"] = "skipped" if self._flags["skip"] else "completed"
                    it["progress"] = 100
                    completed += 1
                    self._flags["skip"] = False
                    self.frame.after(0, self._refresh_table)
                    self.frame.after(0, self._update_overall_progress, completed, total)
                    self.frame.after(0, self._stop_url_timer, True)
                    # Show log window upon first completion
                    if not self._log_visible:
                        self._log_visible = True
                        try:
                            self.log_outer.grid()
                        except Exception:
                            pass
                    # Append formatted entry
                    state_text = "übersprungen" if it["state"] == "skipped" else "download abgeschlossen"
                    self._append_log(f"URL Nr. {idx+1:02d} - {title or url}: {state_text}\n")
                except Exception as e:  # pragma: no cover
                    it["state"] = "failed"
                    it["last_message"] = str(e)
                    self.frame.after(0, self._refresh_table)
                    self.frame.after(0, self._stop_url_timer, False)
                    self._append_log(f"❌ Fehler bei URL Nr. {idx+1:02d}: {e}\n")
                    continue

                # stop requested
                if self._flags["stop"]:
                    break

            # finish
            self._stop_overall_timer()
            self.frame.after(0, self._finish_done)

        threading.Thread(target=worker, daemon=True).start()

    def _update_status_line(self, idx: int, total: int, msg: str) -> None:
        self.status_var.set(f"[{idx+1}/{total}] {msg}")

    def _update_progress_item(self, idx: int, p: int) -> None:
        # Im Auto-Modus übernimmt _on_stats die Fortschrittsanzeige; hier überspringen
        try:
            if getattr(self, "_url_run_auto_mode", False):
                return
        except Exception:
            pass
        if 0 <= idx < len(self.bulk_items):
            self.bulk_items[idx]["progress"] = p
        self._refresh_table(keep_index=idx)
        try:
            self.url_progress.configure(value=int(p))
        except Exception:
            pass

    def _update_overall_progress(self, completed: int, total: int) -> None:
        # y = Anzahl der URLs in der Tabelle, nicht Kapitel
        try:
            total_urls = len(self.bulk_items)
        except Exception:
            total_urls = total
        total_urls = max(1, int(total_urls))
        
        # x = Anzahl der URLs die bereits heruntergeladen wurden (completed/skipped)
        try:
            completed_urls = sum(1 for item in self.bulk_items if item.get("state") in ("completed", "skipped"))
        except Exception:
            completed_urls = max(0, int(completed))
        
        self.overall_stat_var.set(f"Manga {completed_urls}/{total_urls} heruntergeladen")
        try:
            pct = int(min(100, max(0, round(completed_urls * 100 / total_urls))))
        except Exception:
            pct = 0
        self.progress.configure(value=pct)

    def _update_overall_label_idle(self) -> None:
        """When idle/not running, reflect current total items in the overall label."""
        if self.state == "running":
            return
        try:
            total = len(self.bulk_items)
        except Exception:
            total = 0
        self.overall_stat_var.set(f"Manga 0/{total} heruntergeladen")

    def _append_log(self, line: str) -> None:
        try:
            self.log.configure(state="normal")
            self.log.insert("end", line)
            self.log.see("end")
            self.log.configure(state="disabled")
        except Exception:
            pass

    # --- Tabellenhöhe einstellen
    def _update_table_height(self) -> None:
        """Set the pixel height of the table wrapper according to item count.
        Rules:
        - Initially (0 items): 60 px fixed
        - Thereafter: (n + 1) * TABLE_ROW_HEIGHT
        """
        try:
            n = len(self.bulk_items)
        except Exception:
            n = 0
        height_px = max(60, (n + 1) * int(TABLE_ROW_HEIGHT)) if n == 0 else (n + 3) * int(TABLE_ROW_HEIGHT)
        # Add 1 px so the lower border is not clipped
        height_px += 1
        try:
            self.table_wrap.configure(height=height_px)
            self.table_wrap.grid_propagate(False)
        except Exception:
            pass
        # Adjust tree visible rows to approximate the same pixel height
        try:
            rows = max(1, height_px // max(1, int(TABLE_ROW_HEIGHT)))
            self.tree.configure(height=rows)
        except Exception:
            pass

    def _schedule_resize_columns(self) -> None:
        try:
            self.frame.after(80, self._resize_columns)
        except Exception:
            pass

    def _on_table_wrap_configure(self, _event=None) -> None:
        self._resize_columns()

    def _resize_columns(self) -> None:
        try:
            width = self.table_wrap.winfo_width()
        except Exception:
            width = 0
        if width <= 1:
            self._schedule_resize_columns()
            return
        avail = max(0, width)
        if avail <= 0:
            return

        base_widths = {
            "#": 40,
            "Titel": 180,
            "URL": 260,
            "Ordner": 220,
            "Modus": 110,
            "Status": 110,
            "%": 60,
        }
        min_widths = {
            "#": 40,
            "Titel": 90,
            "URL": 120,
            "Ordner": 120,
            "Modus": 80,
            "Status": 80,
            "%": 50,
        }

        total_base = sum(base_widths.values())
        scale = 1.0
        if total_base > 0:
            scale = min(1.0, avail / total_base)

        widths = {}
        for col in base_widths:
            widths[col] = max(min_widths[col], int(base_widths[col] * scale))

        total_width = sum(widths.values())
        delta = avail - total_width

        flex_order = ["URL", "Ordner", "Titel", "Status", "Modus"]
        idx = 0
        guard = max(1, len(flex_order) * 200)
        while delta > 0 and guard > 0:
            col = flex_order[idx % len(flex_order)]
            widths[col] += 1
            delta -= 1
            idx += 1
            guard -= 1

        idx = 0
        guard = max(1, len(flex_order) * 200)
        while delta < 0 and guard > 0:
            col = flex_order[idx % len(flex_order)]
            if widths[col] > min_widths[col]:
                widths[col] -= 1
                delta += 1
            idx += 1
            guard -= 1

        for col, width in widths.items():
            stretch = col in {"URL", "Ordner", "Titel", "Status", "Modus"}
            try:
                self.tree.column(col, width=width, stretch=stretch)
            except Exception:
                pass

    def _on_pause_resume(self) -> None:
        if self.state != "running" or download_controller is None:
            return
        self._paused = not self._paused
        now_ts = __import__("time").time()
        if self._paused:
            if download_controller.pause_start_time <= 0:
                download_controller.pause_start_time = now_ts
            download_controller.is_paused = True
            self._timer_pause_start = now_ts
            try:
                self.btn_pause.configure(text=" Fortsetzen")
            except Exception:
                pass
            # per-URL timer pause bookkeeping
            try:
                if getattr(self, "_url_timer_running", False) and getattr(self, "_url_timer_pause_start", 0.0) <= 0:
                    self._url_timer_pause_start = now_ts
            except Exception:
                pass
        else:
            if download_controller.pause_start_time > 0:
                download_controller.total_paused_duration += now_ts - download_controller.pause_start_time
            download_controller.pause_start_time = 0.0
            download_controller.is_paused = False
            try:
                self.btn_pause.configure(text=" Pausieren")
            except Exception:
                pass
            # accumulate overall paused time
            try:
                self._timer_total_paused += now_ts - self._timer_pause_start
            except Exception:
                pass
            # per-URL timer resume bookkeeping
            try:
                if getattr(self, "_url_timer_running", False) and getattr(self, "_url_timer_pause_start", 0.0) > 0:
                    self._url_timer_total_paused += now_ts - self._url_timer_pause_start
                    self._url_timer_pause_start = 0.0
            except Exception:
                pass

    def _on_stop(self) -> None:
        self._flags["stop"] = True
        if download_controller is not None:
            download_controller.should_stop = True
            download_controller.is_paused = False
            download_controller.pause_start_time = 0.0
        self.status_var.set("⏹️ Stoppen angefordert…")

    def _on_skip(self) -> None:
        self._flags["skip"] = True
        if download_controller is not None:
            download_controller.should_stop = True
            download_controller.is_paused = False
            download_controller.pause_start_time = 0.0
        self.status_var.set("⏭️ Überspringen angefordert…")

    def _on_reset(self) -> None:
        self.url_var.set("")
        self.bulk_items.clear()
        self._refresh_table()
        self.editor_outer.grid_remove()
        self.progress.configure(value=0)
        self.timer_var.set("Gesamte Laufzeit: 00:00")
        self.overall_stat_var.set("Manga 0/0 runtergeladen")
        self.status_var.set(" Bereit…")
        self._apply_stats(0, 0, 0, 0.0, 0.0, 0.0)
        try:
            self.url_progress.configure(value=0)
            self._current_manga_title = ""
            self.url_timer_var.set("Laufzeit: 00:00")
        except Exception:
            pass
        self.editor["folder_entry"].delete(0, tk.END)
        self.editor["folder_entry"].insert(0, self.standard_dir)
        self.editor["standard_dir_var"].set(self.standard_dir)
        self.editor["standard_info_var"].set(f"Standardordner: {self.standard_dir}")
        self._apply_state_idle()

    def _on_restart(self) -> None:
        self._on_reset()

    def _finish_done(self) -> None:
        self._apply_state_done()
        self.status_var.set("✅ Bulk abgeschlossen")
        self.progress.configure(value=100)
        try:
            # finalize per-URL timer
            self._stop_url_timer(True)
        except Exception:
            pass
        # Show final overall runtime as a finished message
        try:
            now = __import__("time").time()
            elapsed = now - getattr(self, "_timer_start", now) - getattr(self, "_timer_total_paused", 0.0)
            if getattr(self, "_paused", False) and getattr(self, "_timer_pause_start", 0.0) > 0:
                elapsed -= (now - self._timer_pause_start)
            elapsed = int(max(0, elapsed))
            hh = elapsed // 3600
            mm = (elapsed % 3600) // 60
            ss = elapsed % 60
            txt = (f"Download beendet in {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"Download beendet in {mm:02d}:{ss:02d}")
            self.timer_var.set(txt)
        except Exception:
            pass

    # stats helper
    def _apply_stats(self, done: int, total: int, total_imgs: int, avg_imgs: float, cpm: float, eta_sec: float) -> None:
        try:
            self.stat_chapters.set(f"Kapitel: {int(done)}/{int(total) if total else 0} abgeschlossen")
            self.stat_images.set(f"Bilder gesamt: {int(total_imgs)} heruntergeladen")
            self.stat_avg.set(f"Durchschnitt: {float(avg_imgs):.1f} Bilder/Chapter")
            self.stat_rate.set(f"Geschwindigkeit: {float(cpm):.1f} Chapters/Min")
            mm = int(float(eta_sec) // 60)
            ss = int(float(eta_sec) % 60)
            self.stat_eta.set(f"Geschätzte Restzeit: {mm:02d}:{ss:02d}")
        except Exception:
            pass

    def _on_stats(self, idx: int, done: int, total: int, total_imgs: int, avg_imgs: float, cpm: float, eta_sec: float) -> None:
        """Wrapper um _apply_stats mit zusätzlicher Fortschrittslogik für Auto-Modus."""
        self._apply_stats(done, total, total_imgs, avg_imgs, cpm, eta_sec)
        try:
            if getattr(self, "_url_run_auto_mode", False) and int(total) > 0:
                pct = int(max(0, min(100, (int(done) * 100) // int(total))))
                # per-URL Balken setzen
                try:
                    self.url_progress.configure(value=pct)
                except Exception:
                    pass
                # Tabellen-% für aktuelle Zeile synchron halten
                if 0 <= idx < len(self.bulk_items):
                    try:
                        self.bulk_items[idx]["progress"] = pct
                    except Exception:
                        pass
                    self._refresh_table(keep_index=idx)
        except Exception:
            pass

    def widget(self) -> tk.Frame:
        return self.frame

    def _on_standard_dir_changed(self, new_dir: str) -> None:
        old_dir = self.standard_dir
        self.standard_dir = new_dir
        # Update labels only; do not auto-fill editor's folder field
        try:
            self.editor["standard_dir_var"].set(new_dir)
            self.editor["standard_info_var"].set(f"Standardordner: {new_dir}")
        except Exception:
            pass
        # Update items that used the old standard dir or were empty
        for item in self.bulk_items:
            try:
                folder = (item.get("folder", "") or "").strip()
                if not folder or folder == old_dir:
                    item["folder"] = new_dir
            except Exception:
                pass
        self._refresh_table()