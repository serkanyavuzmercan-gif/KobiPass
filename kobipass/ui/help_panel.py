"""KobiPass premium Yardım penceresi."""

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
from kobipass.ui.icons import icon_help

_CARD_COUNT = 5


class HelpPanel(QDialog):
    """Giriş ekranıyla aynı tasarım dilindeki kullanım rehberi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("premiumInfoDialog")
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(860, 550)
        self.resize(900, 580)
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

        steps = QFrame()
        steps.setObjectName("premiumInfoHero")
        steps.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        steps.setMinimumWidth(280)
        steps.setMaximumWidth(330)
        step_layout = QVBoxLayout(steps)
        step_layout.setContentsMargins(22, 22, 22, 22)
        step_layout.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("premiumInfoHeroIcon")
        icon.setPixmap(icon_help(size=56).pixmap(56, 56))
        step_layout.addWidget(icon)
        self._steps_title = QLabel()
        self._steps_title.setObjectName("premiumInfoHeroTitle")
        step_layout.addWidget(self._steps_title)

        self._step_labels: list[QLabel] = []
        for n in (1, 2, 3):
            step_row = QHBoxLayout()
            step_row.setSpacing(10)
            badge = QLabel(str(n))
            badge.setObjectName("premiumStepBadge")
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text = QLabel()
            text.setObjectName("premiumStepText")
            text.setWordWrap(True)
            step_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            step_row.addWidget(text, 1)
            step_layout.addLayout(step_row)
            self._step_labels.append(text)
        step_layout.addStretch(1)

        self._version = QLabel()
        self._version.setObjectName("premiumInfoChip")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_layout.addWidget(self._version)
        body.addWidget(steps)

        content = QVBoxLayout()
        content.setSpacing(10)
        self._warn_box = QLabel()
        self._warn_box.setObjectName("premiumWarning")
        self._warn_box.setWordWrap(True)
        content.addWidget(self._warn_box)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._card_titles: list[QLabel] = []
        self._card_texts: list[QLabel] = []
        for index in range(_CARD_COUNT):
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

        footer = QLabel()
        footer.setObjectName("premiumCreditsText")
        footer.setText(tr("help_credits_footer"))
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        content.addWidget(footer)
        self._footer = footer
        body.addLayout(content, 1)
        outer.addLayout(body, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self._close_btn = QPushButton()
        self._close_btn.setObjectName("premiumCloseBtn")
        self._close_btn.setMinimumWidth(110)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.accept)
        buttons.addWidget(self._close_btn)
        outer.addLayout(buttons)
        self.retranslate()

    def toggle(self) -> None:
        if self.isVisible():
            self.close()
            return
        self.show()
        self.raise_()
        self.activateWindow()

    def retranslate(self) -> None:
        self.setWindowTitle(tr("help_title"))
        self._eyebrow.setText(tr("help_window_eyebrow"))
        self._title.setText(tr("help_window_title"))
        self._subtitle.setText(tr("help_window_subtitle"))
        self._steps_title.setText(tr("help_steps_title"))
        for idx, label in enumerate(self._step_labels, start=1):
            label.setText(tr(f"help_step{idx}"))
        self._warn_box.setText(tr("help_warn"))
        for idx in range(_CARD_COUNT):
            self._card_titles[idx].setText(tr(f"help_card{idx + 1}_title"))
            self._card_texts[idx].setText(tr(f"help_card{idx + 1}_text"))
        self._version.setText(tr("help_credits_ver", version=__version__))
        self._footer.setText(tr("help_credits_footer"))
        self._close_btn.setText(tr("help_close"))
