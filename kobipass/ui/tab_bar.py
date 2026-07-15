"""Kasa çalışma alanının üstündeki Excel benzeri sekme çubuğu.

Sekmeleri (VaultTab) yatay çipler halinde gösterir; aktif sekme vurgulanır,
gizli sekmelerde küçük bir kilit rozeti çıkar. Yöneticiye her çipte küçük bir
'×' ile hızlı kaldırma sunar. Sekme yönetimi (ekle / yeniden adlandır /
gizle-göster / sil) yalnızca yöneticiye açıktır. Bileşen veriyi tutmaz;
sinyallerle ana pencereyi haberdar eder.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QWidget,
)

from kobipass.i18n import tr
from kobipass.ui.icons import icon_lock, icon_plus


class _TabChip(QPushButton):
    """Tek bir sekme çipi. Sol tık → seç, çift tık → yeniden adlandır,
    sağ tık → menü, sağdaki '×' → kaldır (yöneticide)."""

    selected = pyqtSignal(str)
    rename_requested = pyqtSignal(str)
    toggle_hidden_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(
        self,
        tab_id: str,
        name: str,
        *,
        hidden: bool,
        active: bool,
        is_admin: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tab_id = tab_id
        self._is_admin = is_admin
        self.setObjectName("vaultTabChip")
        self.setCheckable(True)
        self.setChecked(active)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("active", active)
        self.setProperty("closable", is_admin)
        self.setText(name)
        if hidden:
            self.setIcon(icon_lock(QColor("#e0b64a"), size=13))
            self.setToolTip(tr("tab_hidden_tip"))
        self.clicked.connect(lambda: self.selected.emit(self._tab_id))

        # Genişliği içeriğe göre sabitle: çok sekme olunca ezilip metin
        # kırpılmasın (fazlası kaydırma çubuğuyla kayar). Font metriği QSS'ten
        # bağımsız güvenli bir üst sınır verir.
        width = self.fontMetrics().horizontalAdvance(name) + 26
        if hidden:
            width += 18
        if is_admin:
            width += 22  # '×' kaldır düğmesi için pay
        self.chip_width = width
        self.setFixedWidth(width)
        self.setFixedHeight(26)

        self._close_btn: QToolButton | None = None
        if is_admin:
            btn = QToolButton(self)
            btn.setObjectName("vaultTabCloseBtn")
            btn.setText("×")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tr("tab_delete"))
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(
                lambda: self.delete_requested.emit(self._tab_id)
            )
            self._close_btn = btn

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._close_btn is not None:
            size = 16
            self._close_btn.setFixedSize(size, size)
            self._close_btn.move(
                self.width() - size - 6, (self.height() - size) // 2
            )

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._is_admin and event.button() == Qt.MouseButton.LeftButton:
            self.rename_requested.emit(self._tab_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        if not self._is_admin:
            return
        menu = QMenu(self)
        act_rename = menu.addAction(tr("tab_rename"))
        act_hidden = menu.addAction(tr("tab_toggle_hidden"))
        menu.addSeparator()
        act_delete = menu.addAction(tr("tab_delete"))
        chosen = menu.exec(event.globalPos())
        if chosen == act_rename:
            self.rename_requested.emit(self._tab_id)
        elif chosen == act_hidden:
            self.toggle_hidden_requested.emit(self._tab_id)
        elif chosen == act_delete:
            self.delete_requested.emit(self._tab_id)


class VaultTabBar(QWidget):
    """Sekme çipleri + (yöneticiye) sekme ekle düğmesi."""

    tab_selected = pyqtSignal(str)
    add_requested = pyqtSignal()
    rename_requested = pyqtSignal(str)
    toggle_hidden_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vaultTabBar")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # Çipler yatay kaydırılabilir bir şeritte; çok sekme olunca küçülmez,
        # kayar.
        self._scroll = QScrollArea()
        self._scroll.setObjectName("vaultTabScroll")
        # widthResizable=False: host kendi doğal genişliğinde kalır (çipler
        # ezilmez), taşınca yatay kaydırma çubuğu çıkar.
        self._scroll.setWidgetResizable(False)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.setFixedHeight(30)  # ince şerit
        self._chips_host = QWidget()
        self._chips_host.setObjectName("vaultTabChipsHost")
        self._chips_layout = QHBoxLayout(self._chips_host)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(3)
        self._scroll.setWidget(self._chips_host)
        outer.addWidget(self._scroll, 1)

        # Düz, çerçevesiz '+' (tarayıcı/Excel usulü) — sekmelerden sonra sabit.
        self._add_btn = QToolButton()
        self._add_btn.setObjectName("vaultTabAddBtn")
        self._add_btn.setIcon(icon_plus(QColor("#8f9bb3"), size=15))
        self._add_btn.setAutoRaise(True)
        self._add_btn.setFixedSize(26, 24)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip(tr("tab_add_tip"))
        self._add_btn.clicked.connect(self.add_requested.emit)
        outer.addWidget(self._add_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._active_chip: _TabChip | None = None

    def set_tabs(self, tabs, active_id: str, *, is_admin: bool) -> None:
        """Çubuğu verilen (görünür) sekmelerle yeniden kurar."""
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._active_chip = None

        total_width = 0
        spacing = self._chips_layout.spacing()
        for tab in tabs:
            chip = _TabChip(
                tab.id,
                tab.name,
                hidden=tab.hidden,
                active=(tab.id == active_id),
                is_admin=is_admin,
            )
            chip.selected.connect(self.tab_selected.emit)
            chip.rename_requested.connect(self.rename_requested.emit)
            chip.toggle_hidden_requested.connect(self.toggle_hidden_requested.emit)
            chip.delete_requested.connect(self.delete_requested.emit)
            self._chips_layout.addWidget(chip, 0)
            total_width += chip.chip_width + spacing
            if tab.id == active_id:
                self._active_chip = chip

        # Host'u tam içerik genişliğinde sabitle → taşınca yatay kaydırma.
        self._chips_host.setFixedWidth(max(1, total_width))
        self._chips_host.setFixedHeight(26)
        self._add_btn.setVisible(is_admin)
        if self._active_chip is not None:
            self._scroll.ensureWidgetVisible(self._active_chip, 40, 0)
