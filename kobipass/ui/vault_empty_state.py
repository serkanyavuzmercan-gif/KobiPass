"""
Kasa görünümü: kalıcı hafif logo filigranı + boş durum rehberi.
Filigran her zaman görünür; rehber yalnızca kayıt yokken.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.resources import watermark_mask_pixmap
from kobipass.ui.icons import icon_file_new
from kobipass.ui.theme import theme_manager

_WATERMARK_DARK_OPACITY = 0.085
_WATERMARK_LIGHT_OPACITY = 0.12


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
        self._source = watermark_mask_pixmap(560)
        self._dark_scaled = QPixmap()
        self._light_scaled = QPixmap()
        theme_manager.theme_changed.connect(self.update)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rebuild_scaled()

    def _rebuild_scaled(self) -> None:
        if self._source.isNull() or self.width() < 8 or self.height() < 8:
            self._dark_scaled = QPixmap()
            self._light_scaled = QPixmap()
            return
        # Kayıt çalışma alanında sağ alta yerleşen temiz, yüksek çözünürlüklü sembol.
        target_h = max(180, int(self.height() * 0.76))
        target_h = min(target_h, int(self.width() * 0.42), 520)
        scaled = self._source.scaledToHeight(
            target_h,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._dark_scaled = self._tint(scaled, QColor("#d7deef"))
        self._light_scaled = self._tint(scaled, QColor("#173e78"))

    @staticmethod
    def _tint(mask: QPixmap, color: QColor) -> QPixmap:
        tinted = QPixmap(mask.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, mask)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        pixmap = self._dark_scaled if theme_manager.is_dark() else self._light_scaled
        if pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        dark = theme_manager.is_dark()

        # İnce mimari çerçeveler boş alanı doldurur; içerikle yarışmaz.
        frame_color = QColor("#41506a") if dark else QColor("#9fb2d0")
        frame_color.setAlpha(24 if dark else 34)
        painter.setPen(QPen(frame_color, 1))
        inset = max(24, int(min(self.width(), self.height()) * 0.08))
        painter.drawRoundedRect(
            QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset),
            34,
            34,
        )

        painter.setOpacity(
            _WATERMARK_DARK_OPACITY if dark else _WATERMARK_LIGHT_OPACITY
        )
        x = self.width() - pixmap.width() - max(28, int(self.width() * 0.055))
        y = self.height() - pixmap.height() - max(18, int(self.height() * 0.05))
        painter.drawPixmap(x, y, pixmap)
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
    """Kayıt yokken premium başlangıç çalışma alanı."""

    add_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultEmptyState")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumHeight(180)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(42, 38, 42, 38)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("vaultEmptyHero")
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hero.setMinimumWidth(360)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 26, 28, 26)
        hero_layout.setSpacing(10)

        self._eyebrow = QLabel()
        self._eyebrow.setObjectName("vaultEmptyEyebrow")
        hero_layout.addWidget(self._eyebrow)

        self._title = QLabel()
        self._title.setObjectName("vaultEmptyTitle")
        self._title.setWordWrap(True)
        hero_layout.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("vaultEmptySubtitle")
        self._subtitle.setWordWrap(True)
        hero_layout.addWidget(self._subtitle)
        hero_layout.addStretch(1)

        self._cta = QPushButton()
        self._cta.setObjectName("vaultEmptyPrimaryBtn")
        self._cta.setIcon(icon_file_new(size=20))
        self._cta.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cta.setFixedHeight(42)
        self._cta.clicked.connect(self.add_requested.emit)
        hero_layout.addWidget(self._cta)

        self._shortcut = QLabel()
        self._shortcut.setObjectName("vaultEmptyShortcut")
        self._shortcut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self._shortcut)
        layout.addWidget(hero, 5)

        steps = QFrame()
        steps.setObjectName("vaultEmptySteps")
        steps.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        steps.setMinimumWidth(280)
        steps_layout = QVBoxLayout(steps)
        steps_layout.setContentsMargins(22, 22, 22, 22)
        steps_layout.setSpacing(12)

        self._steps_title = QLabel()
        self._steps_title.setObjectName("vaultEmptyStepsTitle")
        steps_layout.addWidget(self._steps_title)
        self._steps_subtitle = QLabel()
        self._steps_subtitle.setObjectName("vaultEmptyStepsSubtitle")
        self._steps_subtitle.setWordWrap(True)
        steps_layout.addWidget(self._steps_subtitle)

        self._tips: list[QLabel] = []
        for index in range(3):
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = QLabel(str(index + 1))
            badge.setObjectName("vaultEmptyStepBadge")
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tip = QLabel()
            tip.setObjectName("vaultEmptyTip")
            tip.setWordWrap(True)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(tip, 1)
            steps_layout.addLayout(row)
            self._tips.append(tip)
        steps_layout.addStretch(1)

        self._security = QLabel()
        self._security.setObjectName("vaultEmptySecurity")
        self._security.setAlignment(Qt.AlignmentFlag.AlignCenter)
        steps_layout.addWidget(self._security)
        layout.addWidget(steps, 4)
        self.retranslate()

    def retranslate(self) -> None:
        self._eyebrow.setText(tr("empty_state_eyebrow"))
        self._title.setText(tr("empty_state_title"))
        self._subtitle.setText(tr("empty_state_subtitle"))
        self._steps_title.setText(tr("empty_state_steps_title"))
        self._steps_subtitle.setText(tr("empty_state_steps_subtitle"))
        for index, tip in enumerate(self._tips, start=1):
            tip.setText(tr(f"empty_state_tip{index}"))
        self._cta.setText(tr("empty_state_cta"))
        self._shortcut.setText(tr("empty_state_shortcut"))
        self._security.setText(tr("empty_state_security"))

    def set_restricted(self, restricted: bool) -> None:
        self._cta.setProperty("restricted", restricted)
        self._cta.setToolTip(
            tr("restricted_add_record") if restricted else tr("add_record_tip")
        )
        self._cta.style().unpolish(self._cta)
        self._cta.style().polish(self._cta)
