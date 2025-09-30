"""
UI und Logik für das Hilfe-Panel
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from .components import create_scrollbar
from .theme import BG_COLOR, LABEL_FG, ENTRY_BG, ENTRY_FG

# Import für Hilfe-Inhalte
try:
    from core.helper import HELP_CONTENT, GENERAL_HELP, IMPORTANT_CONTENT
except ImportError:
    HELP_CONTENT = {}
    GENERAL_HELP = {}
    IMPORTANT_CONTENT = {}


class HelperPanel:
    """Panel für die Hilfe und Anleitungen"""

    def __init__(self, parent: tk.Widget, context: Optional[object] = None):
        """Initialisiert das Panel und baut das Layout auf."""
        self.parent = parent
        self.context = context
        
        # Root frame
        self.frame = tk.Frame(parent, bg=BG_COLOR)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        
        # Liste aller Labels für dynamische wraplength-Anpassung
        self.text_labels = []

        # Scrollbarer Canvas + Content-Container
        self._canvas = tk.Canvas(self.frame, bg=BG_COLOR, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vbar = create_scrollbar(self.frame, orient="vertical", command=self._canvas.yview)
        try:
            self._vbar.grid(row=0, column=1, sticky="ns")
            self._canvas.configure(yscrollcommand=self._vbar.set)
        except Exception:
            pass
        
        self.content = tk.Frame(self._canvas, bg=BG_COLOR)
        self._content_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")
        try:
            self.content.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        # Scrollregion und Breitenanpassung
        def _on_content_config(_evt=None):
            try:
                self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            except Exception:
                pass
        def _on_canvas_config(event):
            try:
                self._canvas.itemconfigure(self._content_window, width=event.width)
                # Dynamische wraplength-Anpassung auslösen
                self._update_wraplength()
            except Exception:
                pass
        self.content.bind("<Configure>", _on_content_config)
        self._canvas.bind("<Configure>", _on_canvas_config)

        # yscrollcommand-Wrapper: feste Thumb-Höhe ~100px
        def _yset(first, last):
            try:
                f = float(first); l = float(last)
            except Exception:
                return
            try:
                sb_h = max(1, int(self._vbar.winfo_height()))
            except Exception:
                sb_h = 1
            desired_px = 100
            desired_frac = min(1.0, max(0.02, desired_px / float(sb_h)))
            nf = max(0.0, min(1.0 - desired_frac, f))
            nl = nf + desired_frac
            try:
                self._vbar.set(nf, nl)
            except Exception:
                pass
        try:
            self._canvas.configure(yscrollcommand=_yset)
        except Exception:
            pass
        try:
            self._canvas.yview_moveto(0.0)
        except Exception:
            pass

        # MouseWheel-Handling
        def _on_mousewheel(event):
            try:
                delta = int(-1*(event.delta/120))
                self._canvas.yview_scroll(delta, "units")
            except Exception:
                pass
        try:
            self._canvas.bind_all("<MouseWheel>", _on_mousewheel)
        except Exception:
            pass

        # Header
        self._create_header()
        
        # Hauptinhalt
        self._create_content()
        
        # Event-Handler für dynamische wraplength-Anpassung
        self._setup_dynamic_wrapping()

    def _setup_dynamic_wrapping(self):
        """Richtet dynamisches Wrapping für alle Text-Labels ein."""
        # Initiale Berechnung nach kurzer Verzögerung
        self.frame.after(100, self._update_wraplength)

    def _update_wraplength(self, event=None):
        """Aktualisiert die wraplength für alle Text-Labels."""
        try:
            # Aktuelle Breite des Canvas ermitteln
            canvas_width = self._canvas.winfo_width()
            if canvas_width <= 1:  # Canvas noch nicht gerendert
                return
            
            # Wraplength berechnen (Canvas-Breite minus Padding)
            base_wraplength = max(300, canvas_width - 40)  # Mindestens 300px
            
            # Alle Labels aktualisieren
            for label_info in self.text_labels:
                label = label_info['label']
                padding_factor = label_info.get('padding_factor', 1.0)
                wraplength = int(base_wraplength * padding_factor)
                label.configure(wraplength=wraplength)
        except Exception:
            pass

    def _add_text_label(self, label: tk.Label, padding_factor: float = 1.0):
        """Fügt ein Label zur Liste der dynamisch angepassten Labels hinzu."""
        self.text_labels.append({
            'label': label,
            'padding_factor': padding_factor
        })

    def _create_header(self):
        """Erstellt den Header des Hilfe-Panels."""
        header_frame = tk.Frame(self.content, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 15))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Titel
        title_label = tk.Label(
            header_frame,
            text="Hilfe & Anleitungen",
            bg=BG_COLOR,
            fg=LABEL_FG,
            font=("Arial", 16, "bold"),
            anchor="center"
        )
        title_label.grid(row=0, column=0, pady=(0, 8))
        
        # Untertitel
        subtitle_label = tk.Label(
            header_frame,
            text="Hier findest du detaillierte Anleitungen für alle Funktionen des MangaPark Downloaders",
            bg=BG_COLOR,
            fg=LABEL_FG,
            font=("Arial", 10),
            anchor="center"
        )
        subtitle_label.grid(row=1, column=0)
        self._add_text_label(subtitle_label, 0.9)

    def _create_content(self):
        """Erstellt den Hauptinhalt des Hilfe-Panels."""
        # Wichtige Hinweise Sektion
        self._create_important_section(0)
        
        # Single-Downloader Sektion
        self._create_section("single_downloader", 1)
        
        # Bulk-Downloader Sektion
        self._create_section("bulk_downloader", 2)
        
        # PDF-Merger Sektion
        self._create_section("pdf_merger", 3)
        
        # Settings Sektion
        self._create_section("settings", 4)
        
        # FAQ Sektion
        self._create_faq_section(5)
        
        # Tipps Sektion
        self._create_tips_section(6)
        
        # Troubleshooting Sektion
        self._create_troubleshooting_section(7)

    def _create_important_section(self, row: int):
        """Erstellt die wichtige Hinweise Sektion."""
        important_data = IMPORTANT_CONTENT.get('important_tips', {})
        if not important_data:
            return
            
        # Wichtige Hinweise Rahmen
        important_frame = tk.LabelFrame(
            self.content,
            text=f" {important_data.get('title', 'Wichtige Hinweise')} ",
            bg=BG_COLOR,
            fg=LABEL_FG,  # Normale Farbe
            bd=2,
            relief="groove",
            font=("Arial", 12, "bold")
        )
        important_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 15))
        important_frame.grid_columnconfigure(0, weight=1)
        
        # Beschreibung
        if important_data.get('description'):
            desc_label = tk.Label(
                important_frame,
                text=important_data['description'],
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 10),
                justify="left"
            )
            desc_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 8))
            self._add_text_label(desc_label, 0.95)
        
        # Schritte
        if important_data.get('steps'):
            steps_frame = tk.Frame(important_frame, bg=BG_COLOR)
            steps_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
            steps_frame.grid_columnconfigure(0, weight=1)
            
            for i, step in enumerate(important_data['steps'], 1):
                step_label = tk.Label(
                    steps_frame,
                    text=step,
                    bg=BG_COLOR,
                    fg=LABEL_FG,  # Normale Farbe
                    font=("Arial", 10),
                    justify="left",
                    anchor="w"
                )
                step_label.grid(row=i, column=0, sticky="w", pady=(4, 4))
                self._add_text_label(step_label, 0.9)

    def _create_section(self, section_key: str, row: int):
        """Erstellt eine Sektion für einen bestimmten Bereich."""
        content = HELP_CONTENT.get(section_key, {})
        if not content:
            return
            
        # Hauptrahmen
        section_frame = tk.LabelFrame(
            self.content,
            text=f" {content.get('title', section_key.title())} ",
            bg=BG_COLOR,
            fg=LABEL_FG,
            bd=2,
            relief="groove",
            font=("Arial", 12, "bold")
        )
        section_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 15))
        section_frame.grid_columnconfigure(0, weight=1)
        
        # Beschreibung
        if content.get('description'):
            desc_label = tk.Label(
                section_frame,
                text=content['description'],
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 10),
                justify="left"
            )
            desc_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 8))
            self._add_text_label(desc_label, 0.95)
        
        # Schritte
        if content.get('steps'):
            steps_frame = tk.Frame(section_frame, bg=BG_COLOR)
            steps_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
            steps_frame.grid_columnconfigure(0, weight=1)
            
            steps_label = tk.Label(
                steps_frame,
                text="Schritte:",
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 10, "bold"),
                anchor="w"
            )
            steps_label.grid(row=0, column=0, sticky="w", pady=(0, 4))
            
            for i, step in enumerate(content['steps'], 1):
                step_label = tk.Label(
                    steps_frame,
                    text=step,
                    bg=BG_COLOR,
                    fg=LABEL_FG,
                    font=("Arial", 9),
                    justify="left",
                    anchor="w"
                )
                step_label.grid(row=i, column=0, sticky="w", pady=(2, 2))
                self._add_text_label(step_label, 0.9)
        
        # Tipps
        if content.get('tips'):
            tips_frame = tk.Frame(section_frame, bg=BG_COLOR)
            tips_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
            tips_frame.grid_columnconfigure(0, weight=1)
            
            tips_label = tk.Label(
                tips_frame,
                text="Tipps:",
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 10, "bold"),
                anchor="w"
            )
            tips_label.grid(row=0, column=0, sticky="w", pady=(0, 4))
            
            for i, tip in enumerate(content['tips'], 1):
                tip_label = tk.Label(
                    tips_frame,
                    text=tip,
                    bg=BG_COLOR,
                    fg=LABEL_FG,
                    font=("Arial", 9),
                    justify="left",
                    anchor="w"
                )
                tip_label.grid(row=i, column=0, sticky="w", pady=(2, 2))
                self._add_text_label(tip_label, 0.9)
        
        # Spezielle Sektionen für Settings
        if section_key == "settings" and content.get('sections'):
            for i, section in enumerate(content['sections'], 3):
                sub_frame = tk.Frame(section_frame, bg=BG_COLOR)
                sub_frame.grid(row=i, column=0, sticky="ew", padx=10, pady=(0, 8))
                sub_frame.grid_columnconfigure(0, weight=1)
                
                sub_title = tk.Label(
                    sub_frame,
                    text=f"• {section['title']}",
                    bg=BG_COLOR,
                    fg=LABEL_FG,
                    font=("Arial", 10, "bold"),
                    anchor="w"
                )
                sub_title.grid(row=0, column=0, sticky="w", pady=(0, 4))
                
                sub_desc = tk.Label(
                    sub_frame,
                    text=section['description'],
                    bg=BG_COLOR,
                    fg=LABEL_FG,
                    font=("Arial", 9),
                    justify="left",
                    anchor="w"
                )
                sub_desc.grid(row=1, column=0, sticky="w", pady=(0, 4))
                self._add_text_label(sub_desc, 0.9)
                
                if section.get('options'):
                    for j, option in enumerate(section['options'], 2):
                        option_label = tk.Label(
                            sub_frame,
                            text=f"  - {option}",
                            bg=BG_COLOR,
                            fg=LABEL_FG,
                            font=("Arial", 9),
                            justify="left",
                            anchor="w"
                        )
                        option_label.grid(row=j, column=0, sticky="w", pady=(1, 1))
                        self._add_text_label(option_label, 0.85)

    def _create_faq_section(self, row: int):
        """Erstellt die FAQ-Sektion."""
        faq_data = GENERAL_HELP.get('faq', [])
        if not faq_data:
            return
            
        # FAQ-Rahmen
        faq_frame = tk.LabelFrame(
            self.content,
            text=" Häufig gestellte Fragen ",
            bg=BG_COLOR,
            fg=LABEL_FG,
            bd=2,
            relief="groove",
            font=("Arial", 12, "bold")
        )
        faq_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 15))
        faq_frame.grid_columnconfigure(0, weight=1)
        
        for i, faq in enumerate(faq_data):
            # Frage
            question_label = tk.Label(
                faq_frame,
                text=f"Q: {faq['question']}",
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 10, "bold"),
                justify="left",
                anchor="w"
            )
            question_label.grid(row=i*2, column=0, sticky="w", padx=10, pady=(8 if i == 0 else 4, 2))
            self._add_text_label(question_label, 0.95)
            
            # Antwort
            answer_label = tk.Label(
                faq_frame,
                text=f"A: {faq['answer']}",
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 9),
                justify="left",
                anchor="w"
            )
            answer_label.grid(row=i*2+1, column=0, sticky="w", padx=20, pady=(0, 8))
            self._add_text_label(answer_label, 0.9)

    def _create_tips_section(self, row: int):
        """Erstellt die Tipps-Sektion."""
        tips_data = GENERAL_HELP.get('tips', [])
        if not tips_data:
            return
            
        # Tipps-Rahmen
        tips_frame = tk.LabelFrame(
            self.content,
            text=" Allgemeine Tipps ",
            bg=BG_COLOR,
            fg=LABEL_FG,
            bd=2,
            relief="groove",
            font=("Arial", 12, "bold")
        )
        tips_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 15))
        tips_frame.grid_columnconfigure(0, weight=1)
        
        for i, tip in enumerate(tips_data):
            tip_label = tk.Label(
                tips_frame,
                text=tip,
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 9),
                justify="left",
                anchor="w"
            )
            tip_label.grid(row=i, column=0, sticky="w", padx=10, pady=(8 if i == 0 else 4, 4))
            self._add_text_label(tip_label, 0.95)

    def _create_troubleshooting_section(self, row: int):
        """Erstellt die Troubleshooting-Sektion."""
        troubleshooting_data = GENERAL_HELP.get('troubleshooting', [])
        if not troubleshooting_data:
            return
            
        # Troubleshooting-Rahmen
        troubleshooting_frame = tk.LabelFrame(
            self.content,
            text=" Problemlösung ",
            bg=BG_COLOR,
            fg=LABEL_FG,
            bd=2,
            relief="groove",
            font=("Arial", 12, "bold")
        )
        troubleshooting_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(0, 15))
        troubleshooting_frame.grid_columnconfigure(0, weight=1)
        
        for i, tip in enumerate(troubleshooting_data):
            tip_label = tk.Label(
                troubleshooting_frame,
                text=tip,
                bg=BG_COLOR,
                fg=LABEL_FG,
                font=("Arial", 9),
                justify="left",
                anchor="w"
            )
            tip_label.grid(row=i, column=0, sticky="w", padx=10, pady=(8 if i == 0 else 4, 4))
            self._add_text_label(tip_label, 0.95)

    def widget(self) -> tk.Frame:
        """Gibt das Haupt-Widget des Panels zurück."""
        return self.frame
