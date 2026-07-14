"""
Yönetici: kullanıcı değişiklik geçmişi görüntüleme.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.permissions import field_label, is_sensitive_audit_field, mask_audit_value
from kobipass.resources import app_icon
from kobipass.vault_model import AuditEntry, KobiVault


def _audit_summary_display(entry: AuditEntry, vault: KobiVault) -> str:
    """Özeti kayıt anında saklanan metinden değil, mevcut dile göre üretir."""
    if entry.action == "vault_save":
        return tr("audit_vault_saved")
    if entry.action == "field_edit":
        if is_sensitive_audit_field(entry.field):
            return tr("audit_password_updated")
        return tr("audit_field_updated", field=field_label(entry.field, vault))
    return entry.summary


def _audit_user_display(entry: AuditEntry, vault: KobiVault) -> str:
    """Kullanıcı adını çevirir: varsayılan 'Kullanıcı N' dile göre çevrilir,
    yöneticinin verdiği özel etiket ise aynen gösterilir."""
    slot = entry.user_slot
    if not slot:
        return entry.user_label
    labels = getattr(vault, "user_slot_labels", []) or []
    if 1 <= slot <= len(labels):
        label = str(labels[slot - 1]).strip()
        # Varsayılan etiketler (eski/yeni) — özel değilse dile göre çevir.
        if label and label not in (f"Kullanıcı {slot}", f"Alt Kullanıcı {slot}"):
            return label
    return tr("role_user", slot=slot)


def _audit_value_display(entry: AuditEntry, which: str) -> str:
    if entry.action != "field_edit":
        return ""
    raw = entry.old_value if which == "old" else entry.new_value
    if is_sensitive_audit_field(entry.field):
        if entry.old_value or entry.new_value or entry.summary:
            return tr("audit_masked_value")
        return tr("audit_masked_value")
    if not entry.old_value and not entry.new_value and entry.field == "info1":
        return tr("audit_masked_value")
    return mask_audit_value(raw, entry.field)


class AuditLogDialog(QDialog):
    def __init__(self, vault: KobiVault, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("audit_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.resize(1020, 520)
        self._vault = vault
        self._all_logs = list(reversed(vault.audit_log))

        layout = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        self._filter = QLineEdit()
        self._filter.setPlaceholderText(tr("audit_filter_placeholder"))
        self._filter.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter)
        layout.addLayout(filter_row)

        self._empty = QLabel(tr("audit_empty"))
        self._empty.setVisible(not self._all_logs)
        layout.addWidget(self._empty)

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

        self._populate(self._all_logs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText(tr("help_close"))
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _apply_filter(self, text: str) -> None:
        term = text.strip().lower()
        if not term:
            self._populate(self._all_logs)
            return
        filtered: list[AuditEntry] = []
        for entry in self._all_logs:
            haystack = " ".join(
                [
                    entry.at,
                    entry.user_label,
                    entry.entry_name,
                    entry.field,
                    entry.summary,
                    field_label(entry.field, self._vault) if entry.field else "",
                ]
            ).lower()
            if term in haystack:
                filtered.append(entry)
        self._populate(filtered)

    def _populate(self, logs: list[AuditEntry]) -> None:
        self._empty.setVisible(not self._all_logs)
        self._table.setRowCount(len(logs))
        for row, entry in enumerate(logs):
            field_display = (
                field_label(entry.field, self._vault) if entry.field else ""
            )
            self._table.setItem(row, 0, QTableWidgetItem(entry.at))
            self._table.setItem(
                row, 1, QTableWidgetItem(_audit_user_display(entry, self._vault))
            )
            self._table.setItem(row, 2, QTableWidgetItem(entry.entry_name))
            self._table.setItem(row, 3, QTableWidgetItem(field_display))
            self._table.setItem(
                row, 4, QTableWidgetItem(_audit_value_display(entry, "old"))
            )
            self._table.setItem(
                row, 5, QTableWidgetItem(_audit_value_display(entry, "new"))
            )
            self._table.setItem(
                row, 6, QTableWidgetItem(_audit_summary_display(entry, self._vault))
            )
