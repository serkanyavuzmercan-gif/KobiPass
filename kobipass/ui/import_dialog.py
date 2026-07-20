"""
CSV içe aktarma önizleme diyaloğu.

Kullanıcı bir CSV seçer; bu diyalog ayracı/kodlamayı saptar, ilk satırın başlık
olup olmadığını seçtirir ve kayıtların hangi alanlara düşeceğini bir önizleme
tablosunda gösterir. Onaylanınca ``plan()`` ile içe aktarma planı alınır.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kobipass.csv_import import CsvDocument, ImportPlan, build_import
from kobipass.i18n import tr
from kobipass.resources import app_icon

_PREVIEW_ROWS = 8


class ImportCsvDialog(QDialog):
    """CSV içe aktarma önizlemesi ve onayı."""

    def __init__(
        self, document: CsvDocument, file_name: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._plan: ImportPlan = build_import(document, has_header=True)

        self.setWindowTitle(tr("import_csv_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumSize(620, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        self._file_label = QLabel(file_name)
        self._file_label.setObjectName("importFileLabel")
        self._file_label.setWordWrap(True)
        layout.addWidget(self._file_label)

        self._summary = QLabel("")
        self._summary.setObjectName("importSummary")
        layout.addWidget(self._summary)

        self._header_check = QCheckBox(tr("import_csv_first_row_header"))
        self._header_check.setChecked(True)
        self._header_check.toggled.connect(self._on_header_toggled)
        layout.addWidget(self._header_check)

        self._table = QTableWidget()
        self._table.setObjectName("importPreviewTable")
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table, 1)

        note = QLabel(tr("import_csv_security_note"))
        note.setObjectName("importSecurityNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)
        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = self._buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText(tr("import_csv_do"))
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))

        self._refresh()

    def _on_header_toggled(self, checked: bool) -> None:
        self._plan = build_import(self._document, has_header=checked)
        self._refresh()

    def _column_titles(self, columns: int) -> list[str]:
        titles: list[str] = []
        for index in range(columns):
            key = "name" if index == 0 else f"info{index}"
            label = self._plan.field_labels.get(key, "")
            if not label:
                if index == 0:
                    label = tr("field_name")
                elif index == 1:
                    label = tr("field_info1")
                else:
                    label = tr("field_info_n", n=index)
            titles.append(label)
        return titles

    def _refresh(self) -> None:
        entries = self._plan.entries
        count = len(entries)
        self._summary.setText(
            tr(
                "import_csv_summary",
                count=count,
                delim=self._document.delimiter,
                encoding=self._document.encoding,
            )
        )
        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(count > 0)

        columns = 1
        for entry in entries:
            columns = max(columns, 2 + len(entry.more_infos))
        self._table.setColumnCount(columns)
        self._table.setHorizontalHeaderLabels(self._column_titles(columns))

        preview = entries[:_PREVIEW_ROWS]
        self._table.setRowCount(len(preview))
        for row, entry in enumerate(preview):
            values = [entry.name, entry.info1, *entry.more_infos]
            for col in range(columns):
                text = values[col] if col < len(values) else ""
                self._table.setItem(row, col, QTableWidgetItem(text))

    def plan(self) -> ImportPlan:
        return self._plan
