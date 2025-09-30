"""
UI und Logik für die Einstellungen
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

from .components import create_flat_button, create_help_icon
from .theme import BG_COLOR, ENTRY_BG, ENTRY_FG, LABEL_FG
from core.utils import load_settings, save_settings


class SettingsPanel:
    """Panel für die Einstellungen"""

    def __init__(self, parent: tk.Widget, context: Optional[object] = None):
        """Initialisiert das Panel und stellt Standard-Download-Ordner ein."""
        self.parent = parent
        self.context = context
        self.frame = tk.Frame(parent, bg=BG_COLOR)
        self.frame.grid_columnconfigure(2, weight=1)

        # Load current settings
        data = load_settings() or {}
        default_dir = data.get("standard_dir", os.path.expanduser("~"))
        if self.context is not None and hasattr(self.context, "standard_dir"):
            try:
                default_dir = getattr(self.context, "standard_dir") or default_dir
            except Exception:
                pass
        self.standard_dir = default_dir
        if self.context is not None and hasattr(self.context, "register"):
            try:
                self.context.register(self._on_standard_dir_changed)
            except Exception:
                pass

        # Label
        tk.Label(
            self.frame,
            text=" Standard-Download-Ordner:",
            bg=BG_COLOR,
            fg=LABEL_FG,
            font=("Arial", 12),
        ).grid(row=0, column=0, sticky="w", padx=(10, 10), pady=(12, 8))

        # Entry
        self.dir_entry = tk.Entry(
            self.frame,
            bg=ENTRY_BG,
            fg=ENTRY_FG,
            insertbackground=ENTRY_FG,
            relief="flat",
            bd=5,
            font=("Arial", 10),
        )
        self.dir_entry.grid(row=0, column=2, sticky="ew", padx=(0, 10), pady=(12, 8))
        self.dir_entry.insert(0, self.standard_dir)
        # Auswahl bei Fokus entfernen und Cursor ans Ende setzen
        try:
            self.dir_entry.bind("<FocusIn>", lambda e: self._clear_entry_selection(self.dir_entry))
        except Exception:
            pass
        # Beim Öffnen den Fokus vom Entry wegnehmen, damit nichts markiert ist
        try:
            self.frame.after_idle(lambda: self.frame.focus_set())
        except Exception:
            pass

        # Browse
        def browse_folder():
            sel = filedialog.askdirectory()
            if sel:
                self.dir_entry.delete(0, tk.END)
                self.dir_entry.insert(0, sel)

        create_flat_button(self.frame, " Browse", command=browse_folder).grid(
            row=0, column=3, padx=(0, 10), pady=(12, 8)
        )
        dir_help_icon = create_help_icon(self.frame, "settings", "dir_entry")
        dir_help_icon.grid(row=0, column=4, padx=(2, 15), pady=(12, 8))  # Standartordner Icon padding

        # Qualitäts Einstellungen (eingerahmt)
        # Geladene Settings (bereits oben in data vorhanden)
        q_frame = tk.LabelFrame(self.frame, text=" Qualitäts Einstellungen ", bg=BG_COLOR, fg=LABEL_FG, bd=2, relief="groove")
        q_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(4, 10))
        try:
            q_frame.grid_columnconfigure(0, weight=0)  # Label
            q_frame.grid_columnconfigure(1, weight=0)  # Icon
            q_frame.grid_columnconfigure(2, weight=1)  # Input field
        except Exception:
            pass

        # Variablen mit Defaults
        self.var_jpeg_quality = tk.IntVar(value=int(data.get("jpeg_quality", 75)))
        self.var_progressive = tk.BooleanVar(value=bool(data.get("jpeg_progressive", True)))
        self.var_max_width = tk.IntVar(value=int(data.get("max_width", 1200)))
        self.var_grayscale = tk.BooleanVar(value=bool(data.get("grayscale", False)))

        # Reihe 0: JPEG Qualität
        quality_label = tk.Label(q_frame, text="JPEG Qualität (1-100):", bg=BG_COLOR, fg=LABEL_FG)
        quality_label.grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(8, 4)) # JPEG Qualität Label padding
        quality_help_icon = create_help_icon(q_frame, "settings", "jpeg_quality")
        quality_help_icon.grid(row=0, column=1, padx=(2, 5), pady=(8, 4)) # JPEG Qualität Icon padding
        self.quality_spin = tk.Spinbox(q_frame, from_=1, to=100, textvariable=self.var_jpeg_quality, width=6, bg=ENTRY_BG, fg=ENTRY_FG)
        self.quality_spin.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=(8, 4)) # JPEG Qualität Input field padding

        # Reihe 1: Progressive
        self.chk_progressive = tk.Checkbutton(q_frame, text=" Progressive JPEG", variable=self.var_progressive, bg=BG_COLOR, fg=LABEL_FG, activebackground=BG_COLOR, activeforeground=LABEL_FG, selectcolor=BG_COLOR)
        self.chk_progressive.grid(row=1, column=0, sticky="w", padx=(10, 6), pady=(4, 4)) # Progressive JPEG Checkbox padding
        progressive_help_icon = create_help_icon(q_frame, "settings", "progressive_jpeg")
        progressive_help_icon.grid(row=1, column=1, padx=(2, 0), pady=(4, 4)) # Progressive JPEG Icon padding

        # Reihe 2: Graustufen
        self.chk_grayscale = tk.Checkbutton(q_frame, text=" S/W Bilder (Graustufen)", variable=self.var_grayscale, bg=BG_COLOR, fg=LABEL_FG, activebackground=BG_COLOR, activeforeground=LABEL_FG, selectcolor=BG_COLOR)
        self.chk_grayscale.grid(row=2, column=0, sticky="w", padx=(10, 6), pady=(4, 4))
        grayscale_help_icon = create_help_icon(q_frame, "settings", "grayscale")
        grayscale_help_icon.grid(row=2, column=1, padx=(2, 0), pady=(4, 4))

        # Reihe 3: Max Breite
        max_width_label = tk.Label(q_frame, text=" Max. Bildbreite (px):", bg=BG_COLOR, fg=LABEL_FG)
        max_width_label.grid(row=3, column=0, sticky="w", padx=(10, 6), pady=(4, 10)) # Max. Bildbreite Label padding
        max_width_help_icon = create_help_icon(q_frame, "settings", "max_width")
        max_width_help_icon.grid(row=3, column=1, padx=(2, 5), pady=(4, 10)) # Max. Bildbreite Icon padding
        self.maxw_entry = tk.Spinbox(q_frame, from_=320, to=10000, increment=10, textvariable=self.var_max_width, width=8, bg=ENTRY_BG, fg=ENTRY_FG)
        self.maxw_entry.grid(row=3, column=2, sticky="w", padx=(0, 10), pady=(4, 10)) # Max. Bildbreite Input field padding

        # Status label
        self.status = tk.Label(self.frame, text="", bg=BG_COLOR, fg=LABEL_FG, anchor="w")
        self.status.grid(row=3, column=0, columnspan=5, sticky="ew", padx=10, pady=(4, 10)) # Status label padding

        # Save button
        def save():
            new_dir = self.dir_entry.get().strip()
            if not new_dir:
                messagebox.showerror("Ungültiger Ordner", "Bitte einen gültigen Ordnerpfad angeben.")
                return
            try:
                os.makedirs(new_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Ordnerfehler", f"Ordner konnte nicht erstellt werden:\n{e}")
                return
            data = load_settings() or {}
            data["standard_dir"] = new_dir
            # Qualitäts-Settings speichern
            try:
                data["jpeg_quality"] = int(self.var_jpeg_quality.get())
            except Exception:
                data["jpeg_quality"] = 75
            try:
                data["jpeg_progressive"] = bool(self.var_progressive.get())
            except Exception:
                data["jpeg_progressive"] = True
            try:
                data["max_width"] = int(self.var_max_width.get())
            except Exception:
                data["max_width"] = 1200
            try:
                data["grayscale"] = bool(self.var_grayscale.get())
            except Exception:
                data["grayscale"] = False
            save_settings(data)
            self.standard_dir = new_dir
            if self.context is not None and hasattr(self.context, "update_standard_dir"):
                try:
                    self.context.update_standard_dir(new_dir)
                except Exception:
                    pass
            self.status.config(text="✅ Standardordner gespeichert")
            if getattr(self, "_status_reset_after_id", None):
                try:
                    self.frame.after_cancel(self._status_reset_after_id)
                except Exception:
                    pass
            # Sekunden bis der Text "Standardordner gespeichert" verschwindet
            self._status_reset_after_id = self.frame.after(3000, lambda: self.status.config(text=""))
        create_flat_button(self.frame, " Speichern", command=save).grid(
            row=2, column=0, columnspan=5, sticky="", pady=(5, 5)
        )

    def _clear_entry_selection(self, entry: tk.Entry) -> None:
        try:
            entry.selection_clear()
        except Exception:
            pass
        try:
            entry.icursor(tk.END)
        except Exception:
            pass

    def widget(self) -> tk.Frame:
        return self.frame

    def _on_standard_dir_changed(self, new_dir: str) -> None:
        self.standard_dir = new_dir
        try:
            current = self.dir_entry.get().strip()
        except Exception:
            current = ""
        if not current or current == new_dir:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, new_dir)