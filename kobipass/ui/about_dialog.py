"""KobiPass 'Hakkında' penceresi — uygulama künyesi ve Hidroteknik tanıtımı.

Güvenlik protokolü ayrı ``SecurityDialog`` penceresinde anlatılır.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kobipass import __version__
from kobipass.i18n import tr
from kobipass.resources import app_icon, logo_pixmap

HIDROTEKNIK_URL = (
    "https://www.hidroteknik.com.tr/"
    "%C3%9Cr%C3%BCnlerimiz/"
    "kobipass-rol-%C4%B0zolasyonlu-%C5%9Eifre-kasas%C4%B1"
)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("premiumInfoDialog")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(560, 600)
        self.resize(600, 700)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(16)

        # ── Başlık: logo + uygulama adı + sürüm ─────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel()
        logo.setObjectName("premiumInfoLogo")
        logo.setPixmap(logo_pixmap(58))
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        self._eyebrow = QLabel()
        self._eyebrow.setObjectName("premiumInfoEyebrow")
        self._title = QLabel()
        self._title.setObjectName("premiumInfoTitle")
        self._version = QLabel()
        self._version.setObjectName("premiumInfoSubtitle")
        header_text.addWidget(self._eyebrow)
        header_text.addWidget(self._title)
        header_text.addWidget(self._version)
        header.addLayout(header_text, 1)
        outer.addLayout(header)

        # ── Ne işe yarar ────────────────────────────────────────────────────
        what_card = QFrame()
        what_card.setObjectName("premiumInfoCard")
        what_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        what_layout = QVBoxLayout(what_card)
        what_layout.setContentsMargins(16, 14, 16, 14)
        what_layout.setSpacing(4)
        self._what = QLabel()
        self._what.setObjectName("premiumInfoCardText")
        self._what.setWordWrap(True)
        what_layout.addWidget(self._what)
        outer.addWidget(what_card)

        # ── Yapan: Hidroteknik ──────────────────────────────────────────────
        maker_card = QFrame()
        maker_card.setObjectName("premiumInfoHero")
        maker_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        maker_layout = QVBoxLayout(maker_card)
        maker_layout.setContentsMargins(18, 16, 18, 16)
        maker_layout.setSpacing(8)
        self._made_by = QLabel()
        self._made_by.setObjectName("premiumInfoHeroTitle")
        self._made_by.setWordWrap(True)
        self._lead = QLabel()
        self._lead.setObjectName("premiumInfoChip")
        self._tagline = QLabel()
        self._tagline.setObjectName("premiumInfoHeroText")
        self._tagline.setWordWrap(True)
        maker_layout.addWidget(self._made_by)
        maker_layout.addWidget(self._lead)
        maker_layout.addWidget(self._tagline)

        self._website_btn = QPushButton()
        self._website_btn.setObjectName("landingSecondaryBtn")
        self._website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._website_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(HIDROTEKNIK_URL))
        )
        maker_layout.addWidget(self._website_btn, 0, Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(maker_card)

        # ── Kullanım ve sorumluluk şartnamesi (kaydırılabilir) ──────────────
        self._manual_title = QLabel()
        self._manual_title.setObjectName("premiumInfoEyebrow")
        outer.addWidget(self._manual_title)

        manual_scroll = QScrollArea()
        manual_scroll.setObjectName("aboutManualScroll")
        manual_scroll.setWidgetResizable(True)
        manual_scroll.setFrameShape(QFrame.Shape.NoFrame)
        manual_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._manual_body = QLabel()
        self._manual_body.setObjectName("aboutManualBody")
        self._manual_body.setWordWrap(True)
        self._manual_body.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self._manual_body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        manual_scroll.setWidget(self._manual_body)
        outer.addWidget(manual_scroll, 1)

        # ── Künye + teknoloji ───────────────────────────────────────────────
        credits = QFrame()
        credits.setObjectName("premiumCredits")
        credits.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        credits_layout = QHBoxLayout(credits)
        credits_layout.setContentsMargins(14, 10, 14, 10)
        self._footer = QLabel()
        self._footer.setObjectName("premiumCreditsText")
        self._footer.setWordWrap(True)
        credits_layout.addWidget(self._footer, 1)
        self._tech = QLabel("PyQt6  ·  cryptography  ·  argon2-cffi")
        self._tech.setObjectName("premiumCreditsTech")
        credits_layout.addWidget(self._tech, 0, Qt.AlignmentFlag.AlignRight)
        outer.addWidget(credits)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("premiumCloseBtn")
        self.close_btn.setMinimumWidth(110)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.close_btn)
        outer.addLayout(buttons)

        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(tr("about_us_title"))
        self._eyebrow.setText(tr("about_us_eyebrow"))
        self._title.setText(tr("app_name"))
        self._version.setText(tr("about_us_ver", version=__version__))
        self._what.setText(tr("about_us_what"))
        self._made_by.setText(tr("about_us_made_by"))
        self._lead.setText(tr("about_us_lead"))
        self._tagline.setText(tr("about_us_tagline"))
        self._website_btn.setText(tr("about_us_website"))
        self._manual_title.setText(tr("about_manual_title"))
        self._manual_body.setText(tr("about_manual_body"))
        self._footer.setText(tr("about_us_footer"))
        self.close_btn.setText(tr("help_close"))
