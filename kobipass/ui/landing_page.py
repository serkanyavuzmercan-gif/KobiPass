"""
KobiPass karşılama ekranı — ekranı ikiye bölen "Dosya Aç" / "Yeni Dosya Oluştur".
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.settings import get_recent_files
from kobipass.ui.icons import (
    icon_file_new,
    icon_folder_open,
    icon_help,
    icon_shield,
    icon_theme,
)


class _ActionPanel(QFrame):
    """Ekranın yarısını kaplayan, tamamı tıklanabilir büyük panel."""

    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.pos())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class LandingPage(QWidget):
    recent_file_chosen = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingPage")
        self._glow_anims: list[QPropertyAnimation] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(12)

        # ── Üst bar: tema · güvenlik · yardım ────────────────────────────────
        top_layout = QHBoxLayout()
        top_layout.addStretch()

        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("themeBtn")
        self.btn_theme.setFixedWidth(56)
        self.btn_theme.setIcon(icon_theme())
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_security = QPushButton()
        self.btn_security.setObjectName("headerSecurityBtn")
        self.btn_security.setIcon(icon_shield())
        self.btn_security.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_help = QPushButton()
        self.btn_help.setObjectName("helpBtn")
        self.btn_help.setIcon(icon_help())
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)

        top_layout.addWidget(self.btn_theme)
        top_layout.addWidget(self.btn_security)
        top_layout.addWidget(self.btn_help)
        main_layout.addLayout(top_layout)

        # ── İki panel: sol "Dosya Aç", sağ "Yeni Dosya Oluştur" ──────────────
        split = QHBoxLayout()
        split.setSpacing(16)

        self.btn_open_file, self._open_title, self._open_sub = self._make_panel(
            icon_folder_open()
        )
        self.btn_create_file, self._create_title, self._create_sub = self._make_panel(
            icon_file_new()
        )

        split.addWidget(self.btn_open_file, 1)
        split.addWidget(self.btn_create_file, 1)
        main_layout.addLayout(split, 1)

        # ── Son açılanlar — "Dosya Aç" panelinin İÇİNDE, kaydırılabilir liste ──
        # En son işlem gören dosya en üstte; liste uzadıkça kaydırma çubuğu çıkar.
        open_layout = self.btn_open_file.layout()

        self._recent_title = QLabel()
        self._recent_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_title.setObjectName("landingRecentTitle")
        self._recent_title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        open_layout.addWidget(self._recent_title)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("landingRecentList")
        self._recent_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recent_list.setMaximumWidth(420)
        self._recent_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        self._recent_list.itemClicked.connect(self._on_recent_activated)

        recent_wrap = QHBoxLayout()
        recent_wrap.addStretch()
        recent_wrap.addWidget(self._recent_list)
        recent_wrap.addStretch()
        open_layout.addLayout(recent_wrap, 2)

        # Liste görünürken alt stretch'i küçült ki liste alana yayılsın.
        open_layout.addStretch(1)

        self.retranslate()
        self.refresh_recent()

    def _make_panel(self, icon) -> tuple[_ActionPanel, QLabel, QLabel]:
        panel = _ActionPanel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("landingPanelIcon")
        icon_lbl.setPixmap(icon.pixmap(48, 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon_lbl)

        title = QLabel()
        title.setObjectName("landingPanelTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(title)

        subtitle = QLabel()
        subtitle.setObjectName("landingPanelSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(subtitle)

        layout.addStretch(1)

        self._attach_glow(panel, offset=len(self._glow_anims))
        return panel, title, subtitle

    def _attach_glow(self, widget: QWidget, offset: int) -> None:
        """Hider'ın nefes alan kenarlığının karşılığı: yumuşak indigo parıltı."""
        glow = QGraphicsDropShadowEffect(widget)
        glow.setColor(QColor(75, 104, 244, 150))  # #4b68f4
        glow.setOffset(0, 0)
        glow.setBlurRadius(12)
        widget.setGraphicsEffect(glow)

        anim = QPropertyAnimation(glow, b"blurRadius", self)
        anim.setDuration(3200)
        anim.setStartValue(12)
        anim.setKeyValueAt(0.5, 40)
        anim.setEndValue(12)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.setLoopCount(-1)
        anim.start()
        if offset:  # iki panel senkron nefes almasın
            anim.setCurrentTime(1600)
        self._glow_anims.append(anim)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_file_chosen.emit(str(path))

    def refresh_recent(self) -> None:
        """En son işlem gören dosya en üstte; boşsa bölüm tamamen gizlenir."""
        self._recent_list.clear()
        recent = [p for p in get_recent_files() if Path(p).exists()]
        self._recent_title.setVisible(bool(recent))
        self._recent_list.setVisible(bool(recent))
        for path in recent:
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._recent_list.addItem(item)

    def retranslate(self) -> None:
        self.btn_theme.setToolTip(tr("btn_theme_tip"))
        self.btn_security.setText(tr("landing_security"))
        self.btn_security.setToolTip(tr("security_badge_tip"))
        self.btn_help.setText(tr("landing_help"))
        self.btn_help.setToolTip(tr("btn_help_tip"))
        self._open_title.setText(tr("landing_open_title"))
        self._open_sub.setText(tr("landing_open_sub"))
        self._create_title.setText(tr("landing_create_title"))
        self._create_sub.setText(tr("landing_create_sub"))
        self._recent_title.setText(tr("landing_recent"))
