#!/usr/bin/env python3
"""
KobiPass — KOBİ parola kasası (PyQt6).

Çalıştırma: python main.py
"""

import sys

if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MercanSoftware.KobiPass.6"
        )
    except Exception:
        pass

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from kobipass.resources import app_icon
from kobipass.single_instance import SingleInstanceGuard, activate_existing_instance
from kobipass.ui.main_window import MainWindow
from kobipass.ui.theme import theme_manager
from kobipass.i18n import tr


def _preferred_ui_font() -> QFont:
    """Modern arayüz fontu: Inter → Manrope → IBM Plex Sans → Segoe UI."""
    families = set(QFontDatabase.families())
    for name in ("Inter", "Manrope", "IBM Plex Sans", "Segoe UI"):
        if name in families:
            return QFont(name)
    return QFont("Segoe UI")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(tr("app_name"))
    app.setOrganizationName("MercanSoftware")
    app.setFont(_preferred_ui_font())
    app.setWindowIcon(app_icon())
    app.setStyleSheet(theme_manager.stylesheet())
    theme_manager.theme_changed.connect(lambda: app.setStyleSheet(theme_manager.stylesheet()))

    if activate_existing_instance():
        return 0

    window = MainWindow()
    SingleInstanceGuard(window, app)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
