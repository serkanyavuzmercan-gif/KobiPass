"""
Kasa görünümü boş durum paneli: hafif filigran + kısa rehber + CTA.
Az kayıt varken görünür; liste büyüyünce kaybolur.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.resources import logo_pixmap

_WATERMARK_OPACITY = 0.08
_WATERMARK_HEIGHT = 168


def should_show_empty_state(row_count: int) -> bool:
    """Yalnızca hiç kayıt satırı yokken boş durum gösterilir."""
    return row_count == 0


class VaultEmptyState(QWidget):
    """Kayıt listesinin altındaki rehber alan + filigran."""

    add_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultEmptyState")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumHeight(180)
        self._watermark = logo_pixmap(_WATERMARK_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(10)
        layout.addStretch(1)

        self._title = QLabel()
        self._title.setObjectName("vaultEmptyTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._tip1 = QLabel()
        self._tip2 = QLabel()
        self._tip3 = QLabel()
        for tip in (self._tip1, self._tip2, self._tip3):
            tip.setObjectName("vaultEmptyTip")
            tip.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            tip.setWordWrap(True)
            layout.addWidget(tip)

        self._cta = QPushButton()
        self._cta.setObjectName("addRecordBtn")
        self._cta.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cta.setFixedHeight(38)
        self._cta.clicked.connect(self.add_requested.emit)
        layout.addWidget(self._cta, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(2)
        self.retranslate()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._watermark.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(_WATERMARK_OPACITY)
        x = (self.width() - self._watermark.width()) // 2
        y = (self.height() - self._watermark.height()) // 2
        painter.drawPixmap(x, y, self._watermark)
        painter.end()

    def retranslate(self) -> None:
        self._title.setText(tr("empty_state_title"))
        self._tip1.setText(tr("empty_state_tip1"))
        self._tip2.setText(tr("empty_state_tip2"))
        self._tip3.setText(tr("empty_state_tip3"))
        self._cta.setText(tr("empty_state_cta"))
