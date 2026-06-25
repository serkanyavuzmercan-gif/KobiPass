"""
En alttaki kayıt satırının göz ikonu ile hizalı '+ Kayıt Ekle' çubuğu.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from kobipass.i18n import tr
from kobipass.ui.entry_row import ROW_CONTROL_HEIGHT, ROW_LAYOUT_SPACING, ROW_MARGINS


class AddRecordBar(QWidget):
    """Liste sonunda; son satırdaki göz ikonunun tam altında Kayıt Ekle."""

    def __init__(self, on_add, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("addRecordBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*ROW_MARGINS)
        layout.setSpacing(ROW_LAYOUT_SPACING)

        self._btn_add = QPushButton()
        self._btn_add.setObjectName("addRecordBtn")
        self._btn_add.setFixedHeight(ROW_CONTROL_HEIGHT)
        self._btn_add.clicked.connect(on_add)
        self.retranslate()

        layout.addWidget(
            self._btn_add,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch(1)

    def retranslate(self) -> None:
        self._btn_add.setText(tr("btn_add_record"))
        self._btn_add.setToolTip(tr("add_record_tip"))

    def set_visible_bar(self, visible: bool) -> None:
        self.setVisible(visible)
