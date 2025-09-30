"""Browser management utilities for the MangaPark Downloader.

This module provides functionality for initializing and managing Playwright browsers.
"""

import os
from typing import Callable, Optional, Tuple, Union

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

# Type alias for UI update callback
UIUpdate = Callable[[str], None]

# Browser configuration from environment
OPERA_PROFILE = os.environ.get(
    "MPD_OPERA_PROFILE",
    r"C:\Users\mklmr\AppData\Roaming\Opera Software\Opera Stable\Default",
)
KEEP_BROWSER_OPEN_FOR_DEBUG = os.environ.get("MPD_KEEP_BROWSER_OPEN", "0") == "1"


class BrowserManager:
    """Manages Playwright browser lifecycle and configuration."""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser_like: Optional[Union[Browser, BrowserContext]] = None
        self.page: Optional[Page] = None
    
    def open_page(self, ui_update: UIUpdate) -> bool:
        """Initialize Playwright browser and return a page.
        
        Args:
            ui_update: Callback function for UI status updates
            
        Returns:
            True if successful, False otherwise
        """
        ui_update(" Initialisiere Playwright…")
        
        # Start Playwright
        try:
            self.playwright = sync_playwright().start()
        except Exception as e:
            ui_update(f" Playwright-Start fehlgeschlagen: {e}")
            return False

        # Try persistent context with profile first
        try:
            ui_update(f" Starte Browser (Chromium persistent) mit Profil: {OPERA_PROFILE}")
            self.browser_like = self.playwright.chromium.launch_persistent_context(
                user_data_dir=OPERA_PROFILE,
                headless=True,
            )
            self.page = self.browser_like.new_page()
            return True
        except Exception as e:
            ui_update(f" Persistent konnte nicht gestartet werden: {e}")

        # Fallback: ephemeral browser
        try:
            ui_update(" Starte Browser (Chromium ephemer) ohne Profil…")
            self.browser_like = self.playwright.chromium.launch(headless=True)
            self.page = self.browser_like.new_page()
            return True
        except Exception as e2:
            ui_update(f" Browserstart fehlgeschlagen: {e2}")
            self.cleanup()
            return False
    
    def cleanup(self, ui_update: Optional[UIUpdate] = None) -> None:
        """Clean up browser resources.
        
        Args:
            ui_update: Optional callback function for UI status updates
        """
        if not KEEP_BROWSER_OPEN_FOR_DEBUG and self.browser_like:
            try:
                self.browser_like.close()
                if ui_update:
                    ui_update("🔒 Browser geschlossen")
            except Exception:
                pass
        
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
        
        # Reset state
        self.playwright = None
        self.browser_like = None
        self.page = None
    
    def get_page(self) -> Optional[Page]:
        """Get the current page instance.
        
        Returns:
            The current page or None if not initialized
        """
        return self.page


def open_page(ui_update: UIUpdate) -> Tuple[Optional[Playwright], Optional[Union[Browser, BrowserContext]], Optional[Page]]:
    """Legacy function for backward compatibility.
    
    Startet Playwright, öffnet einen Browserkontext und gibt (playwright, browser/context, page) zurück.
    
    Args:
        ui_update: Callback function for UI status updates
        
    Returns:
        Tuple of (playwright, browser_like, page) or (None, None, None) on failure
    """
    manager = BrowserManager()
    if manager.open_page(ui_update):
        return manager.playwright, manager.browser_like, manager.page
    return None, None, None