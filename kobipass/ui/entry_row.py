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
    QVBoxLayout,
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
FIELD_STEP_BTN_WIDTH = 30
FIELD_STEP_BTN_HEIGHT = 20

_ICON_BTN_SIZE = COPY_BTN_SIZE
_FIELD_EYE_BTN_SIZE = QSize(28, 28)
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


def _field_step_button(label: str, object_name: str) -> QToolButton:
    btn = QToolButton()
    btn.setObjectName(object_name)
    btn.setText(label)
    btn.setFixedSize(FIELD_STEP_BTN_WIDTH, FIELD_STEP_BTN_HEIGHT)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        return QSize(0, ROW_CONTROL_HEIGHT + 14)  # +14 Scrollbar boşluğu

    def minimumSizeHint(self) -> QSize:
        return QSize(0, ROW_CONTROL_HEIGHT + 14)  # +14 Scrollbar boşluğu

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
        self._eye_btn: QToolButton | None = None
        self._strength_meter: QFrame | None = None
        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        if sensitive:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            row_host = QWidget(self)
            layout = QHBoxLayout(row_host)
            self.setFixedHeight(ROW_CONTROL_HEIGHT + 3)
        else:
            layout = QHBoxLayout(self)
            self.setFixedHeight(ROW_CONTROL_HEIGHT)

        layout.setContentsMargins(*COPY_GROUP_INSET)
        layout.setSpacing(4)
        layout.setAlignment(_ROW_ALIGN)

        self._copy_btn = _icon_button(icon_copy(), "", "copyBtn")
        self._copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        layout.addWidget(self._copy_btn, 0, _ROW_ALIGN)

        inner_h = ROW_CONTROL_HEIGHT - COPY_GROUP_INSET[1] - COPY_GROUP_INSET[3]
        trailing_btn_width = _FIELD_EYE_BTN_SIZE.width() if sensitive else 0
        gap_count = 2 if sensitive else 1
        edit_width = (
            fixed_width
            - COPY_BTN_SIZE.width()
            - trailing_btn_width
            - COPY_GROUP_INSET[0]
            - COPY_GROUP_INSET[2]
            - 4 * gap_count
        )
        self._edit = QLineEdit()
        self._edit.setFixedWidth(max(72, edit_width))
        self._edit.setFixedHeight(inner_h)
        self._edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._edit, 0, _ROW_ALIGN)

        if sensitive:
            self._eye_btn = QToolButton()
            self._eye_btn.setObjectName("fieldEyeBtn")
            self._eye_btn.setIconSize(_ICON_SIZE)
            self._eye_btn.setFixedSize(_FIELD_EYE_BTN_SIZE)
            self._eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._eye_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._eye_btn.setCheckable(True)
            self._eye_btn.setAutoRaise(True)
            self._eye_btn.setChecked(not self._hidden)
            self._eye_btn.clicked.connect(self._on_eye_clicked)
            layout.addWidget(self._eye_btn, 0, _ROW_ALIGN)

        if sensitive:
            outer.addWidget(row_host)
            self._strength_meter = QFrame(self)
            self._strength_meter.setFixedHeight(3)
            self._strength_meter.setStyleSheet("background-color: transparent;")
            outer.addWidget(self._strength_meter, 0, Qt.AlignmentFlag.AlignBottom)
            self._edit.textChanged.connect(self._update_strength)

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
        self._refresh_eye()

    def _refresh_eye(self) -> None:
        if self._eye_btn is None:
            return
        shown = not self._hidden
        self._eye_btn.setIcon(icon_eye() if shown else icon_eye_off())
        self._eye_btn.setToolTip(tr("eye_hide") if shown else tr("eye_show"))

    def _update_strength(self, text: str) -> None:
        if not self._sensitive or self._strength_meter is None:
            return
        score = len(text)
        color = "red" if score < 6 else "orange" if score < 10 else "green"
        self._strength_meter.setStyleSheet(f"background-color: {color};")

    def set_permission(self, level: FieldLevel) -> None:
        self._permission = level
        effective = level
        if self._always_show and (level == "none" or not can_edit(level)):
            effective = "write"
        elif level == "none":
            effective = "read"
        visible = can_view(effective)
        self.setVisible(visible)
        if not visible:
            return
        editable = can_edit(effective)
        self._edit.setReadOnly(not editable)
        self._edit.setEnabled(editable)
        self._copy_btn.setEnabled(can_copy(effective))
        self._sync_echo()

    def _sync_echo(self) -> None:
        if not self.isVisible() and self._permission == "hidden":
            return
        if self._sensitive and self._eye_btn is not None:
            self._edit.setEchoMode(
                QLineEdit.EchoMode.Password
                if self._hidden
                else QLineEdit.EchoMode.Normal
            )
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
        if self._eye_btn is not None:
            self._eye_btn.blockSignals(True)
            self._eye_btn.setChecked(not hidden)
            self._eye_btn.blockSignals(False)
            self._refresh_eye()
        self._sync_echo()

    def _on_eye_clicked(self) -> None:
        if self._eye_btn is None:
            return
        self._hidden = not self._eye_btn.isChecked()
        self._refresh_eye()
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
        self._permissions = UserPermissions()
        self._extra_fields: list[CompactField] = []

        row = QHBoxLayout(self)
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(ROW_LAYOUT_SPACING)
        row.setAlignment(_ROW_ALIGN)

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
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Scrollarea yüksekliğine scrollbar nefes payı (+14)
        self._scroll.setMinimumHeight(ROW_CONTROL_HEIGHT + 14)

        # Kutular 14px boşluğun ortasında yüzmesin — yukarı yasla
        self._scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._extras_host = QWidget()
        self._extras_host.setObjectName("entryExtrasHost")
        self._extras_layout = QHBoxLayout(self._extras_host)
        self._extras_layout.setContentsMargins(0, 0, 0, 0)
        self._extras_layout.setSpacing(ROW_LAYOUT_SPACING)

        # İçeriği sola ve yukarı hizala
        self._extras_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._field_step_column = QWidget()
        self._field_step_column.setObjectName("fieldStepColumn")
        field_step_layout = QVBoxLayout(self._field_step_column)
        field_step_layout.setContentsMargins(0, 0, 0, 0)
        field_step_layout.setSpacing(2)
        field_step_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )

        self._add_field_btn = _field_step_button("+", "addFieldBtn")
        self._add_field_btn.clicked.connect(self._add_extra_field)
        field_step_layout.addWidget(self._add_field_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self._remove_field_btn = _field_step_button("-", "removeFieldBtn")
        self._remove_field_btn.clicked.connect(self._remove_last_extra_field)
        field_step_layout.addWidget(
            self._remove_field_btn, 0, Qt.AlignmentFlag.AlignHCenter
        )
        self._extras_layout.addWidget(self._field_step_column, 0, Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._extras_host)
        row.addWidget(self._scroll, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)

        self._remove_btn = QPushButton()
        self._remove_btn.setObjectName("dangerBtn")
        self._remove_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove_btn.setFixedHeight(ROW_CONTROL_HEIGHT)
        self._remove_btn.setMinimumWidth(ROW_CONTROL_HEIGHT)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        row.addWidget(self._remove_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.retranslate()

        self._name.textChanged().connect(self._emit_changed)
        self._info1.textChanged().connect(self._emit_changed)

        self._wire_tab_order()
        self._update_field_step_buttons()

    def _field_step_index(self) -> int:
        return self._extras_layout.indexOf(self._field_step_column)

    def _update_field_step_buttons(self) -> None:
        self._remove_field_btn.setEnabled(len(self._extra_fields) > 0)

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

    def _sync_scroll_width(self, *, scroll_to_end: bool = False) -> None:
        # Manuel pikselleri hesaplama kodları (for döngüsü ve setFixedSize) tamamen silindi.
        # Genişlik hesabını artık setWidgetResizable(True) sayesinde QHBoxLayout kendisi yapacak.

        def update_scroll():
            bar = self._scroll.horizontalScrollBar()
            if scroll_to_end:
                bar.setValue(bar.maximum())
            else:
                bar.setValue(min(bar.value(), bar.maximum()))

        # Yeni alan eklendiğinde Qt'nin arayüzü çizmesi birkaç milisaniye sürer.
        # Scroll barın doğru maksimum değere ulaşması için çizimin bitmesini sıfır gecikmeli timer ile bekliyoruz.
        QTimer.singleShot(0, update_scroll)

    def _add_extra_field(self, *, initial_text: str = "", block_signals: bool = False) -> None:
        info_index = len(self._extra_fields) + 2
        field = CompactField(
            info_index=info_index,
            fixed_width=INFO_FIELD_WIDTH,
            sensitive=True,
            parent=self._extras_host,
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
            self._field_step_index(),
            field,
            0,
            _ROW_ALIGN,
        )
        self._extra_fields.append(field)
        field.show()
        self._sync_scroll_width(scroll_to_end=not block_signals)
        self._wire_tab_order()
        self._update_field_step_buttons()
        self._emit_changed()

    def _remove_last_extra_field(self) -> None:
        if not self._extra_fields:
            return
        field = self._extra_fields.pop()
        self._extras_layout.removeWidget(field)
        field.deleteLater()
        self._sync_scroll_width()
        self._wire_tab_order()
        self._update_field_step_buttons()
        self._emit_changed()

    def _clear_extra_fields(self) -> None:
        for field in self._extra_fields:
            self._extras_layout.removeWidget(field)
            field.deleteLater()
        self._extra_fields.clear()
        self._sync_scroll_width()
        self._update_field_step_buttons()

    def apply_permissions(self, perms: UserPermissions) -> None:
        self._permissions = perms
        self._name.set_permission(perms.name)
        self._info1.set_permission(perms.info1)
        for index, field in enumerate(self._extra_fields, start=2):
            field.set_permission(perms.level_for_info_index(index))
        self._sync_scroll_width()
        self._wire_tab_order()

    def set_sensitive_shown(self, shown: bool) -> None:
        for field in self._sensitive_fields():
            if field.isVisible():
                field.set_hidden(not shown)

    def set_can_delete(self, allowed: bool) -> None:
        self._can_delete = allowed
        self._remove_btn.setVisible(allowed)

    def retranslate(self) -> None:
        self._name.retranslate()
        self._info1.retranslate()
        for field in self._extra_fields:
            field.retranslate()
        self._add_field_btn.setToolTip(tr("add_field_tip"))
        self._remove_field_btn.setToolTip(tr("remove_field_tip"))
        self._remove_btn.setText(tr("btn_delete"))

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
