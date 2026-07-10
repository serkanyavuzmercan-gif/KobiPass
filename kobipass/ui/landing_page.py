"""
KobiPass karşılama ekranı — dosya aç / yeni kasa oluştur / son dosyalar.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.settings import get_recent_files


class LandingPage(QWidget):
    recent_file_chosen = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingPage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        top_layout = QHBoxLayout()
        top_layout.addStretch()

        self.btn_security = QPushButton()
        self.btn_security.setObjectName("headerSecurityBtn")
        self.btn_security.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_help = QPushButton()
        self.btn_help.setObjectName("helpBtn")
        self.btn_help.setCursor(Qt.CursorShape.PointingHandCursor)

        top_layout.addWidget(self.btn_security)
        top_layout.addWidget(self.btn_help)
        main_layout.addLayout(top_layout)

        main_layout.addStretch()

        center_layout = QHBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(60)

        self.btn_open_file = QPushButton()
        self.btn_open_file.setFixedSize(260, 260)
        self.btn_open_file.setObjectName("landingSquareBtn")
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_create_file = QPushButton()
        self.btn_create_file.setFixedSize(260, 260)
        self.btn_create_file.setObjectName("landingSquareBtn")
        self.btn_create_file.setCursor(Qt.CursorShape.PointingHandCursor)

        center_layout.addWidget(self.btn_open_file)
        center_layout.addWidget(self.btn_create_file)
        main_layout.addLayout(center_layout)

        main_layout.addSpacing(24)

        self._recent_title = QLabel()
        self._recent_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_title.setObjectName("landingRecentTitle")
        main_layout.addWidget(self._recent_title)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("landingRecentList")
        self._recent_list.setMaximumHeight(140)
        self._recent_list.setMaximumWidth(560)
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        self._recent_list.itemClicked.connect(self._on_recent_activated)
        recent_wrap = QHBoxLayout()
        recent_wrap.addStretch()
        recent_wrap.addWidget(self._recent_list)
        recent_wrap.addStretch()
        main_layout.addLayout(recent_wrap)

        self._recent_empty = QLabel()
        self._recent_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_empty.setObjectName("landingRecentEmpty")
        main_layout.addWidget(self._recent_empty)

        main_layout.addStretch()
        self.retranslate()
        self.refresh_recent()

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_file_chosen.emit(str(path))

    def refresh_recent(self) -> None:
        self._recent_list.clear()
        recent = [p for p in get_recent_files() if Path(p).exists()]
        self._recent_empty.setVisible(not recent)
        self._recent_list.setVisible(bool(recent))
        for path in recent:
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._recent_list.addItem(item)

    def retranslate(self) -> None:
        self.btn_security.setText(tr("landing_security"))
        self.btn_security.setToolTip(tr("security_badge_tip"))
        self.btn_help.setText(tr("landing_help"))
        self.btn_help.setToolTip(tr("btn_help_tip"))
        self.btn_open_file.setText(tr("landing_open"))
        self.btn_create_file.setText(tr("landing_create"))
        self._recent_title.setText(tr("landing_recent"))
        self._recent_empty.setText(tr("landing_recent_empty"))
