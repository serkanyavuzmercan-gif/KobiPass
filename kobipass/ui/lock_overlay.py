"""Tam pencereyi kaplayan kilit örtüsü.

Boşta kalma, küçültme ya da Ctrl+L ile kasa kilitlendiğinde çalışma alanının
üzerine TAM OPAK, kapatıcı bir katman koyar. Altındaki kasa hiç görünmez;
"adam gibi kilitli" — içerik sızmaz. Tek çıkış yolu doğru parolayla açmak ya da
ana ekrana dönmektir. Arkaplan; yavaşça dolaşan renkli bir aurora ve nefes alan
bir kart parıltısıyla canlı tutulur (statik, ölü bir ekran değil).
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.resources import asset_path
from kobipass.ui.icons import icon_lock

# Aurora blob'ları: (renk, faz kayması, merkez X oranı, merkez Y oranı).
_AURORA = (
    (QColor(59, 91, 253), 0.0, 0.28, 0.30),
    (QColor(124, 99, 255), 2.2, 0.72, 0.36),
    (QColor(46, 170, 160), 4.1, 0.44, 0.74),
)


class LockOverlay(QWidget):
    """Kasa kilitliyken çalışma alanını tümüyle kapatan canlı katman."""

    unlock_requested = pyqtSignal(str)
    home_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("lockOverlay")
        # Tıklama/klavye olaylarını bu katman yutar; altına geçmez.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._phase = 0.0
        self._anim = QTimer(self)
        self._anim.setInterval(40)  # ~25 fps — akıcı ama hafif
        self._anim.timeout.connect(self._tick)

        # Arkaplanda çok soluk marka izi (logo3). Bir kez ölçeklenip önbelleğe
        # alınır; her karede yeniden yüklenmez.
        self._brand = QPixmap(str(asset_path("logo3.png")))

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

        self._brand_label = QLabel("KOBİPASS")
        self._brand_label.setObjectName("lockBrand")
        self._brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._brand_label)

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

        # Kartın çevresinde nefes alan renkli parıltı — kilidin "canlı" olduğunu
        # ve odağın burada olduğunu hissettirir.
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setOffset(0, 0)
        self._glow.setBlurRadius(46)
        self._glow.setColor(QColor(59, 91, 253, 160))
        card.setGraphicsEffect(self._glow)

        row.addWidget(card)
        row.addStretch(1)
        root.addLayout(row)
        root.addStretch(1)

    # ---- animasyon ----------------------------------------------------
    def _tick(self) -> None:
        self._phase += 0.016
        pulse = 0.5 + 0.5 * math.sin(self._phase * 2.3)  # 0..1 nefes
        self._glow.setBlurRadius(34 + 30 * pulse)
        self._glow.setColor(
            QColor(
                int(59 + 46 * pulse),
                int(91 + 24 * pulse),
                int(253 - 34 * pulse),
                175,
            )
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        # 1) Tam OPAK koyu taban — arkadaki kasa kesinlikle görünmez.
        base = QLinearGradient(0, 0, r.width(), r.height())
        base.setColorAt(0.0, QColor(7, 11, 20))
        base.setColorAt(1.0, QColor(11, 17, 32))
        painter.fillRect(r, base)

        # 2) Soluk, sürüklenen marka izi (logo3) — sağ altta, hafif kayar.
        if not self._brand.isNull():
            target = int(min(r.width(), r.height()) * 0.42)
            if target > 0:
                scaled = self._brand.scaled(
                    target,
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                drift = math.sin(self._phase * 0.7) * 10
                bx = int(r.width() * 0.80 - scaled.width() / 2 + drift)
                by = int(r.height() * 0.74 - scaled.height() / 2 - drift)
                painter.setOpacity(0.05)
                painter.drawPixmap(bx, by, scaled)
                painter.setOpacity(1.0)

        # 3) Yavaşça dolaşan renkli aurora — toplamalı harmanla yumuşak ışıma.
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        radius = max(r.width(), r.height()) * 0.55
        for color, offset, fx, fy in _AURORA:
            ax = r.width() * fx + math.cos(self._phase + offset) * r.width() * 0.12
            ay = r.height() * fy + math.sin(self._phase * 0.9 + offset) * r.height() * 0.12
            grad = QRadialGradient(ax, ay, radius)
            inner = QColor(color)
            inner.setAlpha(48)
            outer = QColor(color)
            outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            painter.fillRect(r, grad)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._anim.isActive():
            self._anim.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._anim.stop()

    # ---- davranış -----------------------------------------------------
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
