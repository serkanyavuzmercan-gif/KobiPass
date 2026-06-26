"""
Tek vault kaydı satırı — alan bazlı izin desteği.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.permissions import can_copy, can_edit, can_view
from kobipass.ui.icons import icon_copy, icon_eye, icon_eye_off
from kobipass.vault_model import FIELD_NAMES, FieldLevel, UserPermissions, VaultEntry

ROW_CONTROL_HEIGHT = 38
COPY_BTN_SIZE = QSize(32, 32)
COPY_GROUP_INSET = (5, 3, 0, 3)
EYE_BTN_SIZE = QSize(ROW_CONTROL_HEIGHT, ROW_CONTROL_HEIGHT)
ROW_MARGINS = (0, 4, 12, 4)
ROW_LAYOUT_SPACING = 8

_ICON_BTN_SIZE = COPY_BTN_SIZE
_ROW_ALIGN = Qt.AlignmentFlag.AlignVCenter
_ICON_SIZE = QSize(20, 20)
_COPY_FLASH_MS = 900

_active_copy_field: "CompactField | None" = None


def _copy_to_clipboard(text: str) -> None:
    QGuiApplication.clipboard().setText(text)


def _notify_copied(source: QWidget, field_label: str, has_text: bool) -> None:
    window = source.window()
    if window is None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            window = app.activeWindow()
    if window is not None and hasattr(window, "show_copy_notice"):
        window.show_copy_notice(field_label, has_text)


def _icon_button(icon, tooltip: str, object_name: str) -> QToolButton:
    btn = QToolButton()
    btn.setObjectName(object_name)
    btn.setIcon(icon)
    btn.setIconSize(_ICON_SIZE)
    btn.setToolTip(tooltip)
    btn.setFixedSize(_ICON_BTN_SIZE)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _restyle(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class CompactField(QWidget):
    """Yatay: giriş kutusu + kopyala ikonu."""

    def __init__(
        self,
        field_key: str,
        min_width: int = 140,
        stretch: int = 1,
        *,
        sensitive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("copyGroup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._field_key = field_key
        self._permission: FieldLevel = "write"
        self._sensitive = sensitive
        self._hidden = sensitive
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*COPY_GROUP_INSET)
        layout.setSpacing(4)
        layout.setAlignment(_ROW_ALIGN)
        self.setFixedHeight(ROW_CONTROL_HEIGHT)

        self._copy_btn = _icon_button(icon_copy(), "", "copyBtn")
        self._copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        layout.addWidget(self._copy_btn, 0, _ROW_ALIGN)

        inner_h = ROW_CONTROL_HEIGHT - COPY_GROUP_INSET[1] - COPY_GROUP_INSET[3]
        self._edit = QLineEdit()
        self._edit.setMinimumWidth(min_width)
        self._edit.setFixedHeight(inner_h)
        self._edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._edit, stretch=stretch, alignment=_ROW_ALIGN)

        self.setFocusProxy(self._edit)
        self._sync_echo()

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_copy_flash)
        self.retranslate()

    def _label_text(self) -> str:
        return tr(self._field_key)

    def retranslate(self) -> None:
        label = self._label_text()
        self._copy_tooltip_base = tr("copy_tooltip", field=label)
        self._edit.setPlaceholderText(label)
        if not self.property("copied"):
            self._copy_btn.setToolTip(self._copy_tooltip_base)

    def set_permission(self, level: FieldLevel) -> None:
        self._permission = level
        visible = can_view(level)
        self.setVisible(visible)
        if not visible:
            return
        editable = can_edit(level)
        self._edit.setReadOnly(not editable)
        self._copy_btn.setEnabled(can_copy(level))
        self._sync_echo()

    def _sync_echo(self) -> None:
        if not self.isVisible() and self._permission == "hidden":
            return
        if self._permission == "hidden_read":
            self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        elif self._sensitive:
            self._edit.setEchoMode(
                QLineEdit.EchoMode.Password
                if self._hidden
                else QLineEdit.EchoMode.Normal
            )

    def _on_copy_clicked(self) -> None:
        global _active_copy_field
        if _active_copy_field is not None and _active_copy_field is not self:
            _active_copy_field._clear_copy_flash()
        text = self._edit.text()
        _copy_to_clipboard(text)
        self._show_copy_flash()
        _active_copy_field = self
        _notify_copied(self, self._label_text(), bool(text.strip()))

    def _show_copy_flash(self) -> None:
        self._flash_timer.stop()
        self.setProperty("copied", True)
        _restyle(self)
        self._copy_btn.setToolTip(tr("copied_tooltip", field=self._label_text()))
        self._flash_timer.start(_COPY_FLASH_MS)

    def _clear_copy_flash(self) -> None:
        global _active_copy_field
        self._flash_timer.stop()
        if not self.property("copied"):
            return
        self.setProperty("copied", False)
        _restyle(self)
        self._copy_btn.setToolTip(self._copy_tooltip_base)
        if _active_copy_field is self:
            _active_copy_field = None

    def set_hidden(self, hidden: bool) -> None:
        self._hidden = hidden
        self._sync_echo()

    def text(self) -> str:
        return self._edit.text()

    def setText(self, value: str) -> None:
        self._edit.setText(value)

    def textChanged(self):
        return self._edit.textChanged

    def focus_edit(self) -> QLineEdit:
        return self._edit


class EntryRowWidget(QWidget):
    """Bir kasa kaydı — tüm alanlar soldan sağa tek satırda."""

    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("entryRow")
        self._can_delete = True
        self._show_sensitive = False

        row = QHBoxLayout(self)
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(ROW_LAYOUT_SPACING)
        row.setAlignment(_ROW_ALIGN)

        self._eye_btn = _icon_button(icon_eye(), "", "eyeBtn")
        self._eye_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._eye_btn.setCheckable(True)
        self._eye_btn.clicked.connect(self._on_eye_clicked)
        row.addWidget(self._eye_btn, 0, _ROW_ALIGN)

        self._name = CompactField("field_name", min_width=165, stretch=2)
        self._info1 = CompactField(
            "field_info1", min_width=160, stretch=2, sensitive=True
        )
        self._info2 = CompactField(
            "field_info2", min_width=105, stretch=1, sensitive=True
        )
        self._info3 = CompactField(
            "field_info3", min_width=120, stretch=1, sensitive=True
        )
        self._info4 = CompactField(
            "field_info4", min_width=120, stretch=1, sensitive=True
        )

        self._fields = {
            "name": self._name,
            "info1": self._info1,
            "info2": self._info2,
            "info3": self._info3,
            "info4": self._info4,
        }
        self._sensitive_fields = (
            self._info1,
            self._info2,
            self._info3,
            self._info4,
        )

        row.addWidget(self._name, stretch=2, alignment=_ROW_ALIGN)
        row.addWidget(self._info1, stretch=2, alignment=_ROW_ALIGN)
        row.addWidget(self._info2, stretch=1, alignment=_ROW_ALIGN)
        row.addWidget(self._info3, stretch=1, alignment=_ROW_ALIGN)
        row.addWidget(self._info4, stretch=1, alignment=_ROW_ALIGN)

        self._remove_btn = QPushButton()
        self._remove_btn.setObjectName("dangerBtn")
        self._remove_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove_btn.setFixedHeight(ROW_CONTROL_HEIGHT)
        self._remove_btn.setMinimumWidth(ROW_CONTROL_HEIGHT)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        row.addWidget(self._remove_btn, 0, _ROW_ALIGN)

        self._eye_btn.setChecked(False)
        self._apply_sensitive_hidden(True)
        self.retranslate()

        for field in self._fields.values():
            field.textChanged().connect(self._emit_changed)

        self._wire_tab_order()

    def focus_edits(self) -> list[QLineEdit]:
        return [
            field.focus_edit()
            for field in self._fields.values()
            if field.isVisible() and field.focus_edit().isEnabled()
        ]

    def _wire_tab_order(self) -> None:
        edits = self.focus_edits()
        for prev, nxt in zip(edits, edits[1:]):
            QWidget.setTabOrder(prev, nxt)

    def set_field_permission(self, field_name: str, level: FieldLevel) -> None:
        field = self._fields.get(field_name)
        if field is not None:
            field.set_permission(level)

    def apply_permissions(self, perms: UserPermissions) -> None:
        for field_name in FIELD_NAMES:
            self.set_field_permission(field_name, perms.field_level(field_name))
        self._wire_tab_order()
        self._apply_visibility()

    def set_sensitive_shown(self, shown: bool) -> None:
        self._show_sensitive = shown
        self._eye_btn.blockSignals(True)
        self._eye_btn.setChecked(shown)
        self._eye_btn.blockSignals(False)
        self._apply_visibility()

    def set_can_delete(self, allowed: bool) -> None:
        self._can_delete = allowed
        self._remove_btn.setVisible(allowed)

    def _apply_sensitive_hidden(self, hidden: bool) -> None:
        for field in self._sensitive_fields:
            if field.isVisible():
                field.set_hidden(hidden)

    def _apply_visibility(self) -> None:
        self._apply_sensitive_hidden(not self._show_sensitive)
        self._eye_btn.setIcon(
            icon_eye() if self._show_sensitive else icon_eye_off()
        )
        self._eye_btn.setToolTip(
            tr("eye_hide") if self._show_sensitive else tr("eye_show")
        )

    def retranslate(self) -> None:
        for field in self._fields.values():
            field.retranslate()
        self._remove_btn.setText(tr("btn_delete"))
        self._apply_visibility()

    def _on_eye_clicked(self) -> None:
        self._show_sensitive = self._eye_btn.isChecked()
        self._apply_visibility()

    def _emit_changed(self) -> None:
        self.changed.emit()

    def to_entry(self) -> VaultEntry:
        return VaultEntry(
            name=self._name.text().strip(),
            info1=self._info1.text(),
            info2=self._info2.text(),
            info3=self._info3.text(),
            info4=self._info4.text(),
        )

    def load_entry(self, entry: VaultEntry) -> None:
        self._name.setText(entry.name)
        self._info1.setText(entry.info1)
        self._info2.setText(entry.info2)
        self._info3.setText(entry.info3)
        self._info4.setText(entry.info4)
        self.set_sensitive_shown(False)

    def block_change_signals(self, block: bool) -> None:
        for field in self._fields.values():
            field._edit.blockSignals(block)
