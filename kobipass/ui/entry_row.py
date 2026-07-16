"""
Tek vault kaydı satırı — İsim sabit; 1. Bilgi ve ek alanlar yatay scroll içinde.
İsim alanındaki ⋯ menüsünden (onayla) kayıt silinir.
"""

from __future__ import annotations

from PyQt6.QtCore import QMimeData, QPoint, QTimer, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QKeySequence, QMouseEvent, QShortcut, QWheelEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from kobipass.clipboard import copy_text
from kobipass.i18n import tr
from kobipass.permissions import can_copy, can_edit, can_view
from kobipass.ui.icons import icon_copy, icon_eye, icon_eye_off, icon_key, icon_more
from kobipass.vault_model import FieldLevel, UserPermissions, VaultEntry

ROW_MIME = "application/x-kobipass-row-index"

ROW_CONTROL_HEIGHT = 38
COPY_BTN_SIZE = QSize(32, 32)
COPY_GROUP_INSET = (5, 3, 0, 3)
ROW_MARGINS = (0, 4, 12, 4)
ROW_LAYOUT_SPACING = 8

NAME_FIELD_WIDTH = 200
NAME_FIELD_MAX_WIDTH = 390
INFO_FIELD_WIDTH = 180
INFO_FIELD_MAX_WIDTH = 300
INFO_VISIBLE_COLUMNS = 3
FIELD_STEP_BTN_WIDTH = 30
FIELD_STEP_BTN_HEIGHT = 20

_ICON_BTN_SIZE = COPY_BTN_SIZE
_FIELD_EYE_BTN_SIZE = QSize(28, 28)
_FIELD_MENU_BTN_SIZE = QSize(22, 28)
_MENU_ICON_SIZE = QSize(16, 16)
_ROW_ALIGN = Qt.AlignmentFlag.AlignVCenter
_ICON_SIZE = QSize(20, 20)
_COPY_FLASH_MS = 900
_GENERATE_SHORTCUT = QKeySequence("Ctrl+G")
_DELETE_SHORTCUT = QKeySequence("Ctrl+Shift+Delete")

_active_copy_field: "CompactField | None" = None


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


def _menu_text(label: str, shortcut: QKeySequence) -> str:
    key_text = shortcut.toString(QKeySequence.SequenceFormat.NativeText)
    return f"{label}\t{key_text}"


def _default_info_label(info_index: int) -> str:
    if info_index <= 4:
        return tr(f"field_info{info_index}")
    return tr("field_info_n", n=info_index)


def responsive_field_width(
    text_width: int,
    chrome_width: int,
    minimum: int,
    maximum: int | None,
) -> int:
    """Metne göre hücre genişliği; maximum=None ise metin kadar sınırsız büyür."""
    desired = chrome_width + max(82, text_width + 28)
    if maximum is None:
        return max(minimum, desired)
    return max(minimum, min(maximum, desired))


def three_column_info_width(viewport_width: int) -> int:
    """İlk üç değer hücresi viewport'u eşit paylaşır; sonrası aynı genişlikte scroll olur."""
    spacing_budget = ROW_LAYOUT_SPACING * INFO_VISIBLE_COLUMNS
    usable = viewport_width - FIELD_STEP_BTN_WIDTH - spacing_budget
    width = usable // INFO_VISIBLE_COLUMNS
    return max(INFO_FIELD_WIDTH, min(INFO_FIELD_MAX_WIDTH, width))


def four_column_default_width(row_content_width: int) -> int:
    """İsim + üç değer + alan düğmeleri için eşit başlangıç kolon genişliği."""
    spacing_budget = ROW_LAYOUT_SPACING * 4
    usable = row_content_width - FIELD_STEP_BTN_WIDTH - spacing_budget
    return max(NAME_FIELD_WIDTH, min(NAME_FIELD_MAX_WIDTH, usable // 4))


def _password_strength_color(text: str) -> str:
    from kobipass.password_tools import strength_color

    color = strength_color(text)
    return "transparent" if color == "transparent" else color


class EntryFieldsScroll(QScrollArea):
    """Yatay kaydırma — scrollbar gizli, tekerlek ile kayar."""

    viewport_resized = pyqtSignal()

    def sizeHint(self) -> QSize:
        return QSize(0, ROW_CONTROL_HEIGHT + 14)  # +14 Scrollbar boşluğu

    def minimumSizeHint(self) -> QSize:
        return QSize(0, ROW_CONTROL_HEIGHT + 14)  # +14 Scrollbar boşluğu

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.viewport_resized.emit()

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
    """Yatay: kopyala + giriş (+ göz/⋯). İsimde kayıt sil; bilgide alan sil."""

    delete_requested = pyqtSignal()
    field_remove_requested = pyqtSignal(object)
    width_changed = pyqtSignal()

    def __init__(
        self,
        info_index: int | None = None,
        *,
        field_key: str | None = None,
        fixed_width: int = INFO_FIELD_WIDTH,
        sensitive: bool = False,
        with_delete_menu: bool = False,
        responsive_width: bool = False,
        max_width: int | None = None,
        primary_field: bool = False,
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
        self._view_only = False
        self._can_delete = True
        self._can_reorder = True
        self._can_remove_field = True
        self._custom_label = ""
        self._eye_btn: QToolButton | None = None
        self._menu_btn: QToolButton | None = None
        self._gen_action = None
        self._delete_action = None
        self._field_remove_action = None
        self._generate_shortcut: QShortcut | None = None
        self._field_remove_shortcut: QShortcut | None = None
        self._delete_shortcut: QShortcut | None = None
        self._strength_meter: QFrame | None = None
        self._base_width = fixed_width
        self._responsive_width = responsive_width
        self._max_width = max_width
        self._primary_field = primary_field
        self.setProperty("primaryField", primary_field)
        self.setFixedWidth(fixed_width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        has_menu = sensitive or with_delete_menu
        has_eye = sensitive

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
        trailing_btn_width = 0
        if has_eye:
            trailing_btn_width += _FIELD_EYE_BTN_SIZE.width()
        if has_menu:
            trailing_btn_width += _FIELD_MENU_BTN_SIZE.width()
        gap_count = 1 + int(has_eye) + int(has_menu)
        edit_width = (
            fixed_width
            - COPY_BTN_SIZE.width()
            - trailing_btn_width
            - COPY_GROUP_INSET[0]
            - COPY_GROUP_INSET[2]
            - 4 * gap_count
        )
        self._chrome_width = fixed_width - max(72, edit_width)
        self._edit = QLineEdit()
        self._edit.setFixedWidth(max(72, edit_width))
        self._edit.setFixedHeight(inner_h)
        self._edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._edit, 0, _ROW_ALIGN)

        if has_eye:
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

        if has_menu:
            self._menu_btn = QToolButton()
            self._menu_btn.setObjectName("fieldMenuBtn")
            self._menu_btn.setIcon(icon_more())
            self._menu_btn.setIconSize(_MENU_ICON_SIZE)
            self._menu_btn.setFixedSize(_FIELD_MENU_BTN_SIZE)
            self._menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._menu_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._menu_btn.setAutoRaise(True)
            self._menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self._field_menu = QMenu(self._menu_btn)
            if sensitive:
                self._gen_action = self._field_menu.addAction(icon_key(), "")
                self._gen_action.triggered.connect(self._on_generate)
                # Parola üret altında: bu bilgi alanını sil
                self._field_remove_action = self._field_menu.addAction("")
                self._field_remove_action.triggered.connect(
                    lambda: self.field_remove_requested.emit(self)
                )
            if with_delete_menu:
                self._delete_action = self._field_menu.addAction("")
                self._delete_action.triggered.connect(self.delete_requested.emit)
            self._menu_btn.setMenu(self._field_menu)
            layout.addWidget(self._menu_btn, 0, _ROW_ALIGN)

        if sensitive:
            self._generate_shortcut = QShortcut(_GENERATE_SHORTCUT, self)
            self._generate_shortcut.setContext(
                Qt.ShortcutContext.WidgetWithChildrenShortcut
            )
            self._generate_shortcut.activated.connect(self._on_generate)
            self._field_remove_shortcut = QShortcut(_DELETE_SHORTCUT, self)
            self._field_remove_shortcut.setContext(
                Qt.ShortcutContext.WidgetWithChildrenShortcut
            )
            self._field_remove_shortcut.activated.connect(
                self._request_field_remove
            )
        elif with_delete_menu:
            self._delete_shortcut = QShortcut(_DELETE_SHORTCUT, self)
            self._delete_shortcut.setContext(
                Qt.ShortcutContext.WidgetWithChildrenShortcut
            )
            self._delete_shortcut.activated.connect(self.delete_requested.emit)

        if sensitive:
            outer.addWidget(row_host)
            self._strength_meter = QFrame(self)
            self._strength_meter.setFixedHeight(3)
            self._strength_meter.setStyleSheet("background-color: transparent;")
            outer.addWidget(self._strength_meter, 0, Qt.AlignmentFlag.AlignBottom)
            self._edit.textChanged.connect(self._update_strength)
        if responsive_width:
            self._edit.textChanged.connect(self._update_responsive_width)

        self.setFocusProxy(self._edit)
        self._sync_echo()

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_copy_flash)
        self.retranslate()

    def _label_text(self) -> str:
        if self._custom_label:
            return self._custom_label
        if self._info_index is not None:
            return _default_info_label(self._info_index)
        if self._field_key:
            return tr(self._field_key)
        return ""

    def set_custom_label(self, label: str) -> None:
        self._custom_label = label.strip()
        self.retranslate()

    def _update_responsive_width(self, text: str = "") -> None:
        if not self._responsive_width:
            return
        sample = text or self._edit.placeholderText() or self._label_text()
        text_width = self._edit.fontMetrics().horizontalAdvance(sample)
        target = responsive_field_width(
            text_width,
            self._chrome_width,
            self._base_width,
            self._max_width,
        )
        if target == self.width():
            return
        self._edit.setFixedWidth(target - self._chrome_width)
        self.setFixedWidth(target)
        self.width_changed.emit()

    def set_compact_width(self, width: int) -> None:
        """Bilgi hücresinin toplam genişliğini kontrolleri bozmadan günceller."""
        target = max(self._chrome_width + 72, width)
        if target == self.width():
            return
        self._edit.setFixedWidth(target - self._chrome_width)
        self.setFixedWidth(target)

    def set_responsive_base_width(self, width: int) -> None:
        if not self._responsive_width:
            return
        self._base_width = width
        self._update_responsive_width(self._edit.text())

    def retranslate(self) -> None:
        label = self._label_text()
        self._copy_tooltip_base = tr("copy_tooltip", field=label)
        placeholder = (
            self._custom_label
            if self._custom_label
            else (tr("field_value_placeholder") if self._info_index is not None else label)
        )
        self._edit.setPlaceholderText(placeholder)
        if not self.property("copied"):
            self._copy_btn.setToolTip(self._copy_tooltip_base)
        self._refresh_eye()
        if self._menu_btn is not None:
            self._menu_btn.setToolTip(tr("row_menu_tip"))
        if self._gen_action is not None:
            self._gen_action.setText(
                _menu_text(tr("gen_password_menu"), _GENERATE_SHORTCUT)
            )
        if self._field_remove_action is not None:
            self._field_remove_action.setText(
                _menu_text(tr("btn_delete"), _DELETE_SHORTCUT)
            )
        if self._delete_action is not None:
            self._delete_action.setText(
                _menu_text(tr("btn_delete"), _DELETE_SHORTCUT)
            )
        self._update_responsive_width(self._edit.text())

    def _refresh_eye(self) -> None:
        if self._eye_btn is None:
            return
        shown = not self._hidden
        self._eye_btn.setIcon(icon_eye() if shown else icon_eye_off())
        self._eye_btn.setToolTip(tr("eye_hide") if shown else tr("eye_show"))

    def _update_strength(self, text: str) -> None:
        if not self._sensitive:
            return
        color = _password_strength_color(text)
        if self._strength_meter is not None:
            self._strength_meter.setStyleSheet(f"background-color: {color};")

    def is_editable(self) -> bool:
        return not self._edit.isReadOnly() and self._edit.isEnabled()

    def set_generated(self, value: str) -> None:
        """Üretilmiş parolayı alana yazar ve görünür yapar."""
        if not self.is_editable():
            return
        self._edit.setText(value)
        self._hidden = False
        self._sync_echo()
        self._refresh_eye()
        if self._eye_btn is not None:
            self._eye_btn.setChecked(True)

    def _on_generate(self) -> None:
        """Kutuya özel parola üret — dolu parolada üzerine yazmadan önce sorar."""
        if not self.is_editable():
            return
        from kobipass.password_tools import generate_password

        if self._edit.text().strip():
            answer = QMessageBox.question(
                self,
                tr("gen_overwrite_title"),
                tr("gen_overwrite_text"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.set_generated(generate_password())

    def _request_field_remove(self) -> None:
        if (
            self._can_remove_field
            and not self._view_only
            and self.is_editable()
        ):
            self.field_remove_requested.emit(self)

    def set_can_delete(self, allowed: bool) -> None:
        self._can_delete = allowed
        self._refresh_menu()

    def set_can_remove_field(self, allowed: bool) -> None:
        self._can_remove_field = allowed
        self._refresh_menu()

    def set_info_index(self, info_index: int) -> None:
        self._info_index = info_index
        self.retranslate()

    def _refresh_menu(self) -> None:
        if self._menu_btn is None:
            return
        show = False
        if self._gen_action is not None:
            gen_ok = self.is_editable()
            self._gen_action.setVisible(gen_ok)
            self._gen_action.setEnabled(gen_ok)
            if self._generate_shortcut is not None:
                self._generate_shortcut.setEnabled(gen_ok)
            show = show or gen_ok
        if self._field_remove_action is not None:
            rem_ok = (
                self._can_remove_field
                and not self._view_only
                and self.is_editable()
            )
            self._field_remove_action.setVisible(rem_ok)
            self._field_remove_action.setEnabled(rem_ok)
            if self._field_remove_shortcut is not None:
                self._field_remove_shortcut.setEnabled(rem_ok)
            show = show or rem_ok
        if self._delete_action is not None:
            del_ok = self._can_delete and not self._view_only
            self._delete_action.setVisible(del_ok)
            self._delete_action.setEnabled(del_ok)
            if self._delete_shortcut is not None:
                self._delete_shortcut.setEnabled(del_ok)
            show = show or del_ok
        self._menu_btn.setVisible(show)

    def set_view_only(self, view_only: bool) -> None:
        self._view_only = view_only

    def set_permission(self, level: FieldLevel) -> None:
        self._permission = level
        effective = level
        visible = can_view(effective)
        self.setVisible(visible)
        if not visible:
            return
        editable = can_edit(effective) and not self._view_only
        self._edit.setReadOnly(not editable)
        if editable:
            self.setEnabled(True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self._edit.setEnabled(True)
            self._edit.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self._edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._edit.setProperty("readOnlyPerm", "false")
        else:
            self.setEnabled(True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self._edit.setEnabled(False)
            self._edit.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._edit.clearFocus()
            self._edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._edit.setProperty("readOnlyPerm", "true")
            self._edit.setToolTip(tr("restricted_field_edit"))
            self.setToolTip(tr("restricted_field_edit"))
        _restyle(self._edit)
        self._copy_btn.setEnabled(can_copy(effective) and not self._view_only)
        if self._copy_btn is not None:
            self._copy_btn.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                self._view_only,
            )
        if self._eye_btn is not None:
            # Göz düğmesi yalnızca maske kaldırma yetkisi olanlarda (read/write)
            # etkin; 'Maskeli görüntüleyebilir'de kapalı → parola gizli kalır.
            reveal = self._can_reveal()
            if not reveal:
                self._hidden = True
            self._eye_btn.setEnabled(reveal)
            self._eye_btn.blockSignals(True)
            self._eye_btn.setChecked(reveal and not self._hidden)
            self._eye_btn.blockSignals(False)
            self._refresh_eye()
            self._eye_btn.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                not reveal,
            )
        self._refresh_menu()
        self._sync_echo()

    def _can_reveal(self) -> bool:
        """Maske kaldırılabilir mi? 'Maskeli görüntüleyebilir' (hidden_read)
        alanlarda parola ASLA açığa çıkarılamaz — yalnızca 'read'/'write'."""
        return self._sensitive and self._permission in ("read", "write")

    def _sync_echo(self) -> None:
        if not self.isVisible() and self._permission == "hidden":
            return
        # Maskeli seviye her şeyin önünde: göz düğmesi ne derse desin gizli kalır.
        if self._permission == "hidden_read":
            self._edit.setEchoMode(QLineEdit.EchoMode.Password)
            return
        if self._sensitive and self._eye_btn is not None:
            self._edit.setEchoMode(
                QLineEdit.EchoMode.Password
                if self._hidden
                else QLineEdit.EchoMode.Normal
            )
            return
        if self._sensitive:
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
        copy_text(text)
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
        # Maskeli seviye açığa çıkarılamaz: genel 'Bilgileri göster' bile
        # hidden_read alanı gösteremez.
        if not self._can_reveal():
            hidden = True
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
        if not self._can_reveal():
            # Maskeli seviyede göz düğmesi maske kaldıramaz.
            self._hidden = True
            self._eye_btn.blockSignals(True)
            self._eye_btn.setChecked(False)
            self._eye_btn.blockSignals(False)
            self._refresh_eye()
            self._sync_echo()
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
    """Bir kasa kaydı — İsim sabit; 1. Bilgi + ek alanlar yatay scroll içinde."""

    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)
    restricted_action = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("entryRow")
        self._can_delete = True
        self._can_reorder = False
        self._view_only = False
        self._pw_updated_at = ""
        self._permissions = UserPermissions()
        self._extra_fields: list[CompactField] = []
        self._field_labels: dict[str, str] = {}
        self._drag_start: QPoint | None = None
        self.vault_index: int | None = None
        self.setToolTip(tr("drag_row_tip"))

        row = QHBoxLayout(self)
        row.setContentsMargins(*ROW_MARGINS)
        row.setSpacing(ROW_LAYOUT_SPACING)
        row.setAlignment(_ROW_ALIGN)

        self._name = CompactField(
            field_key="field_name",
            fixed_width=NAME_FIELD_WIDTH,
            sensitive=False,
            with_delete_menu=True,
            responsive_width=True,
            max_width=None,
            primary_field=True,
        )
        self._name.delete_requested.connect(self._confirm_and_remove)
        self._name.width_changed.connect(self._schedule_info_field_layout)
        row.addWidget(self._name, 0, Qt.AlignmentFlag.AlignTop)

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
        self._scroll.setMinimumHeight(ROW_CONTROL_HEIGHT + 14)
        self._scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._scroll.viewport_resized.connect(self._schedule_info_field_layout)

        self._extras_host = QWidget()
        self._extras_host.setObjectName("entryExtrasHost")
        self._extras_layout = QHBoxLayout(self._extras_host)
        self._extras_layout.setContentsMargins(0, 0, 0, 0)
        self._extras_layout.setSpacing(ROW_LAYOUT_SPACING)
        self._extras_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._info1 = CompactField(
            info_index=1,
            fixed_width=INFO_FIELD_WIDTH,
            sensitive=True,
            parent=self._extras_host,
        )
        self._info1.field_remove_requested.connect(self._on_info_field_remove)
        self._extras_layout.addWidget(self._info1, 0, Qt.AlignmentFlag.AlignTop)

        self._field_step_column = QWidget()
        self._field_step_column.setObjectName("fieldStepColumn")
        field_step_layout = QVBoxLayout(self._field_step_column)
        field_step_layout.setContentsMargins(0, 0, 0, 0)
        field_step_layout.setSpacing(2)
        field_step_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )

        # Yalnızca '+' (alan ekle) düğmesi. '-' kaldırıldı: bir bilgi alanı
        # zaten kendi '…' menüsünden kaldırılabildiği için gereksizdi.
        self._add_field_btn = _field_step_button("+", "addFieldBtn")
        self._add_field_btn.clicked.connect(self._add_extra_field)
        field_step_layout.addWidget(self._add_field_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self._extras_layout.addWidget(
            self._field_step_column, 0, Qt.AlignmentFlag.AlignTop
        )

        self._scroll.setWidget(self._extras_host)
        row.addWidget(self._scroll, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)

        self.retranslate()

        self._name.textChanged().connect(self._emit_changed)
        self._info1.textChanged().connect(self._emit_changed)

        self._wire_tab_order()
        self._update_field_step_buttons()
        self._update_info_remove_actions()
        self._schedule_info_field_layout()

    def _confirm_and_remove(self) -> None:
        if self._view_only:
            return
        if not self._can_delete:
            self.restricted_action.emit("restricted_delete_record")
            return
        # Boş kayıtta onay sorma; en az bir alan doluysa sor.
        if not self.to_entry().has_content():
            self.remove_requested.emit(self)
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("confirm_delete_title"))
        box.setText(tr("confirm_delete_text"))
        box.setIcon(QMessageBox.Icon.Question)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        yes_btn = box.button(QMessageBox.StandardButton.Yes)
        no_btn = box.button(QMessageBox.StandardButton.No)
        if yes_btn:
            yes_btn.setText(tr("yes"))
        if no_btn:
            no_btn.setText(tr("no"))
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(self)

    def _field_step_index(self) -> int:
        return self._extras_layout.indexOf(self._field_step_column)

    def _update_field_step_buttons(self) -> None:
        # '-' düğmesi kaldırıldı; '+' her zaman etkin (sınır yok).
        return

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

    def _schedule_info_field_layout(self) -> None:
        QTimer.singleShot(0, self._layout_info_fields)

    def _layout_info_fields(self) -> None:
        row_content_width = (
            self.width() - ROW_MARGINS[0] - ROW_MARGINS[2]
        )
        if row_content_width <= 0:
            return
        default_width = four_column_default_width(row_content_width)
        self._name.set_responsive_base_width(default_width)

        scroll_width = (
            row_content_width - self._name.width() - ROW_LAYOUT_SPACING
        )
        width = three_column_info_width(scroll_width)
        fields = [self._info1, *self._extra_fields]
        for field in fields:
            field.set_compact_width(width)
        # Üç kolona kadar viewport dolar; dördüncü hücre yatay scroll'u başlatır.
        content_width = (
            len(fields) * width
            + FIELD_STEP_BTN_WIDTH
            + len(fields) * ROW_LAYOUT_SPACING
        )
        self._extras_host.setMinimumWidth(max(scroll_width, content_width))
        self._extras_layout.invalidate()

    def _sync_scroll_width(self, *, scroll_to_end: bool = False) -> None:
        self._schedule_info_field_layout()

        def update_scroll():
            bar = self._scroll.horizontalScrollBar()
            if scroll_to_end:
                bar.setValue(bar.maximum())
            else:
                bar.setValue(min(bar.value(), bar.maximum()))

        QTimer.singleShot(0, update_scroll)

    def _add_extra_field(self, *, initial_text: str = "", block_signals: bool = False) -> None:
        if (
            not block_signals
            and not self._view_only
            and self._permissions.info != "write"
        ):
            self.restricted_action.emit("restricted_edit_fields")
            return
        info_index = len(self._extra_fields) + 2
        field = CompactField(
            info_index=info_index,
            fixed_width=INFO_FIELD_WIDTH,
            sensitive=True,
            parent=self._extras_host,
        )
        field._always_show = True
        field.set_custom_label(self._field_labels.get(f"info{info_index}", ""))
        if block_signals:
            field._edit.blockSignals(True)
        field.setText(initial_text)
        if block_signals:
            field._edit.blockSignals(False)

        level = self._permissions.level_for_info_index(info_index)
        field.set_permission(level)
        field.textChanged().connect(self._emit_changed)
        field.field_remove_requested.connect(self._on_info_field_remove)

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
        self._update_info_remove_actions()
        self._emit_changed()

    def _update_info_remove_actions(self) -> None:
        """1. Bilgi yalnızken silinmez; ek alanlar her zaman silinebilir."""
        can_edit = not self._view_only
        self._info1.set_can_remove_field(can_edit and len(self._extra_fields) > 0)
        for field in self._extra_fields:
            field.set_can_remove_field(can_edit)

    def _on_info_field_remove(self, field: CompactField) -> None:
        """Belirli bir bilgi alanını siler; kalanlar kaydırılıp yeniden numaralanır."""
        if self._view_only:
            return
        if field is self._info1:
            if not self._extra_fields:
                return
            # 1. Bilgi silinince 2. Bilgi yukarı kayar.
            promoted = self._extra_fields.pop(0)
            self._info1.setText(promoted.text())
            self._extras_layout.removeWidget(promoted)
            promoted.deleteLater()
            self._renumber_extra_fields()
        elif field in self._extra_fields:
            self._extra_fields.remove(field)
            self._extras_layout.removeWidget(field)
            field.deleteLater()
            self._renumber_extra_fields()
        else:
            return
        self._sync_scroll_width()
        self._wire_tab_order()
        self._update_field_step_buttons()
        self._update_info_remove_actions()
        self._emit_changed()

    def _renumber_extra_fields(self) -> None:
        for offset, field in enumerate(self._extra_fields):
            info_index = offset + 2
            field.set_info_index(info_index)
            field.set_custom_label(self._field_labels.get(f"info{info_index}", ""))
            field.set_permission(self._permissions.level_for_info_index(info_index))

    def _clear_extra_fields(self) -> None:
        for field in self._extra_fields:
            self._extras_layout.removeWidget(field)
            field.deleteLater()
        self._extra_fields.clear()
        self._sync_scroll_width()
        self._update_field_step_buttons()
        self._update_info_remove_actions()

    def apply_permissions(
        self, perms: UserPermissions, *, view_only: bool = False
    ) -> None:
        self._view_only = view_only
        self._permissions = perms
        for field in (self._name, self._info1, *self._extra_fields):
            field.set_view_only(view_only)
        self._name.set_permission(perms.name)
        self._info1.set_permission(perms.level_for_info_index(1))
        for index, field in enumerate(self._extra_fields, start=2):
            field.set_permission(perms.level_for_info_index(index))
        self.setVisible(perms.name != "none" or perms.info != "none")
        self._field_step_column.setVisible(
            not view_only and perms.info != "none"
        )
        # Menü görünür kalır; yetki yoksa tıklama açıklayıcı bildirim üretir.
        self._name.set_can_delete(not view_only)
        fields_restricted = perms.info != "write"
        self._add_field_btn.setProperty("restricted", fields_restricted)
        self._add_field_btn.setToolTip(
            tr("restricted_edit_fields")
            if fields_restricted
            else tr("add_field_tip")
        )
        self._add_field_btn.style().unpolish(self._add_field_btn)
        self._add_field_btn.style().polish(self._add_field_btn)
        self._update_info_remove_actions()
        if view_only:
            self._add_field_btn.setEnabled(False)
        else:
            self._update_field_step_buttons()
        self._sync_scroll_width()
        self._wire_tab_order()

    def apply_field_labels(self, labels: dict[str, str]) -> None:
        self._field_labels = dict(labels)
        self._name.set_custom_label(labels.get("name", ""))
        self._info1.set_custom_label(labels.get("info1", ""))
        for index, field in enumerate(self._extra_fields, start=2):
            field.set_custom_label(labels.get(f"info{index}", ""))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._view_only
            and self._can_reorder
        ):
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if (
            self._drag_start is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._view_only
            and self._can_reorder
            and self.vault_index is not None
        ):
            if (event.position().toPoint() - self._drag_start).manhattanLength() >= 8:
                self._start_drag()
                self._drag_start = None
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        if self.vault_index is None:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(ROW_MIME, str(self.vault_index).encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def set_sensitive_shown(self, shown: bool) -> None:
        for field in self._sensitive_fields():
            if field.isVisible():
                field.set_hidden(not shown)

    def set_can_delete(self, allowed: bool) -> None:
        self._can_delete = allowed
        self._name.set_can_delete(not self._view_only)

    def set_can_reorder(self, allowed: bool) -> None:
        self._can_reorder = allowed
        self.setToolTip(
            tr("drag_row_tip") if allowed else tr("restricted_reorder")
        )

    def retranslate(self) -> None:
        self._name.retranslate()
        self._info1.retranslate()
        for field in self._extra_fields:
            field.retranslate()
        self._add_field_btn.setToolTip(tr("add_field_tip"))

    def _emit_changed(self) -> None:
        self.changed.emit()

    def to_entry(self) -> VaultEntry:
        return VaultEntry(
            name=self._name.text().strip(),
            info1=self._info1.text(),
            more_infos=[field.text() for field in self._extra_fields],
            pw_updated_at=self._pw_updated_at,
        )

    def load_entry(self, entry: VaultEntry) -> None:
        self._name.setText(entry.name)
        self._info1.setText(entry.info1)
        self._pw_updated_at = entry.pw_updated_at
        self._clear_extra_fields()
        for value in entry.more_infos:
            self._add_extra_field(initial_text=value, block_signals=True)
        self._sync_scroll_width()
        self.set_sensitive_shown(False)
        self._apply_pw_age_tooltip()

    def _apply_pw_age_tooltip(self) -> None:
        """info1 alanına parola yaşını tooltip olarak yazar."""
        from kobipass.password_tools import humanize_age

        tip = tr("pw_age_tip", age=humanize_age(self._pw_updated_at))
        self._info1.setToolTip(tip)
        self._info1._edit.setToolTip(tip)

    def block_change_signals(self, block: bool) -> None:
        self._name._edit.blockSignals(block)
        self._info1._edit.blockSignals(block)
        for field in self._extra_fields:
            field._edit.blockSignals(block)
