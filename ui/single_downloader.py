"""
UI und Logik für den Single-Downloader
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .components import (
    create_button,
    create_progress_bar,
    create_detail_editor,
    create_scrollbar,
    create_help_icon,
)
from .theme import (
    BG_COLOR,
    ENTRY_BG,
    ENTRY_FG,
    LABEL_FG,
    DOWNLOAD_BORDER_COLOR,
    STYLE_BUTTON_PRIMARY,
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


class SingleDownloaderPanel:
    """Panel für den Single-Download"""

    def __init__(self, parent: tk.Widget, context: Optional[object] = None):
        """Initialisiert das Panel und baut das Layout auf.

        Layout:
        1) Chapter URL
        2) Detail-Editor
        3) Ladebalken + Statistiken
        4) Buttons (zustandsabhängig)
        """
        self.parent = parent
        self.context = context
        self.state = "idle"  # idle | running | done

        # Resolve standard download directory from settings
        settings = load_settings() or {}
        default_dir = settings.get("standard_dir") or os.path.expanduser("~")
        if self.context and hasattr(self.context, "standard_dir"):
            default_dir = getattr(self.context, "standard_dir", default_dir)
        self.standard_dir = default_dir
        self._last_standard_dir = self.standard_dir
        if self.context and hasattr(self.context, "register"):
            self.context.register(self._on_standard_dir_changed)

        # Root frame for this panel
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

        # MouseWheel-Handling setup
        self._setup_scroll_bindings()

        # URL input section
        url_row = tk.Frame(self.content, bg=BG_COLOR)
        url_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        url_row.grid_columnconfigure(1, weight=1)
        
        tk.Label(url_row, text=" Chapter URL:", bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w")
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG, relief="flat", bd=5)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=(8, 4))
        
        url_help_icon = create_help_icon(url_row, "single_downloader", "url_entry")
        url_help_icon.grid(row=0, column=2, padx=(4, 14))

        # 2) Detail-Editor
        editor_outer = tk.Frame(self.content, bg=BG_COLOR)
        editor_outer.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 6))
        editor_outer.grid_columnconfigure(0, weight=1)

        def _browse_dir() -> Optional[str]:
            path = filedialog.askdirectory()
            return path or None

        editor = create_detail_editor(
            editor_outer,
            standard_dir=self.standard_dir,
            browse_command=_browse_dir,
            url_entry=self.url_entry,
        )
        editor["frame"].grid(row=0, column=0, sticky="ew")
        
        # Apply scroll bindings to editor
        self._apply_scroll_bindings(editor_outer)
        self._apply_scroll_bindings(editor.get("frame", editor_outer))

        # 3) Ladebalken + Statistiken (in eigenem Rahmen)
        self.run_outer = tk.Frame(
            self.content,
            bg=BG_COLOR,
            highlightbackground=DOWNLOAD_BORDER_COLOR,
            highlightthickness=1,
            bd=0,
        )
        self.run_outer.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 6))
        self.run_outer.grid_columnconfigure(0, weight=1)

        run_inner = tk.Frame(self.run_outer, bg=BG_COLOR)
        run_inner.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        run_inner.grid_columnconfigure(0, weight=1)
        
        # Apply scroll bindings to download area
        self._apply_scroll_bindings(self.run_outer)
        self._apply_scroll_bindings(run_inner)
        self._apply_scroll_bindings(self.content)

        # Laufzeit (zentriert, größer)
        self.timer_var = tk.StringVar(value="Laufzeit: 00:00")
        self.status_var = tk.StringVar(value=" Bereit…")
        tk.Label(
            run_inner,
            textvariable=self.timer_var,
            bg=BG_COLOR,
            fg=LABEL_FG,
            font=("Arial", 14, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # Progressbar direkt darunter
        self.progress = create_progress_bar(run_inner, mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        # Status unterhalb des Ladebalken
        tk.Label(run_inner, textvariable=self.status_var, bg=BG_COLOR, fg=LABEL_FG).grid(
            row=2, column=0, sticky="w", pady=(6, 0)	
        )

        # Statistiken unterhalb des Status
        stats = tk.Frame(run_inner, bg=BG_COLOR)
        stats.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        stats.grid_columnconfigure(0, weight=1)
        self.stat_chapters = tk.StringVar(value="Kapitel: 0/0 abgeschlossen")
        self.stat_images = tk.StringVar(value="Bilder gesamt: 0 heruntergeladen")
        self.stat_avg = tk.StringVar(value="Durchschnitt: 0.0 Bilder/Chapter")
        self.stat_rate = tk.StringVar(value="Geschwindigkeit: 0.0 Chapters/Min")
        self.stat_eta = tk.StringVar(value="Geschätzte Restzeit: 00:00")
        for r, var in enumerate(
            [self.stat_chapters, self.stat_images, self.stat_avg, self.stat_rate, self.stat_eta]
        ):
            tk.Label(stats, textvariable=var, bg=BG_COLOR, fg=LABEL_FG).grid(row=r, column=0, sticky="w")


        # initially hidden in idle
        self.run_outer.grid_remove()

        # 4) Buttons (container, we will swap sets by state)
        self.btn_bar = tk.Frame(self.content, bg=BG_COLOR)
        self.btn_bar.grid(row=3, column=0, pady=(6, 10))

        # Idle buttons (Reset + Start)
        self.btn_reset = create_button(self.btn_bar, " Reset", variant="reset", command=self._on_reset)
        self.btn_start = create_button(
            self.btn_bar,
            " Download starten",
            variant="primary",
            command=self._on_start,
        )
        
        # Fragezeichen-Icons für Buttons hinzufügen
        reset_help_icon = create_help_icon(self.btn_bar, "single_downloader", "reset_button")
        reset_help_icon.grid(row=0, column=1, padx=(4, 0))
        
        start_help_icon = create_help_icon(self.btn_bar, "single_downloader", "start_button")
        start_help_icon.grid(row=0, column=2, padx=(4, 0))

        # Running buttons (Pause + Stop)
        self.btn_pause = create_button(self.btn_bar, " Pausieren", variant="pause", command=self._on_pause_resume)
        self.btn_stop = create_button(self.btn_bar, " Stoppen", variant="alert", command=self._on_stop)
        
        # Fragezeichen-Icons für Running-Buttons hinzufügen
        pause_help_icon = create_help_icon(self.btn_bar, "single_downloader", "pause_button")
        pause_help_icon.grid(row=0, column=3, padx=(4, 0))
        
        stop_help_icon = create_help_icon(self.btn_bar, "single_downloader", "stop_button")
        stop_help_icon.grid(row=0, column=4, padx=(4, 0))

        # Done button (Restart)
        self.btn_restart = create_button(
            self.btn_bar, " Neuen Download beginnen", variant="primary", command=self._on_restart
        )
        
        # Fragezeichen-Icon für Restart-Button hinzufügen
        restart_help_icon = create_help_icon(self.btn_bar, "single_downloader", "restart_button")
        restart_help_icon.grid(row=0, column=5, padx=(4, 0))

        # Keep references to editor inputs
        self.editor = editor

        # State init
        self._apply_state_idle()

    # --- Scroll handling
    def _setup_scroll_bindings(self) -> None:
        """Setup centralized scroll handling for the entire panel."""
        def _on_mousewheel(event):
            try:
                cx = self._canvas.winfo_rootx()
                cy = self._canvas.winfo_rooty()
                cw = self._canvas.winfo_width()
                ch = self._canvas.winfo_height()
                inside = (cx <= event.x_root <= cx + cw) and (cy <= event.y_root <= cy + ch)
            except Exception:
                inside = True
            
            if inside:
                try:
                    delta = int(-1 * (event.delta / 120))
                    self._canvas.yview_scroll(delta, "units")
                except Exception:
                    pass
                return "break"
            return None

        # Global binding
        self._canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Install scroll area tags
        def _install_scrollarea_tags(root_widget):
            self.frame.bind_class("ScrollArea", "<MouseWheel>", _on_mousewheel, add="+")
            def _walk(w):
                tags = w.bindtags()
                if "ScrollArea" not in tags:
                    w.bindtags(("ScrollArea",) + tags)
                for c in w.winfo_children():
                    _walk(c)
            _walk(root_widget)

        _install_scrollarea_tags(self.content)
        self.frame.after(0, lambda: _install_scrollarea_tags(self.content))

    def _apply_scroll_bindings(self, widget) -> None:
        """Apply scroll bindings to a specific widget."""
        def _bind_wheel_recursive(w):
            w.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), add="+")
            w.bind("<Enter>", lambda e: self._canvas.focus_set(), add="+")
            for c in w.winfo_children():
                _bind_wheel_recursive(c)
        
        _bind_wheel_recursive(widget)
        if hasattr(widget, 'bindtags'):
            widget.bindtags(("ScrollArea",) + widget.bindtags())

    def _start_timer(self) -> None:
        """Start the download timer."""
        self._timer_running = True
        self._timer_start = __import__("time").time()
        self._timer_pause_start = 0.0
        self._timer_total_paused = 0.0
        
        def _tick():
            if not getattr(self, "_timer_running", False):
                return
            now = __import__("time").time()
            elapsed = now - self._timer_start - self._timer_total_paused
            if getattr(self, "_paused", False) and self._timer_pause_start > 0:
                elapsed -= (now - self._timer_pause_start)
            elapsed = int(max(0, elapsed))
            mm = elapsed // 60
            ss = elapsed % 60
            self.timer_var.set(f"Laufzeit: {mm:02d}:{ss:02d}")
            self.frame.after(1000, _tick)
        
        self.frame.after(1000, _tick)
    
    def _stop_timer(self) -> None:
        """Stop the download timer."""
        self._timer_running = False
    
    def _pause_timer(self) -> None:
        """Pause the download timer."""
        if not getattr(self, "_paused", False):
            return
        now_ts = __import__("time").time()
        if self._timer_pause_start <= 0:
            self._timer_pause_start = now_ts
    
    def _resume_timer(self) -> None:
        """Resume the download timer."""
        if getattr(self, "_paused", False):
            return
        now_ts = __import__("time").time()
        if self._timer_pause_start > 0:
            self._timer_total_paused += now_ts - self._timer_pause_start
            self._timer_pause_start = 0.0

    # --- State management
    def _clear_btn_bar(self) -> None:
        for w in self.btn_bar.grid_slaves():
            w.grid_forget()

    def _apply_state_idle(self) -> None:
        self.state = "idle"
        self.run_outer.grid_remove()
        self._clear_btn_bar()
        self.btn_reset.grid(row=0, column=0, padx=(0, 10))
        self.btn_start.grid(row=0, column=1)
        # Disable start if logic missing
        if download_multiple_chapters is None:
            self.btn_start.configure(state="disabled")
            self.status_var.set("❌ Downloader nicht verfügbar")
        else:
            self.btn_start.configure(state="normal")
            self.status_var.set(" Bereit…")
        self.timer_var.set("Laufzeit: 00:00")
        self.progress.configure(value=0)

    def _apply_state_running(self) -> None:
        self.state = "running"
        self.run_outer.grid()
        self._clear_btn_bar()
        self.btn_pause.grid(row=0, column=0, padx=(0, 10))
        self.btn_stop.grid(row=0, column=1)

    def _apply_state_done(self) -> None:
        self.state = "done"
        self.run_outer.grid()
        self._clear_btn_bar()
        # Sicherstellen, dass Pause/Stop entfernt bleiben
        try:
            self.btn_pause.grid_remove()
            self.btn_stop.grid_remove()
        except Exception:
            pass
        try:
            self.btn_restart.configure(style=STYLE_BUTTON_PRIMARY)
        except Exception:
            pass
        self.btn_restart.grid(row=0, column=0)

    # --- Button handlers
    def _on_start(self) -> None:
        if download_multiple_chapters is None:
            messagebox.showerror("Fehlende Abhängigkeit", f"Downloader-Logik nicht verfügbar: {IMPORT_ERROR_DOWNLOADER}")
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Fehlende Eingabe", "Bitte eine Chapter-URL eingeben.")
            return

        title = self.editor["title_entry"].get().strip()
        output_folder = self.editor["folder_entry"].get().strip() or self.standard_dir
        manual = bool(self.editor["manual_var"].get())
        auto = not manual
        try:
            max_chapters = int(self.editor["manual_count_var"].get()) if manual else 0
        except Exception:
            max_chapters = 0

        merge_after = bool(self.editor["merge_var"].get())
        merge_chapters = int(self.editor["merge_chapters_var"].get()) if merge_after else 0
        delete_originals = bool(self.editor["delete_originals_var"].get())
        only_new_manifest = bool(self.editor["only_new_manifest_var"].get())
        delete_images = bool(self.editor["delete_images_var"].get())

        os.makedirs(output_folder, exist_ok=True)

        # Reset UI
        self.progress.configure(value=0)
        self.timer_var.set("Laufzeit: 00:00")
        self.status_var.set(" Starte Download…")
        self._apply_state_running()

        # timer state
        self._timer_running = True
        self._timer_start = __import__("time").time()
        self._timer_pause_start = 0.0
        self._timer_total_paused = 0.0

        def _tick():
            if not getattr(self, "_timer_running", False):
                return
            now = __import__("time").time()
            elapsed = now - self._timer_start - self._timer_total_paused
            if getattr(self, "_paused", False) and self._timer_pause_start > 0:
                elapsed -= (now - self._timer_pause_start)
            elapsed = int(max(0, elapsed))
            mm = elapsed // 60
            ss = elapsed % 60
            self.timer_var.set(f"Laufzeit: {mm:02d}:{ss:02d}")
            try:
                self.frame.after(1000, _tick)
            except Exception:
                pass

        self.frame.after(1000, _tick)

        # Merke den aktiven Run-Modus (für Progress-Logik)
        try:
            self._run_auto_mode = bool(auto)
        except Exception:
            self._run_auto_mode = False

        # Worker thread
        def worker():
            try:
                download_multiple_chapters(
                    start_url=url,
                    output_folder=output_folder,
                    manga_title=title,
                    max_chapters=max_chapters,
                    auto_detect=auto,
                    ui_update=lambda m: self.frame.after(0, self.status_var.set, m),
                    progress_update=lambda p: self.frame.after(0, self._on_progress, int(p)),
                    stats_update=lambda d, t, imgs, avg, cpm, eta: self.frame.after(0, self._on_stats, d, t, imgs, avg, cpm, eta),
                    delete_images_after_pdf=delete_images,
                    keep_manifest=bool(merge_after and only_new_manifest),
                )
                # Merge optional
                if merge_after:
                    try:
                        from logic.merger import merge_pdfs
                    except Exception:
                        merge_pdfs = None
                    if merge_pdfs is not None:
                        self.frame.after(0, self.status_var.set, "🧩 Starte PDF-Merge…")
                        try:
                            merge_pdfs(
                                output_folder,
                                merge_chapters,
                                lambda m: self.frame.after(0, self.status_var.set, m),
                                selected_files=None,
                                use_session_manifest=only_new_manifest,
                                ignore_merged=True,
                            )
                            # Nach erfolgreichem Merge: Manifest und Pointer aufräumen, wenn 'Nur neue' verwendet wurde
                            if only_new_manifest:
                                try:
                                    pointer = os.path.join(output_folder, "latest_manifest.txt")
                                    manifests_dir = os.path.join(output_folder, "_manifests")
                                    if os.path.exists(pointer):
                                        with __import__("contextlib").suppress(Exception):
                                            os.remove(pointer)
                                    if os.path.isdir(manifests_dir):
                                        import shutil as _shutil
                                        with __import__("contextlib").suppress(Exception):
                                            _shutil.rmtree(manifests_dir)
                                    self.frame.after(0, self.status_var.set, "🧹 Manifest bereinigt")
                                except Exception:
                                    pass
                        except Exception as me:
                            self.frame.after(0, self.status_var.set, f"❌ Merge-Fehler: {me}")
                        if delete_originals:
                            try:
                                import shutil as _shutil
                                _shutil.rmtree(os.path.join(output_folder, "_originals"), ignore_errors=True)
                            except Exception:
                                pass

                # Finish
                self.frame.after(0, self._finish_success)
            except Exception as e:  # pragma: no cover
                self.frame.after(0, lambda: messagebox.showerror("Fehler", str(e)))
                self.frame.after(0, self._finish_failed)

        threading.Thread(target=worker, daemon=True).start()

    def _on_pause_resume(self) -> None:
        if self.state != "running" or download_controller is None:
            return
        self._paused = not getattr(self, "_paused", False)
        now_ts = __import__("time").time()
        if self._paused:
            self.status_var.set(" ⏸️ Pausiert")
            # inner controller
            if download_controller.pause_start_time <= 0:
                download_controller.pause_start_time = now_ts
            download_controller.is_paused = True
            self._pause_timer()
            self.btn_pause.configure(text=" Fortsetzen")
        else:
            self.status_var.set(" ▶️ Fortgesetzt")
            if download_controller.pause_start_time > 0:
                download_controller.total_paused_duration += now_ts - download_controller.pause_start_time
            download_controller.pause_start_time = 0.0
            download_controller.is_paused = False
            self._resume_timer()
            self.btn_pause.configure(text=" Pausieren")

    def _on_stop(self) -> None:
        if download_controller is not None:
            download_controller.should_stop = True
            download_controller.is_paused = False
            download_controller.pause_start_time = 0.0
        self.status_var.set("⏹️ Stoppen angefordert…")

    def _on_reset(self) -> None:
        # Clear inputs and stats
        self.url_var.set("")
        self.editor["title_entry"].delete(0, tk.END)
        self.editor["folder_entry"].delete(0, tk.END)
        # leave empty; will be filled via URL autofill
        self.editor["standard_dir_var"].set(self.standard_dir)
        self.editor["standard_info_var"].set(f"Standardordner: {self.standard_dir}")
        self.editor["manual_var"].set(True)
        self.editor["auto_var"].set(False)
        self.editor["manual_count_var"].set("5")
        self.editor["merge_var"].set(False)
        self.editor["delete_originals_var"].set(False)
        self.editor["only_new_manifest_var"].set(False)
        self.editor["delete_images_var"].set(False)
        try:
            self.editor["merge_opts_frame"].grid_remove()
        except Exception:
            pass
        # Stats
        self.progress.configure(value=0)
        self.timer_var.set("Laufzeit: 00:00")
        self.status_var.set(" Bereit…")
        self._apply_stats(0, 0, 0, 0.0, 0.0, 0.0)
        # Timer & Pausenstatus vollständig zurücksetzen
        self._timer_running = False
        self._paused = False
        self._timer_start = 0.0
        self._timer_pause_start = 0.0
        self._timer_total_paused = 0.0
        # Letzten Stats-Snapshot verwerfen
        try:
            del self._last_stats
        except Exception:
            pass
        # Fokus auf URL-Feld setzen für schnellen Neustart
        try:
            self.url_entry.focus_set()
        except Exception:
            pass
        self._restore_window_size()
        self._apply_state_idle()

    def _on_restart(self) -> None:
        self._on_reset()

    # --- Helpers
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

    def _on_stats(self, done: int, total: int, total_imgs: int, avg_imgs: float, cpm: float, eta_sec: float) -> None:
        """Speichert den letzten Stats-Snapshot und aktualisiert die Anzeige."""
        try:
            self._last_stats = (
                int(done),
                int(total),
                int(total_imgs),
                float(avg_imgs),
                float(cpm),
                float(eta_sec),
            )
        except Exception:
            self._last_stats = (done, total, total_imgs, avg_imgs, cpm, eta_sec)
        self._apply_stats(done, total, total_imgs, avg_imgs, cpm, eta_sec)
        # Im Auto-Modus den Ladebalken anhand Kapitel done/total setzen
        try:
            if getattr(self, "_run_auto_mode", False) and int(total) > 0:
                pct = int(max(0, min(100, (int(done) * 100) // int(total))))
                self.progress.configure(value=pct)
        except Exception:
            pass

    def _on_progress(self, p: int) -> None:
        """Progress-Update aus der Downloader-Logik.
        - Im manuellen Modus direkt die Prozentzahl übernehmen (bestehendes Verhalten)
        - Im Automatik-Modus ignorieren, da der Balken aus den Kapitel-Stats gesetzt wird
        """
        try:
            if getattr(self, "_run_auto_mode", False):
                return
            self.progress.configure(value=int(p))
        except Exception:
            pass

    def _finish_success(self) -> None:
        self._stop_timer()
        # Berechne finale Laufzeit, damit die Anzeige den gesamten Download widerspiegelt
        elapsed_seconds = 0
        try:
            if getattr(self, "_timer_start", None):
                now_ts = __import__("time").time()
                elapsed_seconds = now_ts - self._timer_start - getattr(self, "_timer_total_paused", 0.0)
                if getattr(self, "_paused", False) and getattr(self, "_timer_pause_start", 0.0) > 0:
                    elapsed_seconds -= now_ts - self._timer_pause_start
        except Exception:
            elapsed_seconds = 0

        elapsed_seconds = max(0, int(elapsed_seconds))
        mm = elapsed_seconds // 60
        ss = elapsed_seconds % 60
        self.timer_var.set(f"Download abgeschlossen in {mm:02d}:{ss:02d}")
        # Letzte bekannte Statistiken noch einmal anzeigen
        try:
            if hasattr(self, "_last_stats") and isinstance(self._last_stats, tuple):
                d, t, imgs, avg, cpm, eta = self._last_stats
                self._apply_stats(d, t, imgs, avg, cpm, 0)
        except Exception:
            pass
        self.status_var.set("✅ Download abgeschlossen")
        self.progress.configure(value=100)
        self._apply_state_done()

    def _finish_failed(self) -> None:
        self._stop_timer()
        self._apply_state_done()

    # Public accessor to mount the panel
    def widget(self) -> tk.Frame:
        return self.frame

    # --- Context callbacks
    def _on_standard_dir_changed(self, new_dir: str) -> None:
        old_dir = self.standard_dir
        self.standard_dir = new_dir
        self.editor["standard_dir_var"].set(new_dir)
        self.editor["standard_info_var"].set(f"Standardordner: {new_dir}")
        folder_entry = self.editor["folder_entry"]
        try:
            current = folder_entry.get().strip()
        except Exception:
            current = ""
        if not current or current == old_dir:
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, new_dir)

    def _restore_window_size(self) -> None:
        """Stellt die Fenstergröße auf die ursprüngliche Geometrie zurück, wenn bekannt."""
        root = self.frame.winfo_toplevel()
        try:
            if getattr(self, "_window_original_geom", None):
                root.geometry(self._window_original_geom)
        except Exception:
            pass