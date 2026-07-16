"""Kasa çalışma alanının sağındaki 'Kayıt Özeti' paneli.

Toplam alan / gizli değer / alan ekleme yetkisi / son kaydedilme
istatistiklerini ve küçük bir güvenlik kartını gösterir. Salt görsel bir
özet olduğu için hiçbir veriyi kalıcı olarak saklamaz veya değiştirmez.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.ui.brand import paint_brand_mark
from kobipass.ui.icons import (
    icon_bar_chart,
    icon_chevron_right,
    icon_clock,
    icon_grid,
    icon_layers,
    icon_save,
)
from kobipass.ui.theme import theme_manager

_STAT_ACCENT = QColor("#8296ff")


class _BrandArt(QWidget):
    """KobiPass amblemini (KP + kilit) vektörel çizen, temaya uyan pano."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumHeight(140)
        theme_manager.theme_changed.connect(self.update)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        # Güvenlik kartı her iki temada da koyu arka planlıdır; amblem her
        # durumda okunur kalsın diye açık mavi tonda çizilir (gece/gündüz uyumlu).
        color = QColor("#9db0ff") if theme_manager.is_dark() else QColor("#8ba0ff")
        side = min(self.width(), self.height()) * 0.82
        rect = QRectF(
            (self.width() - side) / 2.0,
            (self.height() - side) / 2.0,
            side,
            side,
        )
        paint_brand_mark(painter, rect, color, opacity=0.95)
        painter.end()


class VaultSummaryPanel(QFrame):
    """İnce sağ panel: istatistik kartları + güvenlik kartı. Başlıktaki '›'
    düğmesiyle daraltılabilir (collapse_requested sinyali)."""

    collapse_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # İnceltildi: daha dar bir panel, kayıt alanına daha çok yer bırakır.
        self.setMinimumWidth(248)
        self.setMaximumWidth(288)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 11, 12, 12)
        outer.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(7)
        header_icon = QLabel()
        header_icon.setPixmap(icon_bar_chart(_STAT_ACCENT, size=14).pixmap(14, 14))
        header.addWidget(header_icon, 0)
        self._title = QLabel()
        self._title.setObjectName("summaryTitle")
        header.addWidget(self._title, 0)
        header.addStretch(1)
        self._collapse_btn = QPushButton()
        self._collapse_btn.setObjectName("summaryCollapseBtn")
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setIcon(icon_chevron_right(QColor("#8a93a8"), size=15))
        self._collapse_btn.clicked.connect(self.collapse_requested.emit)
        header.addWidget(self._collapse_btn, 0)
        outer.addLayout(header)
        outer.addSpacing(1)

        self._row_rows, self._value_rows = self._make_stat_row(icon_layers)
        outer.addWidget(self._row_rows)
        self._row_cells, self._value_cells = self._make_stat_row(icon_grid)
        outer.addWidget(self._row_cells)
        self._row_access, self._value_access = self._make_stat_row(icon_clock)
        outer.addWidget(self._row_access)
        self._row_saved, self._value_saved = self._make_stat_row(icon_save)
        outer.addWidget(self._row_saved)

        outer.addSpacing(2)

        security = QFrame()
        security.setObjectName("summarySecurityCard")
        security.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        security_layout = QVBoxLayout(security)
        security_layout.setSpacing(10)

        self._security_text = QLabel()
        self._security_text.setObjectName("summarySecurityText")
        self._security_text.setWordWrap(True)
        self._security_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # KobiPass amblemi (KP + kilit) vektörel çizilir; boş alanı doldurur,
        # gündüz/gece temasına uyar (raster görsel yerine).
        security.setObjectName("summarySecurityCardArt")
        security_layout.setContentsMargins(16, 16, 16, 14)
        self._brand_art = _BrandArt()
        self._brand_art.setObjectName("summarySecurityArt")
        security_layout.addWidget(self._brand_art, 1)
        security_layout.addWidget(self._security_text, 0)
        outer.addWidget(security, 1)

        self.retranslate()

    def _make_stat_row(self, icon_fn) -> tuple[QFrame, QLabel]:
        row = QFrame()
        row.setObjectName("summaryStatRow")
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(9, 5, 11, 5)
        lay.setSpacing(9)

        icon_tile = QLabel()
        icon_tile.setObjectName("summaryStatIcon")
        icon_tile.setFixedSize(23, 23)
        icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_tile.setPixmap(icon_fn(_STAT_ACCENT, size=14).pixmap(14, 14))
        lay.addWidget(icon_tile, 0)

        label = QLabel()
        label.setObjectName("summaryStatLabel")
        lay.addWidget(label, 1)
        row._label_widget = label  # type: ignore[attr-defined]

        value = QLabel()
        value.setObjectName("summaryStatValue")
        lay.addWidget(value, 0)
        return row, value

    def set_stats(
        self,
        *,
        total_rows: int,
        total_cells: int,
        last_access_text: str,
        last_saved_text: str,
    ) -> None:
        self._value_rows.setText(str(total_rows))
        self._value_cells.setText(str(total_cells))
        self._value_access.setText(last_access_text)
        self._value_saved.setText(last_saved_text)

    def retranslate(self) -> None:
        self._title.setText(tr("summary_title"))
        self._collapse_btn.setToolTip(tr("summary_collapse"))
        self._row_rows._label_widget.setText(tr("summary_total_rows"))  # type: ignore[attr-defined]
        self._row_cells._label_widget.setText(tr("summary_total_cells"))  # type: ignore[attr-defined]
        self._row_access._label_widget.setText(tr("summary_last_access"))  # type: ignore[attr-defined]
        self._row_saved._label_widget.setText(tr("summary_last_saved"))  # type: ignore[attr-defined]
        self._security_text.setText(tr("summary_security_text"))
