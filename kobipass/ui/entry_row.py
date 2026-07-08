"""
Tek vault kaydı satırı — sabit isim/1.bilgi, + ile dinamik ek alanlar.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.permissions import can_copy, can_edit, can_view
from kobipass.ui.icons import icon_copy, icon_eye, icon_eye_off
from kobipass.vault_model import FieldLevel, UserPermissions, VaultEntry

ROW_CONTROL_HEIGHT = 38
COPY_BTN_SIZE = QSize(32, 32)
COPY_GROUP_INSET = (5, 3, 0, 3)
ROW_MARGINS = (0, 4, 12, 4)
ROW_LAYOUT_SPACING = 8

NAME_FIELD_WIDTH = 180
INFO_FIELD_WIDTH = 180

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


def _info_label(info_index: int) -> str:
    if info_index <= 4:
        return tr(f"field_info{info_index}")
    return tr("field_info_n", n=info_index)


class EntryFieldsScroll(QScrollArea):
    """Yatay kaydırma — scrollbar gizli, tekerlek ile kayar."""

    def sizeHint(self) -> QSize:
        return QSize(0, ROW_CONTROL_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, ROW_CONTROL_HEIGHT)

    def wheelEvent(self, event: QWheelEvent) -> None:
        bar = self.horizontalScrollBar()
        delta = event.angleDelta()
        if bar.maximum() > 0 and delta.x() != 0:
            bar.setValue(bar.value() - delta.x())
            event.accept()
            return
        if (
            bar.maximum() > 0
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            and delta.y() != 0
        ):
            bar.setValue(bar.value() - delta.y())
            event.accept()
            return
        event.ignore()


class CompactField(QWidget):
    """Yatay: giriş kutusu + kopyala ikonu (sabit genişlik)."""

    def __init__(
        self,
        info_index: int | None = None,
        *,
        field_key: str | None = None,
        fixed_width: int = INFO_FIELD_WIDTH,
        sensitive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("copyGroup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._info_index = info_index
        self._field_key = field_key
        self._permission: FieldLevel = "write"
        self._sensitive = sensitive
        self._hidden = sensitive
        self._always_show = False
        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

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
        edit_width = fixed_width - COPY_BTN_SIZE.width() - COPY_GROUP_INSET[0] - COPY_GROUP_INSET[2] - 4
        self._edit = QLineEdit()
        self._edit.setFixedWidth(max(72, edit_width))
        self._edit.setFixedHeight(inner_h)
        self._edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._edit, 0, _ROW_ALIGN)

        self.setFocusProxy(self._edit)
        self._sync_echo()

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_copy_flash)
        self.retranslate()

    def _label_text(self) -> str:
        if self._info_index is not None:
            return _info_label(self._info_index)
        if self._field_key:
            return tr(self._field_key)
        return ""

    def retranslate(self) -> None:
        label = self._label_text()
        self._copy_tooltip_base = tr("copy_tooltip", field=label)
        self._edit.setPlaceholderText(label)
        if not self.property("copied"):
            self._copy_btn.setToolTip(self._copy_tooltip_base)

    def set_permission(self, level: FieldLevel) -> None:
        self._permission = level
        effective = level
        if level == "none" and self._always_show:
            effective = "read"
        visible = can_view(effective)
        self.setVisible(visible)
        if not visible:
            return
        editable = can_edit(level)
        self._edit.setReadOnly(not editable)
        self._copy_btn.setEnabled(can_copy(level) if level != "none" else can_copy(effective))
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
    """Bir kasa kaydı — isim + 1.bilgi sabit, + ile ek alanlar."""

    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("entryRow")
        self._can_delete = True
        self._show_sensitive = False
        self._permissions = UserPermissions()
        self._extra_fields: list[CompactField] = []

        row = QHBoxLayout(self)
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(ROW_LAYOUT_SPACING)
        row.setAlignment(_ROW_ALIGN)

        self._eye_btn = _icon_button(icon_eye(), "", "eyeBtn")
        self._eye_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._eye_btn.setCheckable(True)
        self._eye_btn.clicked.connect(self._on_eye_clicked)
        row.addWidget(self._eye_btn, 0, Qt.AlignmentFlag.AlignTop)

        self._name = CompactField(
            field_key="field_name",
            fixed_width=NAME_FIELD_WIDTH,
            sensitive=False,
        )
        self._info1 = CompactField(
            info_index=1,
            fixed_width=INFO_FIELD_WIDTH,
            sensitive=True,
        )
        row.addWidget(self._name, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._info1, 0, Qt.AlignmentFlag.AlignTop)

        self._scroll = EntryFieldsScroll()
        self._scroll.setObjectName("entryFieldsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setMinimumHeight(ROW_CONTROL_HEIGHT)

        # Kutular 14px boşluğun ortasında yüzmesin — yukarı yasla
        self._scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._extras_host = QWidget()
        self._extras_host.setObjectName("entryExtrasHost")
        self._extras_host.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )
        self._extras_layout = QHBoxLayout(self._extras_host)
        self._extras_layout.setContentsMargins(0, 0, 0, 0)
        self._extras_layout.setSpacing(ROW_LAYOUT_SPACING)

        # İçeriği sola ve yukarı hizala
        self._extras_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._add_field_btn = QToolButton()
        self._add_field_btn.setObjectName("addFieldBtn")
        self._add_field_btn.setText("+")
        self._add_field_btn.setFixedSize(ROW_CONTROL_HEIGHT, ROW_CONTROL_HEIGHT)
        self._add_field_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_field_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._add_field_btn.clicked.connect(self._add_extra_field)
        self._extras_layout.addWidget(self._add_field_btn, 0, _ROW_ALIGN)

        self._scroll.setWidget(self._extras_host)
        row.addWidget(self._scroll, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)

        self._remove_btn = QPushButton()
        self._remove_btn.setObjectName("dangerBtn")
        self._remove_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove_btn.setFixedHeight(ROW_CONTROL_HEIGHT)
        self._remove_btn.setMinimumWidth(ROW_CONTROL_HEIGHT)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        row.addWidget(self._remove_btn, 0, Qt.AlignmentFlag.AlignTop)

        self._eye_btn.setChecked(False)
        self._apply_sensitive_hidden(True)
        self.retranslate()

        self._name.textChanged().connect(self._emit_changed)
        self._info1.textChanged().connect(self._emit_changed)

        self._wire_tab_order()

    def _sensitive_fields(self) -> list[CompactField]:
        return [self._info1, *self._extra_fields]

    def focus_edits(self) -> list[QLineEdit]:
        edits = [self._name.focus_edit(), self._info1.focus_edit()]
        for field in self._extra_fields:
            if field.isVisible() and field.focus_edit().isEnabled():
                edits.append(field.focus_edit())
        return edits

    def _wire_tab_order(self) -> None:
        edits = self.focus_edits()
        for prev, nxt in zip(edits, edits[1:]):
            QWidget.setTabOrder(prev, nxt)

    def _sync_scroll_width(self) -> None:
        # Genişlik QHBoxLayout + setWidgetResizable(True) ile hesaplanır.
        # Otomatik sağa kaydırma yok — her + basışında görünür scrollbar/kayma olmaz.
        self._extras_host.adjustSize()

        def clamp_scroll():
            bar = self._scroll.horizontalScrollBar()
            bar.setValue(min(bar.value(), bar.maximum()))

        QTimer.singleShot(0, clamp_scroll)

    def _add_extra_field(self, *, initial_text: str = "", block_signals: bool = False) -> None:
        info_index = len(self._extra_fields) + 2
        field = CompactField(
            info_index=info_index,
            fixed_width=INFO_FIELD_WIDTH,
            sensitive=True,
        )
        field._always_show = True
        if block_signals:
            field._edit.blockSignals(True)
        field.setText(initial_text)
        if block_signals:
            field._edit.blockSignals(False)

        level = self._permissions.level_for_info_index(info_index)
        field.set_permission(level)
        field.textChanged().connect(self._emit_changed)

        self._extras_layout.insertWidget(
            self._extras_layout.indexOf(self._add_field_btn),
            field,
            0,
            _ROW_ALIGN,
        )
        self._extra_fields.append(field)
        field.show()
        self._apply_sensitive_hidden(not self._show_sensitive)
        self._sync_scroll_width()
        self._wire_tab_order()
        self._emit_changed()

    def _clear_extra_fields(self) -> None:
        for field in self._extra_fields:
            self._extras_layout.removeWidget(field)
            field.deleteLater()
        self._extra_fields.clear()
        self._sync_scroll_width()

    def apply_permissions(self, perms: UserPermissions) -> None:
        self._permissions = perms
        self._name.set_permission(perms.name)
        self._info1.set_permission(perms.info1)
        for index, field in enumerate(self._extra_fields, start=2):
            field.set_permission(perms.level_for_info_index(index))
        self._sync_scroll_width()
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
        for field in self._sensitive_fields():
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
        self._name.retranslate()
        self._info1.retranslate()
        for field in self._extra_fields:
            field.retranslate()
        self._add_field_btn.setToolTip(tr("add_field_tip"))
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
            more_infos=[field.text() for field in self._extra_fields],
        )

    def load_entry(self, entry: VaultEntry) -> None:
        self._name.setText(entry.name)
        self._info1.setText(entry.info1)
        self._clear_extra_fields()
        for value in entry.more_infos:
            self._add_extra_field(initial_text=value, block_signals=True)
        self._sync_scroll_width()
        self.set_sensitive_shown(False)

    def block_change_signals(self, block: bool) -> None:
        self._name._edit.blockSignals(block)
        self._info1._edit.blockSignals(block)
        for field in self._extra_fields:
            field._edit.blockSignals(block)
