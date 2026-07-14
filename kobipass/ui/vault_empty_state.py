"""
Kasa görünümü: kalıcı hafif logo filigranı + boş durum rehberi.
Filigran her zaman görünür; rehber yalnızca kayıt yokken.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.resources import logo_pixmap

_WATERMARK_OPACITY = 0.075
# Pencerenin kısa kenarına göre oran — ekrana daha yayılır, yine silik kalır.
_WATERMARK_SIZE_RATIO = 0.58
_WATERMARK_MIN = 220
_WATERMARK_MAX = 520


def should_show_empty_state(row_count: int) -> bool:
    """Yalnızca hiç kayıt satırı yokken boş durum gösterilir."""
    return row_count == 0


class VaultWatermarkPane(QWidget):
    """Kasa gövdesinin arkasında duran, asla kaybolmayan logo filigranı."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultWatermarkPane")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._source = logo_pixmap(512)
        self._scaled = QPixmap()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rebuild_scaled()

    def _rebuild_scaled(self) -> None:
        if self._source.isNull() or self.width() < 8 or self.height() < 8:
            self._scaled = QPixmap()
            return
        side = int(min(self.width(), self.height()) * _WATERMARK_SIZE_RATIO)
        side = max(_WATERMARK_MIN, min(_WATERMARK_MAX, side))
        self._scaled = self._source.scaled(
            side,
            side,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._scaled.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(_WATERMARK_OPACITY)
        x = (self.width() - self._scaled.width()) // 2
        y = (self.height() - self._scaled.height()) // 2
        painter.drawPixmap(x, y, self._scaled)
        painter.end()


class VaultBody(QWidget):
    """Filigran + scroll üst üste; filigran her zaman görünür."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultBody")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.watermark = VaultWatermarkPane(self)
        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("vaultEntriesScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.scroll.viewport().setAutoFillBackground(False)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.watermark.setGeometry(self.rect())
        self.scroll.setGeometry(self.rect())
        self.watermark.lower()
        self.scroll.raise_()


class VaultEmptyState(QWidget):
    """Kayıt yokken rehber + CTA (filigran ayrı katmanda kalır)."""

    add_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultEmptyState")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumHeight(180)

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

    def retranslate(self) -> None:
        self._title.setText(tr("empty_state_title"))
        self._tip1.setText(tr("empty_state_tip1"))
        self._tip2.setText(tr("empty_state_tip2"))
        self._tip3.setText(tr("empty_state_tip3"))
        self._cta.setText(tr("empty_state_cta"))
