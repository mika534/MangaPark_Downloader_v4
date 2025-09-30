"""Wiederverwendbare UI-Komponenten."""

from typing import Callable, Optional, Dict, Any
import os
import re
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from .theme import (
    BG_COLOR,
    ENTRY_BG,
    ENTRY_FG,
    BUTTON_BG,
    BUTTON_FG,
    LABEL_FG,
    DETAIL_BORDER_COLOR,
    STYLE_BUTTON_PRIMARY,
    STYLE_BUTTON_ALERT,
    STYLE_BUTTON_RESET,
    STYLE_PROGRESSBAR,
    STYLE_BUTTON_PAUSE,
    STYLE_BUTTON_SKIP,
    STYLE_BUTTON_SMALL,
    STYLE_BUTTON_SMALL_ALERT,
    SCROLLBAR_WIDTH,
    SCROLLBAR_TRACK_COLOR,
    SCROLLBAR_THUMB_COLOR,
    SCROLLBAR_THUMB_HOVER,
    TOOLTIP_BG,
    TOOLTIP_FG,
    TOOLTIP_BORDER,
    TOOLTIP_PADX,
    TOOLTIP_PADY,
    TOOLTIP_DURATION,
    # Neue Farben
    HELP_ICON_FG,
    HELP_ICON_HOVER_FG,
    HELP_ICON_HOVER_BG,
    DROPDOWN_BG,
    DROPDOWN_FG,
    DROPDOWN_BORDER,
    DROPDOWN_HOVER,
    BUTTON_PRIMARY_HOVER,
)

# Import für Tooltip-Texte
try:
    from core.helper import TOOLTIP_TEXTS
except ImportError:
    TOOLTIP_TEXTS = {}

# Optionaler Import von customtkinter
try:
    import customtkinter as ctk  # type: ignore
except Exception:  # pragma: no cover
    ctk = None  # type: ignore


class Tooltip:
    """Einfache Tooltip-Klasse für UI-Elemente."""
    
    def __init__(self, widget: tk.Widget, text: str, duration: int = TOOLTIP_DURATION):
        """
        Erstellt einen Tooltip für ein Widget.
        
        Args:
            widget: Das Widget für das der Tooltip angezeigt werden soll
            text: Der Tooltip-Text
            duration: Anzeigedauer in Millisekunden (Standard: 2 Sekunden)
        """
        self.widget = widget
        self.text = text
        self.duration = duration
        self.tooltip_window = None
        self.hide_after_id = None
        
        # Bind Click Event
        self.widget.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        """Click Event - zeigt Tooltip für 2 Sekunden an."""
        self._hide_tooltip()  # Verstecke vorherigen Tooltip falls vorhanden
        self._show_tooltip()
        # Timer für automatisches Verstecken nach 2 Sekunden
        self.hide_after_id = self.widget.after(self.duration, self._hide_tooltip)
    
    def _cancel_timer(self):
        """Bricht den Hide-Timer ab."""
        if self.hide_after_id:
            self.widget.after_cancel(self.hide_after_id)
            self.hide_after_id = None
    
    def _show_tooltip(self):
        """Zeigt den Tooltip an."""
        if self.tooltip_window or not self.text:
            return
        
        # Finde das Hauptfenster (root)
        root = self.widget.winfo_toplevel()
        
        # Tooltip-Fenster erstellen
        self.tooltip_window = tk.Toplevel(root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)
        
        # Tooltip schließen wenn Hauptfenster geschlossen wird
        def on_root_close():
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None
        
        root.bind("<Destroy>", lambda e: on_root_close())
        
        # Tooltip-Inhalt
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            bg=TOOLTIP_BG,
            fg=TOOLTIP_FG,
            font=("Arial", 9),
            relief="solid",
            borderwidth=1,
            padx=TOOLTIP_PADX,
            pady=TOOLTIP_PADY,
            wraplength=300,
            justify="left",
            highlightthickness=1,
            highlightbackground=TOOLTIP_BORDER
        )
        label.pack()
        
        # Position berechnen
        self._position_tooltip()
    
    def _position_tooltip(self):
        """Positioniert den Tooltip neben der Maus."""
        if not self.tooltip_window:
            return
        
        # Widget-Position im Bildschirm
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() - 30
        
        # Tooltip-Größe
        self.tooltip_window.update_idletasks()
        width = self.tooltip_window.winfo_width()
        height = self.tooltip_window.winfo_height()
        
        # Bildschirm-Grenzen prüfen
        root = self.widget.winfo_toplevel()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Position anpassen falls Tooltip außerhalb des Bildschirms wäre
        if x + width > screen_width:
            x = screen_width - width - 10
        if y < 0:
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        if y + height > screen_height:
            y = screen_height - height - 10
        
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def _hide_tooltip(self):
        """Versteckt den Tooltip."""
        self._cancel_timer()
        
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget: tk.Widget, panel: str, element: str) -> Optional[Tooltip]:
    """
    Erstellt einen Tooltip für ein Widget basierend auf Panel und Element-Name.
    
    Args:
        widget: Das Widget für das der Tooltip erstellt werden soll
        panel: Der Panel-Name (z.B. "single_downloader", "bulk_downloader")
        element: Der Element-Name (z.B. "url_entry", "start_button")
    
    Returns:
        Tooltip-Objekt oder None falls kein Text gefunden wurde
    """
    try:
        text = TOOLTIP_TEXTS.get(panel, {}).get(element)
        if text:
            return Tooltip(widget, text)
    except Exception:
        pass
    return None


def add_tooltip_to_widget(widget: tk.Widget, panel: str, element: str) -> None:
    """
    Fügt einem Widget einen Tooltip hinzu (einfache Hilfsfunktion).
    
    Args:
        widget: Das Widget dem der Tooltip hinzugefügt werden soll
        panel: Der Panel-Name
        element: Der Element-Name
    """
    create_tooltip(widget, panel, element)


def create_dark_dropdown(parent: tk.Widget, textvariable: tk.StringVar, values: list, width: int = 6) -> ctk.CTkComboBox:
    """Erstellt ein Dark Mode Dropdown mit CustomTkinter."""
    dropdown = ctk.CTkComboBox(
        parent,
        variable=textvariable,
        values=values,
        width=width * 10,  # CustomTkinter verwendet andere Einheiten
        height=28,
        corner_radius=6,
        border_width=1,
        button_color=DROPDOWN_BG,
        button_hover_color=DROPDOWN_HOVER,
        dropdown_hover_color=DROPDOWN_HOVER,
        dropdown_text_color=DROPDOWN_FG,
        text_color=DROPDOWN_FG,
        fg_color=DROPDOWN_BG,
        border_color=DROPDOWN_BORDER,
        state="readonly"
    )
    return dropdown


def create_help_icon(parent: tk.Widget, panel: str, element: str, position: str = "right") -> tk.Label:
    """
    Erstellt ein Fragezeichen-Icon mit Tooltip.
    
    Args:
        parent: Das Parent-Widget
        panel: Der Panel-Name für den Tooltip
        element: Der Element-Name für den Tooltip
        position: Position relativ zum Parent ("right", "left", "top", "bottom")
    
    Returns:
        Das Fragezeichen-Label-Widget
    """
    help_icon = tk.Label(
        parent,
        text="?",
        bg=BG_COLOR,
        fg=HELP_ICON_FG,
        font=("Arial", 10, "bold"),
        cursor="hand2",
        relief="flat",
        bd=0,
        padx=2,
        pady=1
    )
    
    # Tooltip für das Icon erstellen
    create_tooltip(help_icon, panel, element)
    
    # Hover-Effekt
    def on_enter(event):
        help_icon.configure(fg=HELP_ICON_HOVER_FG, bg=HELP_ICON_HOVER_BG)
    
    def on_leave(event):
        help_icon.configure(fg=HELP_ICON_FG, bg=BG_COLOR)
    
    help_icon.bind("<Enter>", on_enter)
    help_icon.bind("<Leave>", on_leave)
    
    return help_icon


def add_help_icon_to_widget(widget: tk.Widget, panel: str, element: str, position: str = "right") -> tk.Label:
    """
    Fügt einem Widget ein Fragezeichen-Icon hinzu.
    
    Args:
        widget: Das Widget neben dem das Icon erscheinen soll
        panel: Der Panel-Name für den Tooltip
        element: Der Element-Name für den Tooltip
        position: Position relativ zum Widget
    
    Returns:
        Das Fragezeichen-Icon
    """
    return create_help_icon(widget.master, panel, element, position)


def create_button(
    parent: tk.Widget,
    text: str,
    variant: str = "primary",
    command: Optional[Callable[[], None]] = None,
) -> ttk.Button:
    """Erstellt einen standardisierten ttk-Button mit Style-Variante.

    Varianten:
    - primary (Start/Bestätigen)
    - alert   (Pause/Stop/Überspringen)
    - reset   (Zurücksetzen)
    """
    style_name = {
        "primary": STYLE_BUTTON_PRIMARY,
        "alert": STYLE_BUTTON_ALERT,
        "reset": STYLE_BUTTON_RESET,
        "pause": STYLE_BUTTON_PAUSE,
        "skip": STYLE_BUTTON_SKIP,
        "small": STYLE_BUTTON_SMALL,
        "small-alert": STYLE_BUTTON_SMALL_ALERT,
    }.get(variant, STYLE_BUTTON_PRIMARY)
    return ttk.Button(parent, text=text, command=command, style=style_name)


def create_flat_button(
    parent: tk.Widget,
    text: str,
    command: Optional[Callable[[], None]] = None,
) -> tk.Button:
    """Erstellt einen flachen Button im dunklen Stil (wie "Browse")."""
    return tk.Button(
        parent,
        text=text,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        relief="flat",
        bd=0,
        font=("Arial", 10, "bold"),
        activebackground=BUTTON_PRIMARY_HOVER,
        activeforeground=BUTTON_FG,
        command=command,
    )


def create_progress_bar(parent: tk.Widget, mode: str = "determinate") -> ttk.Progressbar:
    """Erstellt eine standardisierte Progressbar (ttk)."""
    return ttk.Progressbar(parent, mode=mode, style=STYLE_PROGRESSBAR)


def create_scrollbar(
    parent: tk.Widget,
    orient: str = "vertical",
    command: Optional[Callable] = None,
):
    """Erstellt einen Custom-Scrollbar.

    Bevorzugt customtkinter (voll konfigurierbare Farben/Breite). Fällt auf ttk.Scrollbar zurück,
    falls customtkinter nicht verfügbar ist.
    """
    if ctk is not None:
        try:
            sb = ctk.CTkScrollbar(
                parent,
                orientation=orient,
                width=int(SCROLLBAR_WIDTH),
                fg_color=SCROLLBAR_TRACK_COLOR,
                button_color=SCROLLBAR_THUMB_COLOR,
                button_hover_color=SCROLLBAR_THUMB_HOVER,
                command=command,
            )
            return sb
        except Exception:
            pass
    # Fallback (eingeschränkte Styling-Möglichkeiten)
    return ttk.Scrollbar(parent, orient=orient, command=command)


def create_detail_editor(
    parent: tk.Widget,
    standard_dir: str,
    browse_command: Optional[Callable[[], Optional[str]]] = None,
    url_entry: Optional[tk.Entry] = None,
) -> Dict[str, Any]:
    """Erstellt den Detail-Editor mit Titel-, Ordner- und Download-Einstellungen."""

    outer_frame = tk.Frame(
        parent,
        bg=BG_COLOR,
        highlightbackground=DETAIL_BORDER_COLOR,
        highlightthickness=1,
        bd=0,
    )
    outer_frame.grid_columnconfigure(0, weight=1)

    frame = tk.Frame(outer_frame, bg=BG_COLOR)
    frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    frame.grid_columnconfigure(1, weight=1)

    standard_dir_var = tk.StringVar(value=standard_dir)
    standard_info_var = tk.StringVar(value=f"Standardordner: {standard_dir}")

    # Abschnitt: Manga-Titel
    title_label = tk.Label(
        frame,
        text="Manga-Titel:",
        bg=BG_COLOR,
        fg=LABEL_FG,
        anchor="w",
        font=("Arial", 12),
    )
    title_label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6))

    title_entry = tk.Entry(
        frame,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        relief="flat",
        bd=5,
        font=("Arial", 10),
    )
    title_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 6))

    # Abschnitt: Zielordner + Browse
    folder_label = tk.Label(
        frame,
        text="Zielordner:",
        bg=BG_COLOR,
        fg=LABEL_FG,
        anchor="w",
        font=("Arial", 12),
    )
    folder_label.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(0, 6))

    # Folder handling: keep empty unless URL-autofill or Browse explicitly fills it
    folder_var = tk.StringVar(value="")
    _folder_guard_set = {"active": False}  # reentrancy/allowance guard
    _folder_url_autofilled = {"done": False}

    def _folder_trace(*_args):
        # Prevent plain standard-dir writes before URL autofill/browse
        if _folder_guard_set["active"]:
            return
        try:
            new_val = folder_var.get().strip()
            std_val = standard_dir_var.get().strip()
            url_val = url_entry.get().strip() if url_entry is not None else ""
            title_val = title_entry.get().strip()
        except Exception:
            return
        if not _folder_url_autofilled["done"] and new_val == std_val and not url_val and not title_val:
            # Block this assignment: revert to empty until URL autofill happens
            _folder_guard_set["active"] = True
            try:
                folder_var.set("")
            finally:
                _folder_guard_set["active"] = False

    folder_var.trace_add("write", lambda *a: _folder_trace())

    folder_entry = tk.Entry(
        frame,
        textvariable=folder_var,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        relief="flat",
        bd=5,
        font=("Arial", 10),
    )
    folder_entry.grid(row=1, column=1, sticky="ew", pady=(0, 6))
    # Do not prefill here; will be filled by URL-autofill (or Browse) after URL is provided

    standard_label = tk.Label(
        frame,
        textvariable=standard_info_var,
        bg=BG_COLOR,
        fg=LABEL_FG,
        anchor="w",
        font=("Arial", 9),
    )
    standard_label.grid(
    row=2,
    column=0,
    columnspan=3,
    sticky="w",
    padx=(100, 0),   # <-- linker/rechter Abstand
    pady=(0, 10),
    )

    def _on_browse() -> None:
        if browse_command is None:
            return
        selected = browse_command()
        if selected:
            _folder_guard_set["active"] = True
            try:
                folder_var.set(selected)
                _folder_url_autofilled["done"] = True
            finally:
                _folder_guard_set["active"] = False

    browse_btn = create_flat_button(frame, "Browse", command=_on_browse)
    browse_btn.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(0, 6))

    # Download-Modus
    mode_frame = tk.LabelFrame(
        frame,
        text="Download-Modus",
        bg=BG_COLOR,
        fg=LABEL_FG,
        bd=1,
        relief="solid",
        font=("Arial", 10, "bold"),
        labelanchor="nw",
    )
    mode_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 10))
    mode_frame.grid_columnconfigure(0, weight=0)  # Checkboxen sollen nicht expandieren
    mode_frame.grid_columnconfigure(1, weight=0)  # Icons sollen nicht expandieren
    mode_frame.grid_columnconfigure(2, weight=1)  # Entry soll expandieren

    manual_var = tk.BooleanVar(value=True)
    auto_var = tk.BooleanVar(value=False)
    manual_count_var = tk.StringVar(value="5")

    def _set_manual():
        if manual_var.get():
            auto_var.set(False)
        else:
            auto_var.set(True)

    def _set_auto():
        if auto_var.get():
            manual_var.set(False)
        else:
            manual_var.set(True)

    manual_check = tk.Checkbutton(
        mode_frame,
        text="Manuell",
        variable=manual_var,
        onvalue=True,
        offvalue=False,
        command=_set_manual,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    manual_check.grid(row=0, column=0, sticky="w", padx=10, pady=(6, 4))
    
    # Fragezeichen-Icon für Manual-Mode Checkbox hinzufügen
    manual_help_icon = create_help_icon(mode_frame, "single_downloader", "manual_mode")
    manual_help_icon.grid(row=0, column=1, padx=(2, 0), pady=(6, 4))

    manual_entry = tk.Entry(
        mode_frame,
        textvariable=manual_count_var,
        width=8,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        relief="flat",
        bd=3,
        font=("Arial", 10),
    )
    manual_entry.grid(row=0, column=2, sticky="w", padx=(8, 0), pady=(6, 4))

    auto_check = tk.Checkbutton(
        mode_frame,
        text="Automatisch",
        variable=auto_var,
        onvalue=True,
        offvalue=False,
        command=_set_auto,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    auto_check.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
    
    # Fragezeichen-Icon für Auto-Mode Checkbox hinzufügen
    auto_help_icon = create_help_icon(mode_frame, "single_downloader", "auto_mode")
    auto_help_icon.grid(row=1, column=1, padx=(2, 0), pady=(0, 6))

    # Erweiterte Funktionen
    advanced_frame = tk.LabelFrame(
        frame,
        text="Erweiterte Funktionen",
        bg=BG_COLOR,
        fg=LABEL_FG,
        bd=1,
        relief="solid",
        font=("Arial", 10, "bold"),
        labelanchor="nw",
    )
    advanced_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
    advanced_frame.grid_columnconfigure(0, weight=0)  # Checkboxen sollen nicht expandieren
    advanced_frame.grid_columnconfigure(1, weight=0)  # Icons sollen nicht expandieren

    merge_var = tk.BooleanVar(value=False)
    delete_originals_var = tk.BooleanVar(value=False)
    only_new_manifest_var = tk.BooleanVar(value=False)
    delete_images_var = tk.BooleanVar(value=False)
    merge_chapters_var = tk.StringVar(value="3")

    merge_check = tk.Checkbutton(
        advanced_frame,
        text="PDFs zusammenführen",
        variable=merge_var,
        onvalue=True,
        offvalue=False,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    merge_check.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
    
    # Fragezeichen-Icon für Merge-Checkbox hinzufügen
    merge_help_icon = create_help_icon(advanced_frame, "single_downloader", "merge_after")
    merge_help_icon.grid(row=0, column=1, padx=(2, 0), pady=(8, 4))

    merge_opts = tk.Frame(advanced_frame, bg=BG_COLOR)
    merge_opts.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(30, 10), pady=(0, 8))
    merge_opts.grid_columnconfigure(0, weight=0)  # Checkboxen sollen nicht expandieren
    merge_opts.grid_columnconfigure(1, weight=0)  # Icons sollen nicht expandieren

    chapters_label = tk.Label(
        merge_opts,
        text="Kapitel pro PDF:",
        bg=BG_COLOR,
        fg=LABEL_FG,
        font=("Arial", 10),
    )
    chapters_label.grid(row=0, column=0, sticky="w")
    
    chapters_help_icon = create_help_icon(merge_opts, "single_downloader", "merge_chapters")
    chapters_help_icon.grid(row=0, column=1, padx=(2, 0))

    chapters_dropdown = create_dark_dropdown(
        merge_opts,
        textvariable=merge_chapters_var,
        values=[str(i) for i in range(2, 11)],
        width=5,
    )
    chapters_dropdown.grid(row=0, column=2, sticky="w", padx=(8, 0))

    delete_originals_check = tk.Checkbutton(
        merge_opts,
        text="Original-PDFs löschen",
        variable=delete_originals_var,
        onvalue=True,
        offvalue=False,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    delete_originals_check.grid(row=1, column=0, sticky="w", pady=(6, 0))
    
    # Fragezeichen-Icon für Delete-Originals Checkbox hinzufügen
    delete_originals_help_icon = create_help_icon(merge_opts, "single_downloader", "delete_originals")
    delete_originals_help_icon.grid(row=1, column=1, padx=(2, 0), pady=(6, 0))

    only_new_manifest_check = tk.Checkbutton(
        merge_opts,
        text="Nur neue PDFs zusammenführen",
        variable=only_new_manifest_var,
        onvalue=True,
        offvalue=False,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    only_new_manifest_check.grid(row=2, column=0, sticky="w", pady=(4, 0))
    
    # Fragezeichen-Icon für Only-New-Manifest Checkbox hinzufügen
    only_new_manifest_help_icon = create_help_icon(merge_opts, "single_downloader", "only_new_manifest")
    only_new_manifest_help_icon.grid(row=2, column=1, padx=(2, 0), pady=(4, 0))

    def _toggle_merge_opts() -> None:
        if merge_var.get():
            merge_opts.grid()
        else:
            merge_opts.grid_remove()

    merge_check.configure(command=_toggle_merge_opts)
    merge_opts.grid_remove()

    delete_images_check = tk.Checkbutton(
        advanced_frame,
        text="Bilder löschen",
        variable=delete_images_var,
        onvalue=True,
        offvalue=False,
        bg=BG_COLOR,
        fg=LABEL_FG,
        selectcolor=ENTRY_BG,
        activebackground=BG_COLOR,
        activeforeground=LABEL_FG,
        font=("Arial", 10),
    )
    delete_images_check.grid(row=2, column=0, sticky="w", padx=10, pady=(4, 10))
    
    # Fragezeichen-Icon für Delete-Images Checkbox hinzufügen
    delete_images_help_icon = create_help_icon(advanced_frame, "single_downloader", "delete_images")
    delete_images_help_icon.grid(row=2, column=1, padx=(2, 0), pady=(4, 10))

    # Auto-Fill binden, falls URL-Feld vorhanden ist
    if url_entry is not None:
        def _mark_url_autofilled():
            _folder_url_autofilled["done"] = True
        bind_detail_editor_autofill(url_entry, title_entry, folder_entry, standard_dir_var, _mark_url_autofilled)

    return {
        "frame": outer_frame,
        "content_frame": frame,
        "title_entry": title_entry,
        "folder_entry": folder_entry,
        "manual_var": manual_var,
        "manual_count_var": manual_count_var,
        "auto_var": auto_var,
        "merge_var": merge_var,
        "merge_chapters_var": merge_chapters_var,
        "delete_originals_var": delete_originals_var,
        "only_new_manifest_var": only_new_manifest_var,
        "delete_images_var": delete_images_var,
        "merge_opts_frame": merge_opts,
        "standard_dir_var": standard_dir_var,
        "standard_info_var": standard_info_var,
        "standard_label": standard_label,
    }


def create_header(
    parent: tk.Widget,
    title_text: str,
    link_text: str,
    link_callback: Optional[Callable[[tk.Event], None]] = None,
) -> tk.Frame:
    """Erstellt den Header mit Logo, Titel und optionalem Link."""
    header = tk.Frame(parent, bg=BG_COLOR)
    header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    header.columnconfigure(0, weight=0)  # Logo - feste Breite
    header.columnconfigure(1, weight=1)   # Zentrierter Bereich
    header.columnconfigure(2, weight=0)  # Rechter Bereich (falls nötig)

    # Logo links
    logo_path = os.path.join(os.path.dirname(__file__), "MPD_Logo_W.png")
    if os.path.exists(logo_path):
        try:
            from PIL import Image, ImageTk
            # Logo laden und auf passende Größe skalieren
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((60, 60), Image.Resampling.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_image)
            
            logo_lbl = tk.Label(
                header,
                image=logo_photo,
                bg=BG_COLOR,
            )
            logo_lbl.image = logo_photo  # Referenz halten
            logo_lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))
        except ImportError:
            # Fallback falls PIL nicht verfügbar ist
            logo_lbl = tk.Label(
                header,
                text="MP",
                bg=BG_COLOR,
                fg=BUTTON_FG,
                font=("Arial", 24, "bold"),
            )
            logo_lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))
        except Exception:
            # Fallback bei anderen Fehlern
            logo_lbl = tk.Label(
                header,
                text="MP",
                bg=BG_COLOR,
                fg=BUTTON_FG,
                font=("Arial", 24, "bold"),
            )
            logo_lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))
    else:
        # Fallback falls Logo-Datei nicht existiert
        logo_lbl = tk.Label(
            header,
            text="MP",
            bg=BG_COLOR,
            fg=BUTTON_FG,
            font=("Arial", 24, "bold"),
        )
        logo_lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 15))

    # Titel zentriert
    title_lbl = tk.Label(
        header,
        text=title_text,
        bg=BG_COLOR,
        fg=BUTTON_FG,
        font=("Arial", 18, "bold"),
    )
    title_lbl.grid(row=0, column=1, pady=(0, 4))

    # Link zentriert
    if link_text:
        link_lbl = tk.Label(
            header,
            text=link_text,
            bg=BG_COLOR,
            fg=BUTTON_BG,
            font=("Arial", 10, "underline"),
            cursor="hand2",
        )
        link_lbl.grid(row=1, column=1)
        if link_callback is not None:
            link_lbl.bind("<Button-1>", link_callback)

    return header


def create_footer(parent: tk.Widget, info_text: str) -> tk.Frame:
    """Erstellt den Footer mit Info-Text."""
    footer = tk.Frame(parent, bg=BG_COLOR)
    footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
    footer.columnconfigure(0, weight=1)

    info = tk.Label(
        footer,
        text=info_text,
        bg=BG_COLOR,
        fg=LABEL_FG,
        font=("Arial", 9),
    )
    info.grid(row=0, column=0)

    return footer


def extract_title_from_url(url: str) -> str:
    """Extrahiert den Titel aus einer MangaPark-URL."""
    try:
        match = re.search(r"/title/(\d+-[a-z]{2}-[^/]+)", url)
        if not match:
            return ""
        slug = match.group(1)
        slug = re.sub(r"^\d+-", "", slug)
        slug = re.sub(r"^[a-z]{2}-", "", slug)
        title = slug.replace("-", " ").title()
        return title
    except Exception:
        return ""


def suggest_output_folder(standard_dir: str, title: str) -> str:
    """Erstellt einen Ausgabeordner basierend auf dem Standardpfad und dem Titel."""
    if not title:
        return standard_dir
    safe_title = title.strip()
    return os.path.join(standard_dir, safe_title)


def bind_detail_editor_autofill(
    url_entry: tk.Entry,
    title_entry: tk.Entry,
    folder_entry: tk.Entry,
    standard_dir_var: tk.StringVar,
    on_autofill: Optional[Callable[[], None]] = None,
) -> None:
    """Bindet Auto-Fill für Titel und Zielordner an das URL-Feld."""

    def _update(_event=None):
        url = url_entry.get().strip()
        title = extract_title_from_url(url)
        if not title:
            return

        current_title = title_entry.get().strip()
        if not current_title:
            title_entry.delete(0, tk.END)
            title_entry.insert(0, title)

        current_folder = folder_entry.get().strip()
        base_dir = standard_dir_var.get()
        suggested = suggest_output_folder(base_dir, title)
        if not current_folder or current_folder.startswith(base_dir):
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, suggested)
            if on_autofill is not None:
                try:
                    on_autofill()
                except Exception:
                    pass

    url_entry.bind("<KeyRelease>", _update)
    url_entry.bind("<FocusOut>", _update)
