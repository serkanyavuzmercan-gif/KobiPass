"""
Parola sağlık raporu — kasadaki zayıf ve tekrar eden parolaları listeler.
Yalnızca yönetici erişir; parola değerleri gösterilmez, yalnızca değerlendirme.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor
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
from kobipass.password_tools import humanize_age, strength_bucket
from kobipass.resources import app_icon
from kobipass.vault_model import KobiVault

_BUCKET_LABEL = {
    "weak": "strength_weak",
    "medium": "strength_medium",
    "strong": "strength_strong",
}
_BUCKET_COLOR = {"weak": "#c42b1c", "medium": "#e07020", "strong": "#3ddc84"}


def analyze_vault(vault: KobiVault) -> list[dict]:
    """info1 parolalarını değerlendirir; zayıf veya tekrar edenleri döndürür."""
    counts: dict[str, int] = {}
    for entry in vault.entries:
        if entry.info1:
            counts[entry.info1] = counts.get(entry.info1, 0) + 1

    findings: list[dict] = []
    for entry in vault.entries:
        pw = entry.info1
        if not pw:
            continue
        bucket = strength_bucket(pw)
        reused = counts.get(pw, 0) > 1
        if bucket == "weak" or reused:
            findings.append(
                {
                    "name": entry.name or tr("audit_unknown_entry"),
                    "bucket": bucket,
                    "reused": reused,
                    "age": humanize_age(entry.pw_updated_at),
                }
            )
    # Önce zayıf, sonra tekrar edenler.
    findings.sort(key=lambda f: (f["bucket"] != "weak", not f["reused"]))
    return findings


class PasswordReportDialog(QDialog):
    def __init__(self, vault: KobiVault, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("report_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setObjectName("userAdminDialog")
        self.resize(720, 460)

        layout = QVBoxLayout(self)

        findings = analyze_vault(vault)
        weak = sum(1 for f in findings if f["bucket"] == "weak")
        reused = sum(1 for f in findings if f["reused"])

        summary = QLabel()
        summary.setObjectName("reportSummary")
        summary.setWordWrap(True)
        if not findings:
            summary.setText(tr("report_all_good"))
            summary.setStyleSheet("color: #3ddc84; font-weight: 600;")
        else:
            summary.setText(tr("report_summary", weak=weak, reused=reused))
        layout.addWidget(summary)

        if findings:
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(
                [
                    tr("audit_col_entry"),
                    tr("report_col_status"),
                    tr("report_col_strength"),
                    tr("report_col_age"),
                ]
            )
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setRowCount(len(findings))

            for row, f in enumerate(findings):
                status_parts = []
                if f["bucket"] == "weak":
                    status_parts.append(tr("report_status_weak"))
                if f["reused"]:
                    status_parts.append(tr("report_status_reused"))
                strength_item = QTableWidgetItem(tr(_BUCKET_LABEL[f["bucket"]]))
                strength_item.setForeground(QColor(_BUCKET_COLOR[f["bucket"]]))

                table.setItem(row, 0, QTableWidgetItem(f["name"]))
                table.setItem(row, 1, QTableWidgetItem(" · ".join(status_parts)))
                table.setItem(row, 2, strength_item)
                table.setItem(row, 3, QTableWidgetItem(f["age"]))
            layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText(tr("help_close"))
        layout.addWidget(buttons)
