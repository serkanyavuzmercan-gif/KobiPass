"""KobiPass premium karşılama ekranı — marka alanı + kasa işlem paneli."""

from __future__ import annotations

from pathlib import Path

from datetime import datetime

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import i18n, tr
from kobipass.resources import hero_left_pixmap, logo_pixmap
from kobipass.settings import (
    clear_recent_files,
    get_recent_files,
    remove_recent_file,
)
from kobipass.ui.icons import (
    icon_arrow_right,
    icon_clock,
    icon_file,
    icon_file_new,
    icon_folder_open,
    icon_home,
    icon_key,
    icon_lock,
    icon_more,
    icon_shield,
    icon_trash,
)

_FEATURE_ACCENT = QColor("#8296ff")
_HERO_RADIUS = 22


class HeroPanel(QFrame):
    """Sol hero paneli: arka plana (kasa+fon) görsel basar, üstüne vektörel
    yazılar/kartlar çocuk widget olarak gelir. Görsel yoksa QSS degrade fon
    kullanılır. Görsel "cover" biçiminde ölçeklenip yuvarlak köşeye kırpılır.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bg = QPixmap()

    def set_background(self, pm: QPixmap) -> None:
        self._bg = pm
        self.update()

    def has_background(self) -> bool:
        return not self._bg.isNull()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)  # QSS degrade fon + kenarlık (yedek)
        if self._bg.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect().adjusted(1, 1, -1, -1)  # kenarlığı koru
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), _HERO_RADIUS - 1, _HERO_RADIUS - 1)
        painter.setClipPath(path)
        scaled = self._bg.scaled(
            rect.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = rect.x() + (rect.width() - scaled.width()) // 2
        y = rect.y() + (rect.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


_NAV_ACCENT = QColor("#8296ff")


class NavRow(QFrame):
    """İkon + metin + sağ ok içeren tıklanabilir satır (dosya seç / oluştur)."""

    clicked = pyqtSignal()

    def __init__(self, icon_pm: QPixmap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingNavRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(icon_pm)
        lay.addWidget(icon, 0)
        self._label = QLabel()
        self._label.setObjectName("landingNavLabel")
        lay.addWidget(self._label, 0)
        lay.addStretch(1)
        arrow = QLabel()
        arrow.setPixmap(icon_arrow_right(QColor("#7f8aa6"), size=18).pixmap(18, 18))
        lay.addWidget(arrow, 0)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentRow(QWidget):
    """Son açılanlar satırı: belge ikonu + ad/yol + tarih + kebab menü."""

    open_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        p = Path(path)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 11, 8, 11)
        lay.setSpacing(11)

        icon_tile = QLabel()
        icon_tile.setObjectName("recentRowIcon")
        icon_tile.setFixedSize(36, 36)
        icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_tile.setPixmap(icon_file(QColor("#8296ff"), size=18).pixmap(18, 18))
        lay.addWidget(icon_tile, 0)

        text = QVBoxLayout()
        text.setSpacing(3)
        name = QLabel(p.name)
        name.setObjectName("recentRowName")
        path_lbl = QLabel(str(p.parent))
        path_lbl.setObjectName("recentRowPath")
        text.addWidget(name)
        text.addWidget(path_lbl)
        lay.addLayout(text, 1)

        stamp = QLabel(self._format_time(p))
        stamp.setObjectName("recentRowStamp")
        lay.addWidget(stamp, 0)

        menu_btn = QPushButton()
        menu_btn.setObjectName("recentRowMenu")
        menu_btn.setFixedSize(26, 26)
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setIcon(icon_more(QColor("#8994ad"), size=18))
        menu_btn.clicked.connect(self._show_menu)
        self._menu_btn = menu_btn
        lay.addWidget(menu_btn, 0)

    def _format_time(self, p: Path) -> str:
        try:
            ts = datetime.fromtimestamp(p.stat().st_mtime)
        except OSError:
            return ""
        now = datetime.now()
        clock = ts.strftime("%H:%M")
        if ts.date() == now.date():
            return tr("date_today", time=clock)
        delta = (now.date() - ts.date()).days
        if delta == 1:
            return tr("date_yesterday", time=clock)
        return ts.strftime("%d.%m.%Y")

    def _show_menu(self) -> None:
        menu = QMenu(self)
        act_open = menu.addAction(tr("recent_open"))
        act_remove = menu.addAction(tr("recent_remove"))
        chosen = menu.exec(
            self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomLeft())
        )
        if chosen == act_open:
            self.open_requested.emit(self._path)
        elif chosen == act_remove:
            self.remove_requested.emit(self._path)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self._path)
        super().mousePressEvent(event)


class LandingPage(QWidget):
    recent_file_chosen = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingPage")
        self._latest_path = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        outer.setSpacing(14)

        # Tema/dil/güvenlik/hakkında düğmeleri artık üst başlık çubuğunda.
        content = QHBoxLayout()
        content.setSpacing(20)
        content.setContentsMargins(0, 0, 0, 0)

        # Sol: arka planda kasa+fon görseli, üstünde vektörel anlatı/kartlar.
        hero = HeroPanel()
        hero.setObjectName("landingHero")
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._hero = hero
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(44, 42, 44, 40)
        hero_layout.setSpacing(14)

        logo = QLabel()
        logo.setObjectName("landingHeroLogo")
        logo.setPixmap(logo_pixmap(96))
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        hero_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignLeft)
        hero_layout.addStretch(1)

        # Yazı ve kartlar solda kalsın; sağ tarafı (fondaki kasa) açık bırak.
        self._eyebrow = QLabel()
        self._eyebrow.setObjectName("landingEyebrow")
        hero_layout.addWidget(self._eyebrow)

        self._hero_title = QLabel()
        self._hero_title.setObjectName("landingHeroTitle")
        self._hero_title.setWordWrap(True)
        hero_layout.addWidget(self._hero_title)

        self._hero_subtitle = QLabel()
        self._hero_subtitle.setObjectName("landingHeroSubtitle")
        self._hero_subtitle.setWordWrap(True)
        self._hero_subtitle.setMaximumWidth(430)
        hero_layout.addWidget(self._hero_subtitle)

        hero_layout.addStretch(1)

        # Özellik kartları: ikon + kalın başlık + açıklama (solda).
        self._feature_cards: list[dict] = []
        feat_row = QHBoxLayout()
        feat_row.setSpacing(12)
        for icon_fn, tkey, dkey in (
            (icon_shield, "feature_aes_title", "feature_aes_desc"),
            (icon_key, "feature_argon_title", "feature_argon_desc"),
            (icon_home, "feature_local_title", "feature_local_desc"),
        ):
            card = self._make_feature_card(icon_fn, tkey, dkey)
            feat_row.addWidget(card["frame"], 1)
        feat_wrap = QHBoxLayout()
        feat_wrap.addLayout(feat_row, 62)
        feat_wrap.addStretch(38)
        hero_layout.addLayout(feat_wrap)

        wide = self._make_feature_card(
            icon_shield, "feature_trust_title", "feature_trust_desc", wide=True
        )
        wide_wrap = QHBoxLayout()
        wide_wrap.addWidget(wide["frame"], 62)
        wide_wrap.addStretch(38)
        hero_layout.addLayout(wide_wrap)
        hero_layout.addStretch(1)

        # Sağ: birincil kasa işlemleri.
        actions = QFrame()
        actions.setObjectName("landingActions")
        actions.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        actions.setMinimumWidth(380)
        actions.setMaximumWidth(500)
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(28, 28, 28, 28)
        actions_layout.setSpacing(12)

        access_header = QHBoxLayout()
        access_header.setSpacing(14)
        access_lock = QLabel()
        access_lock.setObjectName("landingAccessLock")
        access_lock.setFixedSize(52, 52)
        access_lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        access_lock.setPixmap(icon_lock(QColor("#aeb9ff"), size=26).pixmap(26, 26))
        access_header.addWidget(access_lock, 0, Qt.AlignmentFlag.AlignTop)

        access_text = QVBoxLayout()
        access_text.setSpacing(4)
        self._actions_title = QLabel()
        self._actions_title.setObjectName("landingActionsTitle")
        access_text.addWidget(self._actions_title)
        self._actions_subtitle = QLabel()
        self._actions_subtitle.setObjectName("landingActionsSubtitle")
        self._actions_subtitle.setWordWrap(True)
        access_text.addWidget(self._actions_subtitle)
        access_header.addLayout(access_text, 1)
        actions_layout.addLayout(access_header)

        # ── Son kasa kartı ───────────────────────────────────────────────
        self._latest_card = QFrame()
        self._latest_card.setObjectName("landingLatestCard")
        self._latest_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        latest_layout = QVBoxLayout(self._latest_card)
        latest_layout.setContentsMargins(18, 16, 18, 16)
        latest_layout.setSpacing(10)

        latest_top = QHBoxLayout()
        latest_top.setSpacing(10)
        latest_text = QVBoxLayout()
        latest_text.setSpacing(4)

        kicker_row = QHBoxLayout()
        kicker_row.setSpacing(6)
        kicker_clock = QLabel()
        kicker_clock.setPixmap(icon_clock(QColor("#8296ff"), size=15).pixmap(15, 15))
        kicker_row.addWidget(kicker_clock, 0)
        self._latest_kicker = QLabel()
        self._latest_kicker.setObjectName("landingLatestKicker")
        kicker_row.addWidget(self._latest_kicker, 0)
        kicker_row.addStretch(1)
        latest_text.addLayout(kicker_row)

        self._latest_name = QLabel()
        self._latest_name.setObjectName("landingLatestName")
        self._latest_name.setWordWrap(True)
        latest_text.addWidget(self._latest_name)

        self._latest_path_label = QLabel()
        self._latest_path_label.setObjectName("landingLatestPath")
        self._latest_path_label.setWordWrap(True)
        latest_text.addWidget(self._latest_path_label)
        latest_top.addLayout(latest_text, 1)

        self._latest_doc = QLabel()
        self._latest_doc.setObjectName("landingLatestDoc")
        self._latest_doc.setFixedSize(46, 46)
        self._latest_doc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._latest_doc.setPixmap(icon_file(QColor("#aeb9ff"), size=22).pixmap(22, 22))
        latest_top.addWidget(self._latest_doc, 0, Qt.AlignmentFlag.AlignTop)
        latest_layout.addLayout(latest_top)

        self._open_latest = QPushButton()
        self._open_latest.setObjectName("landingPrimaryBtn")
        self._open_latest.setIcon(icon_lock(QColor("#ffffff"), size=18))
        self._open_latest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_latest.clicked.connect(self._open_latest_path)
        latest_layout.addWidget(self._open_latest)
        actions_layout.addWidget(self._latest_card)

        # ── Dosya seç / oluştur (ok'lu satırlar) ─────────────────────────
        self.btn_open_file = NavRow(
            icon_folder_open(_NAV_ACCENT, size=20).pixmap(20, 20)
        )
        self.btn_open_file.setObjectName("landingNavRow")
        actions_layout.addWidget(self.btn_open_file)

        self.btn_create_file = NavRow(
            icon_file_new(_NAV_ACCENT, size=20).pixmap(20, 20)
        )
        actions_layout.addWidget(self.btn_create_file)

        # ── Son açılanlar başlığı + Tümünü temizle ───────────────────────
        self._recent_header = QWidget()
        recent_header = QHBoxLayout(self._recent_header)
        recent_header.setContentsMargins(0, 6, 0, 0)
        recent_header.setSpacing(6)
        recent_clock = QLabel()
        recent_clock.setPixmap(icon_clock(QColor("#8994ad"), size=15).pixmap(15, 15))
        recent_header.addWidget(recent_clock, 0)
        self._recent_title = QLabel()
        self._recent_title.setObjectName("landingRecentTitle")
        recent_header.addWidget(self._recent_title, 0)
        recent_header.addStretch(1)
        self._clear_recent = QPushButton()
        self._clear_recent.setObjectName("landingClearRecent")
        self._clear_recent.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_recent.setIcon(icon_trash(QColor("#8994ad"), size=15))
        self._clear_recent.clicked.connect(self._on_clear_recent)
        recent_header.addWidget(self._clear_recent, 0)
        actions_layout.addWidget(self._recent_header)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("landingRecentList")
        self._recent_list.setSelectionMode(
            QListWidget.SelectionMode.NoSelection
        )
        self._recent_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        actions_layout.addWidget(self._recent_list, 1)

        self._recent_empty = QLabel()
        self._recent_empty.setObjectName("landingRecentEmpty")
        self._recent_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions_layout.addWidget(self._recent_empty)
        actions_layout.addStretch(1)

        content.addWidget(hero, 5)
        content.addWidget(actions, 4)
        outer.addLayout(content, 1)

        self._apply_hero_image()
        self.retranslate()
        self.refresh_recent()

    def _apply_hero_image(self) -> None:
        """Mevcut dile göre hero arka plan görselini (kasa+fon) yükler."""
        pm = hero_left_pixmap(english=not i18n.is_tr())
        self._hero.set_background(pm)

    def _make_feature_card(
        self, icon_fn, title_key: str, desc_key: str, *, wide: bool = False
    ) -> dict:
        frame = QFrame()
        frame.setObjectName(
            "landingFeatureCardWide" if wide else "landingFeatureCard"
        )
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("landingFeatureIcon")
        icon_lbl.setPixmap(icon_fn(_FEATURE_ACCENT, size=24).pixmap(24, 24))
        icon_lbl.setFixedSize(38, 38)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl, 0)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel()
        title.setObjectName("landingFeatureTitle")
        desc = QLabel()
        desc.setObjectName("landingFeatureDesc")
        desc.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(desc)
        lay.addLayout(text, 1)

        card = {"frame": frame, "title": title, "desc": desc,
                "tkey": title_key, "dkey": desc_key}
        self._feature_cards.append(card)
        return card

    def _open_latest_path(self) -> None:
        if self._latest_path:
            self.recent_file_chosen.emit(self._latest_path)

    def _on_clear_recent(self) -> None:
        clear_recent_files()
        self.refresh_recent()

    def _on_remove_recent(self, path: str) -> None:
        remove_recent_file(path)
        self.refresh_recent()

    def refresh_recent(self) -> None:
        self._recent_list.clear()
        recent = [p for p in get_recent_files() if Path(p).exists()]
        self._latest_path = recent[0] if recent else ""
        self._latest_card.setVisible(bool(recent))
        self._recent_list.setVisible(bool(recent))
        self._recent_header.setVisible(bool(recent))
        self._recent_empty.setVisible(not recent)

        if recent:
            latest = Path(recent[0])
            self._latest_name.setText(latest.name)
            self._latest_path_label.setText(str(latest.parent))
            self._latest_path_label.setToolTip(str(latest))
        for path in recent[:5]:
            row = RecentRow(path)
            row.open_requested.connect(self.recent_file_chosen.emit)
            row.remove_requested.connect(self._on_remove_recent)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, max(64, row.sizeHint().height())))
            self._recent_list.addItem(item)
            self._recent_list.setItemWidget(item, row)

    def retranslate(self) -> None:
        self._apply_hero_image()

        self._eyebrow.setText(tr("landing_eyebrow"))
        self._hero_title.setText(tr("landing_hero_title"))
        self._hero_subtitle.setText(tr("landing_hero_subtitle"))
        for card in self._feature_cards:
            card["title"].setText(tr(card["tkey"]))
            card["desc"].setText(tr(card["dkey"]))

        self._actions_title.setText(tr("landing_actions_title"))
        self._actions_subtitle.setText(tr("landing_actions_subtitle"))
        self._latest_kicker.setText(tr("landing_latest_kicker"))
        self._open_latest.setText(tr("landing_open_latest"))
        self.btn_open_file.set_text(tr("landing_open_other"))
        self.btn_create_file.set_text(tr("landing_create_title"))
        self.btn_create_file.setToolTip(tr("landing_create_sub"))
        self._recent_title.setText(tr("landing_recent"))
        self._clear_recent.setText(tr("landing_clear_recent"))
        self._recent_empty.setText(tr("landing_recent_empty"))
