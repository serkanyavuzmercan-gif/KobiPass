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

from kobipass.clipboard import clear_clipboard
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


def _install_crash_reporter() -> None:
    """Yakalanmamış istisnayı kullanıcıya GÖSTER.

    Yayınlanan derlemeler PyInstaller ``--windowed`` ile üretiliyor; konsol
    olmadığı için traceback hiçbir yere yazılmıyor ve uygulama tek bir mesaj
    bile göstermeden ölüyordu.
    """
    import traceback

    def hook(exc_type, exc_value, exc_tb) -> None:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        if issubclass(exc_type, KeyboardInterrupt):
            return
        try:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                tr("app_name"),
                tr("fatal_error_text", error=f"{exc_type.__name__}: {exc_value}"),
            )
        except Exception:
            pass

    sys.excepthook = hook


def main() -> int:
    app = QApplication(sys.argv)
    _install_crash_reporter()
    app.setApplicationName(tr("app_name"))
    app.setOrganizationName("MercanSoftware")
    app.setFont(_preferred_ui_font())
    app.setWindowIcon(app_icon())
    app.setStyleSheet(theme_manager.stylesheet())
    theme_manager.theme_changed.connect(lambda: app.setStyleSheet(theme_manager.stylesheet()))

    if activate_existing_instance():
        return 0

    # Süreç herhangi bir yoldan sonlanırken (görev yöneticisi hariç) pano
    # temizlensin; kopyalanan parola uygulamadan sonra sistemde kalmasın.
    app.aboutToQuit.connect(clear_clipboard)

    window = MainWindow()
    # Koruma kurulamazsa (adı yabancı bir süreç tutuyor) uygulama yine açılır;
    # tek örnek koruması bir kolaylıktır, çalışma şartı değildir.
    SingleInstanceGuard(window, app)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
