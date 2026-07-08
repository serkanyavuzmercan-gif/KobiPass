"""
KobiPass karşılama ekranı — dosya aç / yeni kasa oluştur.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from kobipass.i18n import tr


class LandingPage(QWidget):
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
        center_layout.setSpacing(50)

        self.btn_open_file = QPushButton()
        self.btn_open_file.setFixedSize(220, 220)
        self.btn_open_file.setObjectName("landingSquareBtn")
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_login = QPushButton()
        self.btn_login.setFixedSize(220, 220)
        self.btn_login.setObjectName("landingSquareBtn")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)

        center_layout.addWidget(self.btn_open_file)
        center_layout.addWidget(self.btn_login)
        main_layout.addLayout(center_layout)

        main_layout.addStretch()
        self.retranslate()

    def retranslate(self) -> None:
        self.btn_security.setText(tr("landing_security"))
        self.btn_security.setToolTip(tr("security_badge_tip"))
        self.btn_help.setText(tr("landing_help"))
        self.btn_help.setToolTip(tr("btn_help_tip"))
        self.btn_open_file.setText(tr("landing_open"))
        self.btn_login.setText(tr("landing_login"))
