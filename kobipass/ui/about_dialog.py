"""KobiPass premium Güvenlik Protokolü penceresi."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kobipass import __version__
from kobipass.i18n import tr
from kobipass.resources import app_icon, logo_pixmap
from kobipass.ui.icons import icon_shield


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("premiumInfoDialog")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(860, 560)
        self.resize(900, 590)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 20)
        outer.setSpacing(16)

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
        self._subtitle = QLabel()
        self._subtitle.setObjectName("premiumInfoSubtitle")
        self._subtitle.setWordWrap(True)
        header_text.addWidget(self._eyebrow)
        header_text.addWidget(self._title)
        header_text.addWidget(self._subtitle)
        header.addLayout(header_text, 1)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("premiumInfoHero")
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hero.setMinimumWidth(240)
        hero.setMaximumWidth(285)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(12)

        shield = QLabel()
        shield.setObjectName("premiumInfoHeroIcon")
        shield.setPixmap(icon_shield(size=60).pixmap(60, 60))
        hero_layout.addWidget(shield)
        hero_layout.addStretch(1)

        self._hero_title = QLabel()
        self._hero_title.setObjectName("premiumInfoHeroTitle")
        self._hero_title.setWordWrap(True)
        hero_layout.addWidget(self._hero_title)
        self._hero_text = QLabel()
        self._hero_text.setObjectName("premiumInfoHeroText")
        self._hero_text.setWordWrap(True)
        hero_layout.addWidget(self._hero_text)

        self._trust_chips: list[QLabel] = []
        for _ in range(3):
            chip = QLabel()
            chip.setObjectName("premiumInfoChip")
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hero_layout.addWidget(chip)
            self._trust_chips.append(chip)
        hero_layout.addStretch(2)
        body.addWidget(hero)

        content = QVBoxLayout()
        content.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(10)
        self._card_titles: list[QLabel] = []
        self._card_texts: list[QLabel] = []
        for index in range(6):
            card = QFrame()
            card.setObjectName("premiumInfoCard")
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(5)
            title = QLabel()
            title.setObjectName("premiumInfoCardTitle")
            title.setWordWrap(True)
            text = QLabel()
            text.setObjectName("premiumInfoCardText")
            text.setWordWrap(True)
            card_layout.addWidget(title)
            card_layout.addWidget(text)
            card_layout.addStretch()
            grid.addWidget(card, index // 2, index % 2)
            self._card_titles.append(title)
            self._card_texts.append(text)
        content.addLayout(grid, 1)

        credits = QFrame()
        credits.setObjectName("premiumCredits")
        credits.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        credits_layout = QHBoxLayout(credits)
        credits_layout.setContentsMargins(14, 10, 14, 10)
        self._credits = QLabel()
        self._credits.setObjectName("premiumCreditsText")
        self._credits.setWordWrap(True)
        credits_layout.addWidget(self._credits, 1)
        self._tech = QLabel("PyQt6  ·  cryptography  ·  argon2-cffi")
        self._tech.setObjectName("premiumCreditsTech")
        credits_layout.addWidget(self._tech, 0, Qt.AlignmentFlag.AlignRight)
        content.addWidget(credits)
        body.addLayout(content, 1)
        outer.addLayout(body, 1)

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
        self.setWindowTitle(tr("about_title"))
        self._eyebrow.setText(tr("security_window_eyebrow"))
        self._title.setText(tr("security_window_title"))
        self._subtitle.setText(tr("security_window_subtitle"))
        self._hero_title.setText(tr("security_hero_title"))
        self._hero_text.setText(tr("security_hero_text"))
        for label, key in zip(
            self._trust_chips,
            ("landing_trust_aes", "landing_trust_argon", "landing_trust_local"),
        ):
            label.setText(tr(key))
        for index in range(6):
            self._card_titles[index].setText(tr(f"security_card{index + 1}_title"))
            self._card_texts[index].setText(tr(f"security_card{index + 1}_text"))
        self._credits.setText(
            tr("security_credits", version=__version__)
        )
        self.close_btn.setText(tr("help_close"))
