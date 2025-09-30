from __future__ import annotations

import os
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

# Core config (app name/version)
from core import config

# UI theme and components
from ui.theme import BG_COLOR, setup_ttk_styles
from ui.components import create_header, create_footer

# Import panel aliases with error handling (prevents silent failure under pythonw)
try:
    from ui import (
        single_downloader_panel,
        bulk_downloader_panel,
        pdf_merger_panel,
        settings_panel,
        helper_panel,
    )
except Exception as e:
    try:
        # Log to file for diagnostics (no directory creation)
        err_path = os.path.join(os.path.dirname(__file__), 'last_gui_error.txt')
        with open(err_path, 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        # Show a message box so double-click users see the reason
        _r = tk.Tk(); _r.withdraw();
        messagebox.showerror('Importfehler', f'{e}');
        _r.destroy()
    except Exception:
        pass
    raise


def open_mangapark(_evt=None):
    try:
        webbrowser.open_new_tab('https://mangapark.net')
    except Exception:
        pass


class AppContext:
    """Shared state between panels (currently only the standard download dir)."""

    def __init__(self):
        from core.utils import load_settings

        settings = load_settings() or {}
        self.standard_dir = settings.get("standard_dir") or os.path.expanduser("~")
        self._listeners = []

    def register(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def update_standard_dir(self, new_dir: str):
        self.standard_dir = new_dir
        for cb in list(self._listeners):
            try:
                cb(new_dir)
            except Exception:
                pass


def main() -> None:
    # Root window
    root = tk.Tk()
    root.title(f"{config.APP_NAME} v{config.APP_VERSION}")
    root.configure(bg=BG_COLOR)
    
    # Fenstergröße (Breite x Höhe)
    root.geometry("700x750")
    # Mindestgröße (Breite x Höhe)
    try:
        root.minsize(455, 500)
    except Exception:
        pass

    setup_ttk_styles()
    context = AppContext()

    # Main container
    container = tk.Frame(root, bg=BG_COLOR)
    container.pack(fill='both', expand=True, padx=20, pady=20)
    container.grid_columnconfigure(0, weight=1)
    container.grid_rowconfigure(1, weight=1)

    # Header
    create_header(
        container,
        title_text=f"{config.APP_NAME}",
        link_text=' MangaPark.com',
        link_callback=open_mangapark,
    )

    # Tabs
    notebook = ttk.Notebook(container)
    notebook.grid(row=1, column=0, sticky='nsew')

    # Single-Downloader Tab
    tab_single = ttk.Frame(notebook)
    tab_single.grid_columnconfigure(0, weight=1)
    tab_single.grid_rowconfigure(0, weight=1)
    single_panel = single_downloader_panel(tab_single, context=context)
    single_panel.widget().grid(row=0, column=0, sticky='nsew')
    notebook.add(tab_single, text='Single-Downloader')

    # Bulk-Downloader Tab
    tab_bulk = ttk.Frame(notebook)
    tab_bulk.grid_columnconfigure(0, weight=1)
    tab_bulk.grid_rowconfigure(0, weight=1)
    bulk_panel = bulk_downloader_panel(tab_bulk, context=context)
    bulk_panel.widget().grid(row=0, column=0, sticky='nsew')
    notebook.add(tab_bulk, text='Bulk-Downloader')

    # PDF-Merger Tab
    tab_merger = ttk.Frame(notebook)
    tab_merger.grid_columnconfigure(0, weight=1)
    tab_merger.grid_rowconfigure(0, weight=1)
    merger_panel = pdf_merger_panel(tab_merger, context=context)
    merger_panel.widget().grid(row=0, column=0, sticky='nsew')
    notebook.add(tab_merger, text='PDF-Merger')

    # Einstellungen Tab
    tab_settings = ttk.Frame(notebook)
    tab_settings.grid_columnconfigure(0, weight=1)
    tab_settings.grid_rowconfigure(0, weight=1)
    settings_panel_inst = settings_panel(tab_settings, context=context)
    settings_panel_inst.widget().grid(row=0, column=0, sticky='nsew')
    notebook.add(tab_settings, text='Einstellungen')

    # Hilfe Tab
    tab_helper = ttk.Frame(notebook)
    tab_helper.grid_columnconfigure(0, weight=1)
    tab_helper.grid_rowconfigure(0, weight=1)
    helper_panel_inst = helper_panel(tab_helper, context=context)
    helper_panel_inst.widget().grid(row=0, column=0, sticky='nsew')
    notebook.add(tab_helper, text='Hilfe')

    # Footer
    create_footer(container, info_text=f"{config.APP_NAME} v{config.APP_VERSION}")

    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        try:
            err_path = os.path.join(os.path.dirname(__file__), 'last_gui_error.txt')
            with open(err_path, 'w', encoding='utf-8') as f:
                f.write(traceback.format_exc())
            _root = tk.Tk(); _root.withdraw();
            messagebox.showerror('Startfehler', f'{e}');
            _root.destroy()
        except Exception:
            pass
