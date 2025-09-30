"""
Theme-Definitionen für die GUI
"""

# =============================================================================
# GRUNDFARBEN - Hauptfarben des dunklen Themes
# =============================================================================

# Hauptfarben
BG_COLOR = "#1e2124"           # Haupt-Hintergrund (Fenster, Panels)
ENTRY_BG = "#2f3136"           # Eingabefelder, Dropdowns, Checkboxen
ENTRY_FG = "#ffffff"           # Text in Eingabefeldern
LABEL_FG = "#b9bbbe"           # Standard-Label-Text
FRAME_BG = "#36393f"           # Rahmen-Hintergrund (Tabs, Gruppen)

# =============================================================================
# BUTTON-FARBEN - Verschiedene Button-Varianten
# =============================================================================

# Standard-Button-Farben
BUTTON_BG = "#7289da"          # Primär-Button (Start, Bestätigen)
BUTTON_FG = "#ffffff"          # Button-Text

# Button-Varianten (werden in setup_ttk_styles() definiert)
BUTTON_PRIMARY_BG = "#7289da"      # Primär-Button (Start/Bestätigen)
BUTTON_PRIMARY_HOVER = "#879ce8"   # Primär-Button Hover
BUTTON_PRIMARY_DISABLED = "#4d5a83" # Primär-Button deaktiviert

BUTTON_ALERT_BG = "#dc3545"        # Alert-Button (Stop/Fehler) - Rot
BUTTON_ALERT_HOVER = "#e35d6a"     # Alert-Button Hover
BUTTON_ALERT_DISABLED = "#8a1f2a"  # Alert-Button deaktiviert

BUTTON_RESET_BG = "#4e5254"        # Reset-Button (Neutral) - Grau
BUTTON_RESET_HOVER = "#686d6f"     # Reset-Button Hover
BUTTON_RESET_DISABLED = "#3a3d3f"  # Reset-Button deaktiviert

BUTTON_PAUSE_BG = "#ff8c42"        # Pause-Button - Orange
BUTTON_PAUSE_HOVER = "#ffa45f"     # Pause-Button Hover
BUTTON_PAUSE_DISABLED = "#a35f30"  # Pause-Button deaktiviert

BUTTON_SKIP_BG = "#5c636a"         # Skip-Button - Dezentes Grau
BUTTON_SKIP_HOVER = "#6c757d"      # Skip-Button Hover
BUTTON_SKIP_DISABLED = "#3f4449"   # Skip-Button deaktiviert

# Kleine Buttons (Tabellen-Aktionen)
BUTTON_SMALL_BG = "#4e5254"        # Kleine Buttons - Neutral
BUTTON_SMALL_HOVER = "#686d6f"     # Kleine Buttons Hover
BUTTON_SMALL_DISABLED = "#3a3d3f"  # Kleine Buttons deaktiviert

# =============================================================================
# RAHMEN UND GRENZEN - Verschiedene Rahmen-Farben
# =============================================================================

TAB_BORDER_COLOR = "#1e2124"       # Tab-Rahmen
GROUP_BORDER_COLOR = "#2a2c30"     # Gruppen-Rahmen (LabelFrames)
DETAIL_BORDER_COLOR = "#4a4d52"    # Detail-Editor-Rahmen
DOWNLOAD_BORDER_COLOR = "#3a3d42"  # Download-Bereich-Rahmen
EXPORT_BORDER_COLOR = "#45484f"    # Export-Bereich-Rahmen

# =============================================================================
# TABELLEN-FARBEN - Treeview und Tabellen-Elemente
# =============================================================================

TABLE_BG = "#2b2d31"               # Tabellen-Hintergrund
TABLE_HEADER_BG = "#23262a"       # Tabellen-Header-Hintergrund
TABLE_HEADER_FG = "#f0f0f0"       # Tabellen-Header-Text
TABLE_SELECT_BG = "#3f4248"       # Tabellen-Selektion
TABLE_ROW_HEIGHT = 20             # Tabellen-Zeilen-Höhe

# =============================================================================
# TOOLTIP-FARBEN - Hilfe-Tooltips
# =============================================================================

TOOLTIP_BG = "#1F2129"            # Tooltip-Hintergrund
TOOLTIP_FG = "#ffffff"            # Tooltip-Text
TOOLTIP_BORDER = "#7289da"        # Tooltip-Rahmen
TOOLTIP_PADX = 9                  # Tooltip-Padding horizontal
TOOLTIP_PADY = 5                  # Tooltip-Padding vertikal
TOOLTIP_DURATION = 4000           # Tooltip-Anzeigedauer (ms)

# =============================================================================
# SCROLLBAR-FARBEN - Custom Scrollbars (customtkinter)
# =============================================================================

SCROLLBAR_WIDTH = 14              # Scrollbar-Breite (px)
SCROLLBAR_TRACK_COLOR = "#1e2124" # Scrollbar-Track
SCROLLBAR_THUMB_COLOR = "#7289da" # Scrollbar-Thumb
SCROLLBAR_THUMB_HOVER = "#8A9DE3" # Scrollbar-Thumb Hover

# =============================================================================
# UI-ELEMENT-FARBEN - Spezielle UI-Elemente
# =============================================================================

# Help-Icons (Fragezeichen)
HELP_ICON_FG = "#666666"          # Help-Icon Standard
HELP_ICON_HOVER_FG = "#ffffff"    # Help-Icon Hover-Text
HELP_ICON_HOVER_BG = "#4a4d52"    # Help-Icon Hover-Hintergrund

# Dropdown-Elemente (customtkinter)
DROPDOWN_BG = ENTRY_BG            # Dropdown-Hintergrund
DROPDOWN_FG = ENTRY_FG            # Dropdown-Text
DROPDOWN_BORDER = "#4a4d52"       # Dropdown-Rahmen
DROPDOWN_HOVER = "#3a3d42"        # Dropdown-Hover

# =============================================================================
# STYLE-NAMEN - Ttk-Style-Identifikatoren
# =============================================================================

STYLE_BUTTON_PRIMARY = "MPD.TButton.Primary"
STYLE_BUTTON_ALERT = "MPD.TButton.Alert"
STYLE_BUTTON_RESET = "MPD.TButton.Reset"
STYLE_BUTTON_PAUSE = "MPD.TButton.Pause"
STYLE_BUTTON_SKIP = "MPD.TButton.Skip"
STYLE_BUTTON_SMALL = "MPD.TButton.Small"
STYLE_BUTTON_SMALL_ALERT = "MPD.TButton.Small.Alert"
STYLE_PROGRESSBAR = "MPD.Horizontal.TProgressbar"

# =============================================================================
# STYLE-SETUP - Ttk-Styles konfigurieren
# =============================================================================

def setup_ttk_styles() -> None:
    """Initialisiert zentrale ttk-Styles (Buttons, Progressbar, Notebook, etc.)."""
    from tkinter import ttk

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Cache default button layout so custom styles inherit a valid layout
    try:
        default_button_layout = style.layout("TButton")
    except Exception:
        default_button_layout = None

    # =========================================================================
    # NOTEBOOK-STYLES - Tab-Navigation
    # =========================================================================
    
    style.configure("TNotebook", background=BG_COLOR, borderwidth=0)

    # Einheitliche Tab-Größe (Breite/Höhe per padding)
    TAB_PADX = 14  # linkes/rechtes Padding
    TAB_PADY = 7   # oberes/unteres Padding

    style.configure(
        "TNotebook.Tab",
        background=FRAME_BG,
        foreground=ENTRY_FG,
        font=("Arial", 11, "bold"),
        padding=(TAB_PADX, TAB_PADY),
    )

    # Gleiche Padding-Werte für ausgewählt/nicht ausgewählt erzwingen
    style.map(
        "TNotebook.Tab",
        background=[("selected", ENTRY_BG)],
        padding=[("selected", (TAB_PADX, TAB_PADY)), ("!selected", (TAB_PADX, TAB_PADY))],
    )

    # =========================================================================
    # TREEVIEW-STYLES - Tabellen und Listen
    # =========================================================================
    
    style.configure(
        "MPD.Treeview",
        background=TABLE_BG,
        fieldbackground=TABLE_BG,
        foreground=ENTRY_FG,
        bordercolor=TABLE_BG,
        borderwidth=0,
        rowheight=TABLE_ROW_HEIGHT,
        font=("Arial", 9),
    )
    style.map(
        "MPD.Treeview",
        background=[("selected", TABLE_SELECT_BG)],
        foreground=[("selected", ENTRY_FG)],
    )

    style.configure(
        "MPD.Treeview.Heading",
        background=TABLE_HEADER_BG,
        foreground=TABLE_HEADER_FG,
        font=("Arial", 11, "bold"),
        borderwidth=0,
    )
    style.map(
        "MPD.Treeview.Heading",
        background=[("active", TABLE_HEADER_BG)],
        foreground=[("active", TABLE_HEADER_FG)],
    )

    # =========================================================================
    # PROGRESSBAR-STYLES - Fortschrittsbalken
    # =========================================================================
    
    style.configure(
        STYLE_PROGRESSBAR,
        troughcolor=ENTRY_BG,
        background=BUTTON_BG,
        bordercolor=ENTRY_BG,
        lightcolor=BUTTON_BG,
        darkcolor=BUTTON_BG,
    )

    # =========================================================================
    # BUTTON-STYLES - Verschiedene Button-Varianten
    # =========================================================================
    
    # Buttons: Basis-Konfiguration
    base_button_conf = {
        "font": ("Arial", 12, "bold"),
        "padding": (14, 10),
        "relief": "flat",
        "foreground": BUTTON_FG,
        "borderwidth": 0,
    }

    # Primary Button (Start/Bestätigen) - Blau
    style.configure(STYLE_BUTTON_PRIMARY, background=BUTTON_PRIMARY_BG, **base_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_PRIMARY, default_button_layout)
    style.map(
        STYLE_BUTTON_PRIMARY,
        background=[("active", BUTTON_PRIMARY_HOVER), ("disabled", BUTTON_PRIMARY_DISABLED)],
        foreground=[("disabled", "#dddddd")],
    )

    # Alert Button (Stop/Fehler) - Rot
    style.configure(STYLE_BUTTON_ALERT, background=BUTTON_ALERT_BG, **base_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_ALERT, default_button_layout)
    style.map(
        STYLE_BUTTON_ALERT,
        background=[("active", BUTTON_ALERT_HOVER), ("disabled", BUTTON_ALERT_DISABLED)],
        foreground=[("disabled", "#dddddd")],
    )

    # Reset Button (Neutral) - Grau
    style.configure(STYLE_BUTTON_RESET, background=BUTTON_RESET_BG, **base_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_RESET, default_button_layout)
    style.map(
        STYLE_BUTTON_RESET,
        background=[("active", BUTTON_RESET_HOVER), ("disabled", BUTTON_RESET_DISABLED)],
        foreground=[("disabled", "#dddddd")],
    )

    # Pause Button - Orange
    style.configure(STYLE_BUTTON_PAUSE, background=BUTTON_PAUSE_BG, **base_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_PAUSE, default_button_layout)
    style.map(
        STYLE_BUTTON_PAUSE,
        background=[("active", BUTTON_PAUSE_HOVER), ("disabled", BUTTON_PAUSE_DISABLED)],
        foreground=[("disabled", "#f7e2d2")],
    )

    # Skip Button - Dezentes Grau
    style.configure(
        STYLE_BUTTON_SKIP,
        background=BUTTON_SKIP_BG,
        foreground="#f0f0f0",
        padding=(14, 10),
        relief="flat",
        borderwidth=0,
        font=("Arial", 12, "bold"),
    )
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_SKIP, default_button_layout)
    style.map(
        STYLE_BUTTON_SKIP,
        background=[("active", BUTTON_SKIP_HOVER), ("disabled", BUTTON_SKIP_DISABLED)],
        foreground=[("disabled", "#c4c4c4")],
    )

    # =========================================================================
    # SMALL BUTTON STYLES - Kleine Buttons für Tabellen-Aktionen
    # =========================================================================
    
    small_button_conf = {
        "font": ("Arial", 10, "bold"),
        "padding": (5, 3),
        "relief": "flat",
        "foreground": BUTTON_FG,
        "borderwidth": 0,
    }

    # Small Neutral Buttons
    style.configure(STYLE_BUTTON_SMALL, background=BUTTON_SMALL_BG, **small_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_SMALL, default_button_layout)
    style.map(
        STYLE_BUTTON_SMALL,
        background=[("active", BUTTON_SMALL_HOVER), ("disabled", BUTTON_SMALL_DISABLED)],
        foreground=[("disabled", "#dddddd")],
    )

    # Small Alert Buttons
    style.configure(STYLE_BUTTON_SMALL_ALERT, background=BUTTON_ALERT_BG, **small_button_conf)
    if default_button_layout is not None:
        style.layout(STYLE_BUTTON_SMALL_ALERT, default_button_layout)
    style.map(
        STYLE_BUTTON_SMALL_ALERT,
        background=[("active", BUTTON_ALERT_HOVER), ("disabled", BUTTON_ALERT_DISABLED)],
        foreground=[("disabled", "#dddddd")],
    )