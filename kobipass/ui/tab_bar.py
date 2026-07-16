"""Kasa çalışma alanının üstündeki Excel benzeri sekme çubuğu.

Sekmeleri (VaultTab) yatay çipler halinde gösterir; aktif sekme vurgulanır,
gizli sekmelerde küçük bir kilit rozeti çıkar. Yöneticiye her çipte küçük bir
'×' ile hızlı kaldırma sunar. Sekme yönetimi (ekle / yeniden adlandır /
gizle-göster / sil) yalnızca yöneticiye açıktır. Bileşen veriyi tutmaz;
sinyallerle ana pencereyi haberdar eder.
"""

from __future__ import annotations

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
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

# Sürükle-bırak ile sekme sıralama için MIME türü.
_TAB_MIME = "application/x-kobipass-tab"


class _TabChip(QPushButton):
    """Tek bir sekme çipi. Sol tık → seç, çift tık → yeniden adlandır,
    sağ tık → menü, sağdaki '×' → kaldır (yöneticide). Yöneticide sürüklenerek
    yeniden sıralanabilir."""

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
        # bağımsız güvenli bir üst sınır verir. (14px yatay dolgu × 2 + pay.)
        width = self.fontMetrics().horizontalAdvance(name) + 32
        if hidden:
            width += 22  # kilit ikonu + boşluk
        if is_admin:
            width += 24  # '×' kaldır düğmesi için pay
        self.chip_width = width
        self.setFixedWidth(width)
        self.setFixedHeight(30)

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

        self._press_pos: QPoint | None = None
        self._dragging = False

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._close_btn is not None:
            size = 16
            self._close_btn.setFixedSize(size, size)
            self._close_btn.move(
                self.width() - size - 8, (self.height() - size) // 2
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # Yönetici sekmeyi sürükleyerek yeniden sıralayabilir.
        if (
            self._is_admin
            and self._press_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            dist = (event.position().toPoint() - self._press_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._dragging = True
                self.setChecked(True)  # tıklama işareti geri kalmasın
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData(_TAB_MIME, self._tab_id.encode("utf-8"))
                drag.setMimeData(mime)
                drag.setPixmap(self.grab())
                drag.setHotSpot(event.position().toPoint())
                drag.exec(Qt.DropAction.MoveAction)
                self._press_pos = None
                return
        super().mouseMoveEvent(event)

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


class _ChipsHost(QWidget):
    """Çipleri taşıyan şerit; sürüklenen sekmenin bırakıldığı konumu hesaplar."""

    reorder_requested = pyqtSignal(str, int)  # kaynak_id, hedef_index

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(_TAB_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(_TAB_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(_TAB_MIME):
            return
        source_id = bytes(event.mimeData().data(_TAB_MIME)).decode("utf-8")
        x = int(event.position().x())
        chips = sorted(self.findChildren(_TabChip), key=lambda c: c.x())
        insert_index = len(chips)
        for i, chip in enumerate(chips):
            if x < chip.x() + chip.width() / 2:
                insert_index = i
                break
        event.acceptProposedAction()
        self.reorder_requested.emit(source_id, insert_index)


class VaultTabBar(QWidget):
    """Sekme çipleri + (yöneticiye) sekme ekle düğmesi."""

    tab_selected = pyqtSignal(str)
    add_requested = pyqtSignal()
    rename_requested = pyqtSignal(str)
    toggle_hidden_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    reordered = pyqtSignal(list)  # yeni sekme id sırası

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
        self._scroll.setFixedHeight(34)  # ince şerit
        self._chips_host = _ChipsHost()
        self._chips_host.setObjectName("vaultTabChipsHost")
        self._chips_host.reorder_requested.connect(self._handle_reorder)
        self._chips_layout = QHBoxLayout(self._chips_host)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(5)
        self._scroll.setWidget(self._chips_host)
        outer.addWidget(self._scroll, 1)

        # Düz, çerçevesiz '+' (tarayıcı/Excel usulü) — son sekmenin hemen
        # yanında durur, sekmelerle birlikte kayar. Şerit temizlenirken
        # silinmemesi için ayrı tutulur.
        self._add_btn = QToolButton()
        self._add_btn.setObjectName("vaultTabAddBtn")
        self._add_btn.setIcon(icon_plus(QColor("#8f9bb3"), size=15))
        self._add_btn.setAutoRaise(True)
        self._add_btn.setFixedSize(28, 30)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setToolTip(tr("tab_add_tip"))
        self._add_btn.clicked.connect(self.add_requested.emit)

        self._active_chip: _TabChip | None = None

    def _handle_reorder(self, source_id: str, insert_index: int) -> None:
        chips = sorted(
            self._chips_host.findChildren(_TabChip), key=lambda c: c.x()
        )
        ids = [chip._tab_id for chip in chips]
        if source_id not in ids:
            return
        original = list(ids)
        src = ids.index(source_id)
        ids.pop(src)
        if src < insert_index:
            insert_index -= 1
        insert_index = max(0, min(insert_index, len(ids)))
        ids.insert(insert_index, source_id)
        if ids != original:
            self.reordered.emit(ids)

    def set_tabs(self, tabs, active_id: str, *, is_admin: bool) -> None:
        """Çubuğu verilen (görünür) sekmelerle yeniden kurar."""
        # Sürükle-bırak sıralama yalnızca yöneticide.
        self._chips_host.setAcceptDrops(is_admin)
        # '+' düğmesini korumak için önce şeritten çıkar ve gizle. DİKKAT:
        # burada setParent(None) ÇAĞIRMA — görünür bir düğmeyi bir an üst-seviye
        # pencereye çevirir ve ekranın sol-üstünde boş bir kutu olarak
        # parlar. removeWidget zaten düzenden çıkarır; ebeveyni host kalır.
        self._chips_layout.removeWidget(self._add_btn)
        self._add_btn.hide()
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

        # '+' düğmesini son sekmenin hemen yanına yerleştir (yalnızca yönetici).
        self._add_btn.setVisible(is_admin)
        if is_admin:
            self._chips_layout.addWidget(
                self._add_btn, 0, Qt.AlignmentFlag.AlignVCenter
            )
            total_width += self._add_btn.width() + spacing

        # Host'u tam içerik genişliğinde sabitle → taşınca yatay kaydırma.
        self._chips_host.setFixedWidth(max(1, total_width))
        self._chips_host.setFixedHeight(30)
        if self._active_chip is not None:
            self._scroll.ensureWidgetVisible(self._active_chip, 40, 0)
