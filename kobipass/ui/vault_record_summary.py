"""Kasa çalışma alanı sağ paneli — kayıt özeti ve güvenlik görseli."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from kobipass.i18n import tr
from kobipass.ui.theme import theme_manager


class _ShieldGraphic(QWidget):
    """Mockup'taki parlayan kalkan görseli."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultSummaryShield")
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        theme_manager.theme_changed.connect(self.update)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = theme_manager.is_dark()
        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(self.width(), self.height()) * 0.34

        ring = QColor("#4b68f4" if dark else "#3b5bdb")
        ring.setAlpha(42 if dark else 56)
        painter.setPen(QPen(ring, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            int(cx - radius - 18),
            int(cy - radius - 18),
            int((radius + 18) * 2),
            int((radius + 18) * 2),
        )
        painter.drawEllipse(
            int(cx - radius + 10),
            int(cy - radius + 10),
            int((radius - 10) * 2),
            int((radius - 10) * 2),
        )

        shield = QColor("#5b7cff" if dark else "#4b68f4")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shield)
        top = cy - radius * 0.72
        height = radius * 1.45
        width = radius * 1.05
        polygon = QPolygonF(
            [
                QPointF(cx, top),
                QPointF(cx + width, top + height * 0.28),
                QPointF(cx + width * 0.82, top + height),
                QPointF(cx, top + height * 1.08),
                QPointF(cx - width * 0.82, top + height),
                QPointF(cx - width, top + height * 0.28),
            ]
        )
        painter.drawPolygon(polygon)

        lock = QColor("#ffffff")
        painter.setBrush(lock)
        body_w = radius * 0.34
        body_h = radius * 0.28
        body_x = cx - body_w / 2
        body_y = cy - body_h * 0.1
        painter.drawRoundedRect(int(body_x), int(body_y), int(body_w), int(body_h), 4, 4)
        shackle_w = radius * 0.42
        shackle_h = radius * 0.24
        painter.setPen(QPen(lock, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(
            int(cx - shackle_w / 2),
            int(body_y - shackle_h),
            int(shackle_w),
            int(shackle_h * 2),
            0,
            180 * 16,
        )
        painter.end()


class VaultRecordSummaryPanel(QFrame):
    """Sağdaki kayıt özeti paneli."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultRecordSummary")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(250)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setObjectName("vaultSummaryTitle")
        layout.addWidget(self._title)

        stats_host = QFrame()
        stats_host.setObjectName("vaultSummaryStats")
        stats_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stats_grid = QGridLayout(stats_host)
        stats_grid.setContentsMargins(12, 10, 12, 10)
        stats_grid.setHorizontalSpacing(10)
        stats_grid.setVerticalSpacing(8)

        self._total_label = QLabel()
        self._total_label.setObjectName("vaultSummaryStatLabel")
        self._total_value = QLabel("0")
        self._total_value.setObjectName("vaultSummaryStatValue")
        stats_grid.addWidget(self._total_label, 0, 0)
        stats_grid.addWidget(self._total_value, 0, 1, Qt.AlignmentFlag.AlignRight)

        self._hidden_label = QLabel()
        self._hidden_label.setObjectName("vaultSummaryStatLabel")
        self._hidden_value = QLabel("0")
        self._hidden_value.setObjectName("vaultSummaryStatValue")
        stats_grid.addWidget(self._hidden_label, 1, 0)
        stats_grid.addWidget(self._hidden_value, 1, 1, Qt.AlignmentFlag.AlignRight)

        self._add_label = QLabel()
        self._add_label.setObjectName("vaultSummaryStatLabel")
        self._add_value = QLabel()
        self._add_value.setObjectName("vaultSummaryStatValue")
        stats_grid.addWidget(self._add_label, 2, 0)
        stats_grid.addWidget(self._add_value, 2, 1, Qt.AlignmentFlag.AlignRight)

        self._saved_label = QLabel()
        self._saved_label.setObjectName("vaultSummaryStatLabel")
        self._saved_value = QLabel()
        self._saved_value.setObjectName("vaultSummaryStatValue")
        stats_grid.addWidget(self._saved_label, 3, 0)
        stats_grid.addWidget(self._saved_value, 3, 1, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(stats_host)
        layout.addWidget(_ShieldGraphic(), 1)
        self._caption = QLabel()
        self._caption.setObjectName("vaultSummaryCaption")
        self._caption.setWordWrap(True)
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._caption)
        self.retranslate()

    def retranslate(self) -> None:
        self._title.setText(tr("vault_summary_section"))
        self._total_label.setText(tr("summary_total_fields"))
        self._hidden_label.setText(tr("summary_hidden_values"))
        self._add_label.setText(tr("summary_field_add"))
        self._saved_label.setText(tr("summary_last_saved"))
        self._caption.setText(tr("summary_security_caption"))

    def update_stats(
        self,
        *,
        total_fields: int,
        hidden_values: int,
        can_add_fields: bool,
        dirty: bool,
    ) -> None:
        self._total_value.setText(str(total_fields))
        self._hidden_value.setText(str(hidden_values))
        self._add_value.setText(
            tr("summary_available") if can_add_fields else tr("summary_restricted")
        )
        self._saved_value.setText(
            tr("summary_not_saved") if dirty else tr("summary_saved")
        )
