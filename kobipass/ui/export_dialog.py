"""
CSV dışa aktarma onay diyaloğu.

Dışa aktarma yıkıcı değil ama GERİ ALINAMAZ bir sızıntı yüzeyi yaratır: diskte,
kasa parolasından bağımsız, düz metin bir dosya. Bu yüzden tek tıkla değil,
ne yazılacağını sayıyla gösteren ve dosyanın şifresiz olduğunu söyleyen bir
onaydan geçer.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.csv_export import (
    DELIMITER_EXCEL,
    DELIMITER_STANDARD,
    ExportPlan,
    build_export,
)
from kobipass.i18n import tr
from kobipass.resources import app_icon
from kobipass.vault_model import KobiVault


class ExportCsvDialog(QDialog):
    """Ne aktarılacağını gösterir, gizli sekme ve biçim seçimini alır."""

    def __init__(self, vault: KobiVault, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vault = vault
        self._hidden_count = len(vault.hidden_tabs())

        self.setWindowTitle(tr("export_title"))
        self.setWindowIcon(app_icon())
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        warning = QLabel(tr("export_warning"))
        warning.setObjectName("exportWarning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        self._summary = QLabel("")
        self._summary.setObjectName("exportSummary")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        # Kullanıcı işlemin iz bıraktığını ÖNCEDEN bilmeli. Dışa aktarmayı
        # ekran görüntüsünden daha iyi bir savunma yapan şey tam da bu: ekran
        # görüntüsü loglanamaz, dışa aktarma loglanır.
        logged = QLabel(tr("export_logged_notice"))
        logged.setObjectName("exportLoggedNotice")
        logged.setWordWrap(True)
        layout.addWidget(logged)

        # Gizli sekmeler VARSAYILAN OLARAK DIŞARIDA. Onlar kasadaki tek gerçek
        # kriptografik sınır; şifresiz bir dosyaya sessizce dökülmemeli.
        self._hidden_check: QCheckBox | None = None
        if self._hidden_count:
            self._hidden_check = QCheckBox(
                tr("export_include_hidden", n=self._hidden_count)
            )
            self._hidden_check.setChecked(False)
            self._hidden_check.toggled.connect(self._refresh)
            layout.addWidget(self._hidden_check)

            note = QLabel(tr("export_include_hidden_note"))
            note.setObjectName("exportHiddenNote")
            note.setWordWrap(True)
            layout.addWidget(note)

        fmt = QGroupBox(tr("export_delimiter"))
        fmt_layout = QVBoxLayout(fmt)
        fmt_layout.setContentsMargins(10, 8, 10, 10)
        self._excel_radio = QRadioButton(tr("export_delimiter_excel"))
        self._excel_radio.setChecked(True)
        self._standard_radio = QRadioButton(tr("export_delimiter_standard"))
        fmt_layout.addWidget(self._excel_radio)
        fmt_layout.addWidget(self._standard_radio)
        layout.addWidget(fmt)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if self._ok_btn:
            self._ok_btn.setText(tr("export_do"))
            # Onay düğmesi VARSAYILAN DEĞİL: Enter'a basmak kazara şifresiz
            # dosya üretmesin.
            self._ok_btn.setDefault(False)
            self._ok_btn.setAutoDefault(False)
        if cancel_btn:
            cancel_btn.setText(tr("cancel"))
            cancel_btn.setDefault(True)

        self._refresh()

    def _refresh(self) -> None:
        plan = self.plan()
        self._summary.setText(
            tr("export_summary", records=plan.record_count, tabs=plan.tab_count)
        )
        if self._ok_btn:
            self._ok_btn.setEnabled(plan.record_count > 0)

    def include_hidden(self) -> bool:
        return bool(self._hidden_check and self._hidden_check.isChecked())

    def delimiter(self) -> str:
        return DELIMITER_EXCEL if self._excel_radio.isChecked() else DELIMITER_STANDARD

    def plan(self) -> ExportPlan:
        return build_export(self._vault, include_hidden=self.include_hidden())
