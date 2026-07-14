"""
Gömülü yardım paneli — hider'daki Info yapısı: ayrı pencere yok,
başlık çubuğunun altından açılır/kapanır ve gövdeyi aşağı iter.

Panel her iki temada da navy chrome üzerinde durur (hider'daki gibi),
bu yüzden renkleri sabittir ve tema geçişinde asla silikleşmez.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from kobipass import __version__
from kobipass.i18n import tr

_CARD_COUNT = 5


class HelpPanel(QWidget):
    """Üstten açılan bilgi paneli: adımlar · uyarı · künye · özellik kartları."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("helpPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 16)
        layout.setSpacing(12)

        # ── Üst satır: adımlar + uyarı (sol) · künye kartı (sağ) ─────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self._step_labels: list[QLabel] = []
        for n in (1, 2, 3):
            step_row = QHBoxLayout()
            step_row.setSpacing(8)
            badge = QLabel(str(n))
            badge.setObjectName("helpStepBadge")
            badge.setFixedSize(22, 22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text = QLabel()
            text.setObjectName("helpStepText")
            text.setWordWrap(True)
            step_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            step_row.addWidget(text, 1)
            left_col.addLayout(step_row)
            self._step_labels.append(text)

        left_col.addStretch()
        top_row.addLayout(left_col, 3)

        self._warn_box = QLabel()
        self._warn_box.setObjectName("helpWarnBox")
        self._warn_box.setWordWrap(True)
        self._warn_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_row.addWidget(self._warn_box, 3, Qt.AlignmentFlag.AlignTop)

        credits = QWidget()
        credits.setObjectName("helpCreditsCard")
        credits.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cred_layout = QVBoxLayout(credits)
        cred_layout.setContentsMargins(14, 12, 14, 12)
        cred_layout.setSpacing(4)

        self._cred_name = QLabel("KobiPass")
        self._cred_name.setObjectName("helpCreditsName")
        self._cred_by = QLabel()
        self._cred_by.setObjectName("helpCreditsBy")
        self._cred_by.setWordWrap(True)
        self._cred_desc = QLabel()
        self._cred_desc.setObjectName("helpCreditsText")
        self._cred_desc.setWordWrap(True)
        self._cred_ver = QLabel()
        self._cred_ver.setObjectName("helpCreditsText")
        self._cred_footer = QLabel()
        self._cred_footer.setObjectName("helpCreditsFooter")
        self._cred_footer.setWordWrap(True)

        cred_layout.addWidget(self._cred_name)
        cred_layout.addWidget(self._cred_by)
        cred_layout.addWidget(self._cred_desc)
        cred_layout.addSpacing(6)
        cred_layout.addWidget(self._cred_ver)
        cred_layout.addStretch()
        cred_layout.addWidget(self._cred_footer)

        top_row.addWidget(credits, 3)
        layout.addLayout(top_row)

        # ── Alt satır: özellik kartları ───────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self._card_titles: list[QLabel] = []
        self._card_texts: list[QLabel] = []
        for _ in range(_CARD_COUNT):
            card = QWidget()
            card.setObjectName("helpFeatureCard")
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(6)
            c_title = QLabel()
            c_title.setObjectName("helpCardTitle")
            c_title.setWordWrap(True)
            c_text = QLabel()
            c_text.setObjectName("helpCardText")
            c_text.setWordWrap(True)
            card_layout.addWidget(c_title)
            card_layout.addWidget(c_text)
            card_layout.addStretch()
            cards_row.addWidget(card, 1)
            self._card_titles.append(c_title)
            self._card_texts.append(c_text)
        layout.addLayout(cards_row)

        self.retranslate()

    def toggle(self) -> None:
        """Hider'daki Info düğmesi davranışı: aç/kapa."""
        self.setVisible(not self.isVisible())

    def retranslate(self) -> None:
        for idx, lbl in enumerate(self._step_labels, start=1):
            lbl.setText(tr(f"help_step{idx}"))
        self._warn_box.setText(tr("help_warn"))
        for idx in range(_CARD_COUNT):
            self._card_titles[idx].setText(tr(f"help_card{idx + 1}_title"))
            self._card_texts[idx].setText(tr(f"help_card{idx + 1}_text"))
        self._cred_by.setText(tr("help_credits_by"))
        self._cred_desc.setText(tr("help_credits_desc"))
        self._cred_ver.setText(tr("help_credits_ver", version=__version__))
        self._cred_footer.setText(tr("help_credits_footer"))
