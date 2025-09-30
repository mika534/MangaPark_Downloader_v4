"""
UI und Logik für den PDF-Merger
"""

from __future__ import annotations

import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional
import customtkinter as ctk

from .components import create_button, create_progress_bar, create_flat_button, create_scrollbar, create_help_icon, create_dark_dropdown
from .theme import (
    BG_COLOR,
    ENTRY_BG,
    ENTRY_FG,
    LABEL_FG,
    TABLE_BG,
    EXPORT_BORDER_COLOR,
    DOWNLOAD_BORDER_COLOR,
    DETAIL_BORDER_COLOR,
)

# Guarded import for merger logic
IMPORT_ERROR_MERGER: Optional[Exception] = None
try:
    from logic.merger import merge_pdfs
except Exception as e:  # pragma: no cover
    merge_pdfs = None  # type: ignore
    IMPORT_ERROR_MERGER = e


class PDFMergerPanel:
    """Panel für den PDF-Merger"""

    def __init__(self, parent: tk.Widget, context: Optional[object] = None):
        self.parent = parent
        self.context = context
        self.state = "idle"  # idle | running | done
        self._paused = False
        self._stop = False

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
        def _on_mousewheel(event):
            delta = int(-1 * (event.delta / 120))
            self._canvas.yview_scroll(delta, "units")
        
        self._canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Drop zone section
        drop_zone = tk.Frame(self.content, bg=ENTRY_BG, highlightthickness=1, highlightbackground=DETAIL_BORDER_COLOR)
        drop_zone.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 8))
        drop_zone.grid_columnconfigure(0, weight=1)
        
        dz_inner = tk.Frame(drop_zone, bg=ENTRY_BG)
        dz_inner.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        dz_inner.grid_columnconfigure(0, weight=1)
        
        dz_label = tk.Label(dz_inner, text="📄 Klicken zum Auswählen", bg=ENTRY_BG, fg=LABEL_FG, font=("Arial", 11, "bold"), pady=14)
        dz_label.grid(row=0, column=0, sticky="ew")

        self.selected_files: List[str] = []

        def add_files_dialog():
            files = filedialog.askopenfilenames(title="PDFs auswählen", filetypes=[("PDF", "*.pdf")])
            if files:
                for f in files:
                    if f.lower().endswith(".pdf") and os.path.isfile(f):
                        if f not in self.selected_files:
                            self.selected_files.append(f)
                self._refresh_file_list()
                self._auto_fill_folder_from_files()

        drop_zone.bind("<Button-1>", lambda e: add_files_dialog())
        dz_label.bind("<Button-1>", lambda e: add_files_dialog())
        drop_zone.bind("<Return>", lambda e: add_files_dialog())
        drop_zone.bind("<space>", lambda e: add_files_dialog())
        dz_label.bind("<Return>", lambda e: add_files_dialog())
        dz_label.bind("<space>", lambda e: add_files_dialog())

        # File list section
        list_outer = tk.Frame(self.content, bg=TABLE_BG, height=150)
        list_outer.grid(row=1, column=0, sticky="ew", padx=10)
        list_outer.grid_propagate(False)
        list_outer.grid_remove()  # hidden until files added
        
        columns = ("#", "Name", "Pfad")
        self.file_tree = ttk.Treeview(list_outer, columns=columns, show="headings", height=6, style="MPD.Treeview")
        
        for col, text, w, anchor in (("#", "#", 40, "center"), ("Name", "Name", 220, "w"), ("Pfad", "Pfad", 240, "w")):
            self.file_tree.heading(col, text=text, anchor=anchor)
            self.file_tree.column(col, width=w, anchor=anchor)
        
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        list_outer.grid_columnconfigure(0, weight=1)
        list_outer.grid_rowconfigure(0, weight=1)
        
        vsb = ttk.Scrollbar(list_outer, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        # Folder selection section
        folder_row = tk.Frame(self.content, bg=BG_COLOR)
        folder_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 6))
        folder_row.grid_columnconfigure(1, weight=1)
        
        tk.Label(folder_row, text=" Zielordner:", bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 11)).grid(row=0, column=0, sticky="w")
        
        self.folder_entry = tk.Entry(folder_row, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG, relief="flat", bd=5)
        self.folder_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        
        # Prevent blue selection on focus
        self.folder_entry.bind("<FocusIn>", lambda e: self._clear_entry_selection(self.folder_entry))
        
        # Setup standard directory
        self.standard_dir_var = tk.StringVar()
        self.standard_info_var = tk.StringVar()
        default_dir = ""
        if self.context and hasattr(self.context, "standard_dir"):
            default_dir = getattr(self.context, "standard_dir", "")
        if not default_dir:
            default_dir = os.path.expanduser("~")
        self.standard_dir_var.set(default_dir)
        self.standard_info_var.set(f"Standardordner: {default_dir}")
        self.folder_entry.insert(0, default_dir)
        self.folder_entry.selection_clear()
        self.folder_entry.icursor(tk.END)

        def browse_folder():
            sel = filedialog.askdirectory()
            if sel:
                self.folder_entry.delete(0, tk.END)
                self.folder_entry.insert(0, sel)
        
        browse_btn = create_flat_button(folder_row, " Browse", command=browse_folder)
        browse_btn.grid(row=0, column=2)
        
        # Set initial focus to browse button to avoid entry selection
        self.frame.after_idle(lambda: browse_btn.focus_set())
        
        self.standard_label = tk.Label(folder_row, textvariable=self.standard_info_var, bg=BG_COLOR, fg=LABEL_FG, anchor="w", font=("Arial", 9))
        self.standard_label.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 0))

        # Export settings section
        export_border = tk.Frame(self.content, bg=BG_COLOR, highlightbackground=EXPORT_BORDER_COLOR, highlightthickness=1, bd=0)
        export_border.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 6))
        export_border.grid_columnconfigure(0, weight=1)
        
        export_frame = tk.Frame(export_border, bg=BG_COLOR)
        export_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        
        chapters_label = tk.Label(export_frame, text=" Kapitel pro PDF:", bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 11))
        chapters_label.grid(row=0, column=0, sticky="w")
        
        chapters_help_icon = create_help_icon(export_frame, "pdf_merger", "chapters_per_pdf")
        chapters_help_icon.grid(row=0, column=1, padx=(2, 0))
        
        self.chapters_var = tk.StringVar(value="3")
        self.chapters_dd = create_dark_dropdown(export_frame, textvariable=self.chapters_var, values=[str(i) for i in range(2, 11)], width=6)
        self.chapters_dd.grid(row=0, column=2, sticky="w", padx=(8, 0))
        
        self.delete_originals_var = tk.BooleanVar(value=False)
        delete_checkbox = tk.Checkbutton(export_frame, text=" Original-PDFs löschen", variable=self.delete_originals_var, onvalue=True, offvalue=False, bg=BG_COLOR, fg=LABEL_FG, selectcolor=ENTRY_BG, activebackground=BG_COLOR, activeforeground=LABEL_FG, font=("Arial", 10))
        delete_checkbox.grid(row=1, column=0, sticky="w", pady=(8, 0))
        
        delete_help_icon = create_help_icon(export_frame, "pdf_merger", "delete_originals")
        delete_help_icon.grid(row=1, column=1, padx=(2, 0), pady=(8, 0))

        # Progress and status section
        run_border = tk.Frame(self.content, bg=BG_COLOR, highlightbackground=DOWNLOAD_BORDER_COLOR, highlightthickness=1, bd=0)
        run_border.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 6))
        run_border.grid_columnconfigure(0, weight=1)
        
        run_outer = tk.Frame(run_border, bg=BG_COLOR)
        run_outer.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        run_outer.grid_columnconfigure(0, weight=1)
        
        self.timer_var = tk.StringVar(value="Laufzeit: 00:00")
        tk.Label(run_outer, textvariable=self.timer_var, bg=BG_COLOR, fg=LABEL_FG, font=("Arial", 12, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        
        self.progress = create_progress_bar(run_outer, mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        
        self.status_var = tk.StringVar(value=" Bereit…")
        tk.Label(run_outer, textvariable=self.status_var, bg=BG_COLOR, fg=LABEL_FG).grid(row=2, column=0, sticky="w")
        
        # Initially hide progress/log area until merge starts
        self._run_outer = run_outer
        self._run_border = run_border
        self._run_border.grid_remove()

        # Button section
        self.btn_bar = tk.Frame(self.content, bg=BG_COLOR)
        self.btn_bar.grid(row=6, column=0, pady=(6, 10))
        
        self.btn_reset = create_button(self.btn_bar, " Reset", variant="reset", command=self._on_reset)
        self.btn_start = create_button(self.btn_bar, " Zusammenführen starten", variant="primary", command=self._on_start)
        self.btn_pause = create_button(self.btn_bar, " Pausieren", variant="pause", command=self._on_pause_resume)
        self.btn_stop = create_button(self.btn_bar, " Stoppen", variant="alert", command=self._on_stop)
        self.btn_restart = create_button(self.btn_bar, " Neue Zusammenführung starten", variant="primary", command=self._on_restart)

        # List visibility controller
        self._list_outer = list_outer
        
        # Initial state
        self._apply_state_idle()
        
        # Listen for context updates
        if self.context and hasattr(self.context, "register"):
            self.context.register(self._on_standard_dir_changed)

    def _start_timer(self) -> None:
        """Start the merge timer."""
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
            mm = elapsed // 60
            ss = elapsed % 60
            self.timer_var.set(f"Laufzeit: {mm:02d}:{ss:02d}")
            self.frame.after(1000, _tick)

        self.frame.after(1000, _tick)

    def _stop_timer(self) -> None:
        """Stop the merge timer."""
        self._timer_running = False

    def _pause_timer(self) -> None:
        """Pause the merge timer."""
        if not self._paused:
            return
        now_ts = __import__("time").time()
        if self._timer_pause_start <= 0:
            self._timer_pause_start = now_ts

    def _resume_timer(self) -> None:
        """Resume the merge timer."""
        if self._paused:
            return
        now_ts = __import__("time").time()
        if self._timer_pause_start > 0:
            self._timer_total_paused += now_ts - self._timer_pause_start
            self._timer_pause_start = 0.0

    # --- Helpers
    def _refresh_file_list(self) -> None:
        # Show/hide list container
        if self.selected_files:
            try:
                self._list_outer.grid()
            except Exception:
                pass
        else:
            try:
                self._list_outer.grid_remove()
            except Exception:
                pass
        # Rebuild tree
        for iid in self.file_tree.get_children():
            self.file_tree.delete(iid)
        for i, p in enumerate(self.selected_files, start=1):
            self.file_tree.insert("", "end", values=(i, os.path.basename(p), p))

    def _auto_fill_folder_from_files(self) -> None:
        if not self.selected_files:
            return
        # Bestimme gemeinsamen Oberordner aller ausgewählten Dateien
        try:
            dirs = [os.path.dirname(p) for p in self.selected_files]
            common_dir = os.path.commonpath(dirs) if dirs else ""
        except Exception:
            # z.B. unterschiedliche Laufwerke: Fallback auf Ordner der ersten Datei
            common_dir = os.path.dirname(self.selected_files[0])
        if not common_dir:
            common_dir = os.path.dirname(self.selected_files[0])
        # Zielordner automatisch auf den (gemeinsamen) Ursprungsordner setzen
        try:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, common_dir)
        except Exception:
            pass

    def _clear_entry_selection(self, entry: tk.Entry) -> None:
        try:
            entry.selection_clear()
        except Exception:
            pass
        try:
            entry.icursor(tk.END)
        except Exception:
            pass

    def _append_log(self, line: str) -> None:
        try:
            current = self.status_var.get().strip()
        except Exception:
            current = ""
        new_line = line.rstrip("\n")
        if current:
            display = f"{current}\n{new_line}"
        else:
            display = new_line
        try:
            self.status_var.set(display)
        except Exception:
            pass

    # --- States
    def _clear_btn_bar(self) -> None:
        for w in self.btn_bar.grid_slaves():
            w.grid_forget()

    def _apply_state_idle(self) -> None:
        self.state = "idle"
        self._clear_btn_bar()
        self.btn_reset.grid(row=0, column=0, padx=(0, 10)) # Buttons padding
        self.btn_start.grid(row=0, column=1)
        if merge_pdfs is None:
            self.btn_start.configure(state="disabled")
            self.status_var.set("❌ Merger nicht verfügbar")
        else:
            self.btn_start.configure(state="normal")
            self.status_var.set(" Bereit…")
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.timer_var.set("Laufzeit: 00:00")
        # hide progress/log area in idle state
        try:
            self._run_border.grid_remove()
        except Exception:
            pass

    def _apply_state_running(self) -> None:
        self.state = "running"
        self._clear_btn_bar()
        self.btn_pause.grid(row=0, column=0, padx=(0, 10)) # Buttons padding
        self.btn_stop.grid(row=0, column=1)
        try:
            # show progress/log area when run starts
            self._run_border.grid()
            self.progress.configure(mode="determinate", value=0)
        except Exception:
            pass

    def _apply_state_done(self) -> None:
        self.state = "done"
        self._clear_btn_bar()
        self.btn_restart.grid(row=0, column=0) # Buttons padding
        try:
            self.progress.stop()
            # auf 100% setzen
            self.progress.configure(mode="determinate", value=100)
        except Exception:
            pass

    # --- Buttons
    def _on_start(self) -> None:
        if merge_pdfs is None:
            messagebox.showerror("Fehlende Abhängigkeit", f"Merger-Logik nicht verfügbar: {IMPORT_ERROR_MERGER}")
            return
        folder = self.folder_entry.get().strip()
        if not folder:
            messagebox.showerror("Fehlende Eingabe", "Bitte Zielordner wählen.")
            return
        try:
            chapters = int(self.chapters_var.get())
        except Exception:
            messagebox.showerror("Fehleingabe", "Bitte gültige Kapitelanzahl (2–10) wählen.")
            return

        self._stop = False
        self._paused = False
        self._apply_state_running()
        self.status_var.set(" Starte Merge…")

        # Fortschritt x/y vorbereiten
        self._progress_done = 0
        # y = Anzahl ausgewählter Dateien (oder später aus Statusmeldung ermittelt)
        sel_files = [self.file_tree.item(i, "values")[2] for i in self.file_tree.get_children()]
        try:
            self._progress_total = max(1, len(sel_files))
        except Exception:
            self._progress_total = 1
        self._counted_outputs = set()

        def _update_progress_bar():
            try:
                total = max(1, int(self._progress_total))
                done = max(0, int(self._progress_done))
                pct = int(min(100, max(0, round(done * 100 / total))))
                self.progress.configure(value=pct)
            except Exception:
                pass
        self._update_progress_bar = _update_progress_bar  # store for inner closures

        self._start_timer()

        delete_originals = self.delete_originals_var.get()

        def worker():
            try:
                local_sel = [self.file_tree.item(i, "values")[2] for i in self.file_tree.get_children()]
                # Wrapper um Status, um Gesamtzahl/Done zu ermitteln
                import re as _re
                def _status(msg: str):
                    # direkt im UI-Thread setzen
                    try:
                        self.frame.after(0, self.status_var.set, msg)
                    except Exception:
                        pass
                    # Gesamtzahl aus "✅ N Kapitel-PDFs gefunden" parsen, wenn keine Auswahl getroffen wurde
                    if (not local_sel) and "Kapitel-PDFs gefunden" in msg:
                        try:
                            m = _re.search(r"✅\s+(\d+)\s+Kapitel-PDFs gefunden", msg)
                            if m:
                                new_total = int(m.group(1))
                                if new_total > 0:
                                    self._progress_total = new_total
                                    self.frame.after(0, self._update_progress_bar)
                        except Exception:
                            pass
                    # Wenn ein Output verarbeitet wird, prüfen ob Datei existiert und dann x++
                    if msg.startswith("⚙️ Verarbeite: "):
                        out_name = msg.split(": ", 1)[1].strip()
                        out_path = os.path.join(folder, out_name)
                        def _try_count():
                            try:
                                if os.path.exists(out_path):
                                    if out_path not in self._counted_outputs:
                                        self._counted_outputs.add(out_path)
                                        self._progress_done += 1
                                        self._update_progress_bar()
                                else:
                                    # später erneut versuchen (Datei wird unmittelbar nach Status geschrieben)
                                    self.frame.after(150, _try_count)
                            except Exception:
                                pass
                        self.frame.after(50, _try_count)
                
                # Pause-Loop vor dem Merge
                while self._paused and not self._stop:
                    __import__("time").sleep(0.1)
                
                if self._stop:
                    return
                
                merge_pdfs(
                    folder,
                    chapters,
                    _status,
                    selected_files=local_sel if local_sel else None,
                    use_session_manifest=False,
                    ignore_merged=False,
                )
                
                # Pause-Loop nach dem Merge
                while self._paused and not self._stop:
                    __import__("time").sleep(0.1)
                
                if self._stop:
                    return
                
                if delete_originals:
                    originals_dir = os.path.join(folder, "_originals")
                    if os.path.isdir(originals_dir):
                        try:
                            shutil.rmtree(originals_dir)
                            self.frame.after(0, lambda: self._append_log("🗑️ Original-PDFs gelöscht.\n"))
                        except Exception as cleanup_exc:  # pragma: no cover
                            self.frame.after(0, lambda: self._append_log(f"⚠️ Konnte Originale nicht löschen: {cleanup_exc}\n"))
                self.frame.after(0, self._finish_done)
            except Exception as e:  # pragma: no cover
                self.frame.after(0, lambda: self._append_log(f"❌ Fehler: {e}\n"))
                self.frame.after(0, self._finish_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_pause_resume(self) -> None:
        """Pausiert oder setzt den Merge-Prozess fort."""
        self._paused = not self._paused
        now_ts = __import__("time").time()
        if self._paused:
            self.status_var.set(" ⏸️ Pausiert")
            self._pause_timer()
            self.btn_pause.configure(text=" Fortsetzen")
        else:
            self.status_var.set(" ▶️ Fortgesetzt")
            self._resume_timer()
            self.btn_pause.configure(text=" Pausieren")

    def _on_stop(self) -> None:
        # Hinweis: merge_pdfs läuft synchron; ein harter Abbruch wird nicht erzwungen.
        self._stop = True
        self.status_var.set("⏹️ Stoppen angefordert… (wird nach aktuellem Schritt beendet)")

    def _on_reset(self) -> None:
        self.selected_files.clear()
        self._refresh_file_list()
        try:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, self.standard_dir_var.get())
        except Exception:
            pass
        self.chapters_var.set("3")
        self.status_var.set(" Bereit…")
        try:
            self.progress.stop()
            self.progress.configure(mode="indeterminate", value=0)
        except Exception:
            pass
        self.timer_var.set("Laufzeit: 00:00")
        try:
            self._run_border.grid_remove()
        except Exception:
            pass
        self._apply_state_idle()

    def _on_restart(self) -> None:
        self._on_reset()

    def _finish_done(self) -> None:
        self._stop_timer()
        self._apply_state_done()
        self.status_var.set("✅ Merge abgeschlossen")
        # finalize and show total runtime as requested
        try:
            now = __import__("time").time()
            elapsed = now - getattr(self, "_timer_start", now) - getattr(self, "_timer_total_paused", 0.0)
            if getattr(self, "_paused", False) and getattr(self, "_timer_pause_start", 0.0) > 0:
                elapsed -= (now - self._timer_pause_start)
            elapsed = int(max(0, elapsed))
            mm = elapsed // 60
            ss = elapsed % 60
            self.timer_var.set(f"Zusammenführung beendet in {mm:02d}:{ss:02d}")
        except Exception:
            pass

    def widget(self) -> tk.Frame:
        return self.frame

    # Context callback
    def _on_standard_dir_changed(self, new_dir: str) -> None:
        self.standard_dir_var.set(new_dir)
        self.standard_info_var.set(f"Standardordner: {new_dir}")
        try:
            current = self.folder_entry.get().strip()
        except Exception:
            current = ""
        if not current or current == "" or current == self.standard_dir_var.get():
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, new_dir)