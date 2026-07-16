"""Tam pencereyi kaplayan kilit örtüsü.

Boşta kalma, küçültme ya da Ctrl+L ile kasa kilitlendiğinde çalışma alanının
üzerine tam kapatıcı bir katman koyar. Altındaki kasa görünmez/etkisiz olur;
tek çıkış yolu doğru parolayla açmak ya da ana ekrana dönmektir. Böylece
"iptal edip çalışmaya devam etme" mümkün değildir.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.ui.icons import icon_lock


class LockOverlay(QWidget):
    """Kasa kilitliyken çalışma alanını tümüyle kapatan katman."""

    unlock_requested = pyqtSignal(str)
    home_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("lockOverlay")
        # Tıklama/klavye olaylarını bu katman yutar; altına geçmez.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch(1)

        row = QHBoxLayout()
        row.addStretch(1)

        card = QFrame()
        card.setObjectName("lockCard")
        card.setFixedWidth(420)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 26, 28, 24)
        cl.setSpacing(14)

        icon = QLabel()
        icon.setPixmap(icon_lock(QColor("#7c93ff"), size=44).pixmap(44, 44))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(icon)

        self._title = QLabel(tr("lock_title"))
        self._title.setObjectName("lockCardTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._title)

        self._subtitle = QLabel(tr("lock_text"))
        self._subtitle.setObjectName("lockCardSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._subtitle)

        self._pwd = QLineEdit()
        self._pwd.setObjectName("lockPwd")
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText(tr("pwd_placeholder"))
        self._pwd.setMinimumHeight(38)
        self._pwd.returnPressed.connect(self._emit_unlock)
        cl.addWidget(self._pwd)

        self._error = QLabel("")
        self._error.setObjectName("lockError")
        self._error.setWordWrap(True)
        self._error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error.setVisible(False)
        cl.addWidget(self._error)

        self._unlock_btn = QPushButton(tr("lock_unlock"))
        self._unlock_btn.setObjectName("lockUnlockBtn")
        self._unlock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._unlock_btn.setMinimumHeight(40)
        self._unlock_btn.clicked.connect(self._emit_unlock)
        cl.addWidget(self._unlock_btn)

        self._home_btn = QPushButton(tr("lock_go_home"))
        self._home_btn.setObjectName("lockHomeBtn")
        self._home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._home_btn.setFlat(True)
        self._home_btn.clicked.connect(self.home_requested.emit)
        cl.addWidget(self._home_btn, 0, Qt.AlignmentFlag.AlignCenter)

        row.addWidget(card)
        row.addStretch(1)
        root.addLayout(row)
        root.addStretch(1)

    def _emit_unlock(self) -> None:
        self.unlock_requested.emit(self._pwd.text())

    def retranslate(self) -> None:
        self._title.setText(tr("lock_title"))
        self._subtitle.setText(tr("lock_text"))
        self._pwd.setPlaceholderText(tr("pwd_placeholder"))
        self._unlock_btn.setText(tr("lock_unlock"))
        self._home_btn.setText(tr("lock_go_home"))

    def prepare(self) -> None:
        """Katman gösterilmeden önce alanı temizler."""
        self._pwd.clear()
        self._error.setVisible(False)
        self._error.setText("")

    def focus_password(self) -> None:
        self._pwd.setFocus()
        self._pwd.selectAll()

    def show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.setVisible(True)
        self._pwd.selectAll()
        self._pwd.setFocus()
