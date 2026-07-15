"""Kasa çalışma alanının sağındaki 'Kayıt Özeti' paneli.

Toplam alan / gizli değer / alan ekleme yetkisi / son kaydedilme
istatistiklerini ve küçük bir güvenlik kartını gösterir. Salt görsel bir
özet olduğu için hiçbir veriyi kalıcı olarak saklamaz veya değiştirmez.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.resources import security_shield_pixmap
from kobipass.ui.icons import (
    icon_bar_chart,
    icon_clock,
    icon_eye_slash,
    icon_layers,
    icon_plus_circle,
    icon_shield,
)

_STAT_ACCENT = QColor("#8296ff")


class _ScalingShield(QLabel):
    """Kalkan görselini, oranını koruyarak kartın genişliğine göre ölçekler.

    Yüksekliği genişliğe göre (heightForWidth) belirlenir; böylece görsel her
    zaman en/boy oranını korur, panel genişledikçe büyür ve etrafındaki
    esnek boşluklarla dikeyde ortalandığında ölü boşluk dengeli görünür.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        policy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def set_source(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self.updateGeometry()
        self._rescale()

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return not self._source.isNull()

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        if self._source.isNull() or self._source.width() == 0:
            return 0
        return int(self._source.height() * max(1, width) / self._source.width())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._source.isNull():
            return
        width = max(1, self.width())
        super().setPixmap(
            self._source.scaledToWidth(
                width, Qt.TransformationMode.SmoothTransformation
            )
        )


class VaultSummaryPanel(QFrame):
    """Sabit genişlikli sağ panel: istatistik kartları + güvenlik kartı."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 13, 14, 13)
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
        outer.addLayout(header)
        outer.addSpacing(1)

        self._row_total, self._value_total = self._make_stat_row(icon_layers)
        outer.addWidget(self._row_total)
        self._row_hidden, self._value_hidden = self._make_stat_row(icon_eye_slash)
        outer.addWidget(self._row_hidden)
        self._row_add, self._value_add = self._make_stat_row(icon_plus_circle)
        outer.addWidget(self._row_add)
        self._row_saved, self._value_saved = self._make_stat_row(icon_clock)
        outer.addWidget(self._row_saved)

        outer.addSpacing(2)

        security = QFrame()
        security.setObjectName("summarySecurityCard")
        security.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        security_layout = QVBoxLayout(security)
        security_layout.setSpacing(12)

        self._security_text = QLabel()
        self._security_text.setObjectName("summarySecurityText")
        self._security_text.setWordWrap(True)
        self._security_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # assets/security_shield.png varsa ham görseli responsive ölçekle;
        # yoksa çizili kalkan ikonuna düş. Her iki durumda kalkan + açıklama
        # grubu kartın dikeyinde ortalanır (üstte/altta dengeli boşluk).
        shield_source = security_shield_pixmap(None)
        security_layout.addStretch(1)
        if not shield_source.isNull():
            security.setObjectName("summarySecurityCardArt")
            security_layout.setContentsMargins(16, 16, 16, 16)
            art = _ScalingShield()
            art.setObjectName("summarySecurityArt")
            art.set_source(shield_source)
            security_layout.addWidget(art, 0)
        else:
            security_layout.setContentsMargins(20, 26, 20, 22)
            shield_icon = QLabel()
            shield_icon.setObjectName("summarySecurityIcon")
            shield_icon.setFixedSize(56, 56)
            shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            shield_icon.setPixmap(
                icon_shield(QColor("#aeb9ff"), size=30).pixmap(30, 30)
            )
            security_layout.addWidget(
                shield_icon, 0, Qt.AlignmentFlag.AlignHCenter
            )
        security_layout.addWidget(self._security_text, 0)
        security_layout.addStretch(1)
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
        total_fields: int,
        hidden_count: int,
        add_allowed: bool,
        last_saved_text: str,
    ) -> None:
        self._value_total.setText(str(total_fields))
        self._value_hidden.setText(str(hidden_count))
        self._value_add.setText(
            tr("summary_add_ok") if add_allowed else tr("summary_add_restricted")
        )
        self._value_saved.setText(last_saved_text)

    def retranslate(self) -> None:
        self._title.setText(tr("summary_title"))
        self._row_total._label_widget.setText(tr("summary_total_fields"))  # type: ignore[attr-defined]
        self._row_hidden._label_widget.setText(tr("summary_hidden_values"))  # type: ignore[attr-defined]
        self._row_add._label_widget.setText(tr("summary_add_field"))  # type: ignore[attr-defined]
        self._row_saved._label_widget.setText(tr("summary_last_saved"))  # type: ignore[attr-defined]
        self._security_text.setText(tr("summary_security_text"))
