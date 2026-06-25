"""
Yönetici: kullanıcı değişiklik geçmişi görüntüleme.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.permissions import field_label
from kobipass.resources import app_icon
from kobipass.vault_model import AuditEntry, KobiVault


def _audit_value_display(entry: AuditEntry, which: str) -> str:
    if entry.action != "field_edit":
        return ""
    if not entry.old_value and not entry.new_value:
        return "—"
    raw = entry.old_value if which == "old" else entry.new_value
    return raw if raw else tr("audit_empty_value")


class AuditLogDialog(QDialog):
    def __init__(self, vault: KobiVault, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("audit_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.resize(1020, 480)

        layout = QVBoxLayout(self)
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            [
                tr("audit_col_at"),
                tr("audit_col_user"),
                tr("audit_col_entry"),
                tr("audit_col_field"),
                tr("audit_col_old"),
                tr("audit_col_new"),
                tr("audit_col_summary"),
            ]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self._table)

        if not vault.audit_log:
            layout.insertWidget(0, QLabel(tr("audit_empty")))

        self._populate(vault)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText(tr("help_close"))
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _populate(self, vault: KobiVault) -> None:
        logs = list(reversed(vault.audit_log))
        self._table.setRowCount(len(logs))
        for row, entry in enumerate(logs):
            field_display = (
                field_label(entry.field) if entry.field else ""
            )
            self._table.setItem(row, 0, QTableWidgetItem(entry.at))
            self._table.setItem(row, 1, QTableWidgetItem(entry.user_label))
            self._table.setItem(row, 2, QTableWidgetItem(entry.entry_name))
            self._table.setItem(row, 3, QTableWidgetItem(field_display))
            self._table.setItem(
                row, 4, QTableWidgetItem(_audit_value_display(entry, "old"))
            )
            self._table.setItem(
                row, 5, QTableWidgetItem(_audit_value_display(entry, "new"))
            )
            self._table.setItem(row, 6, QTableWidgetItem(entry.summary))
