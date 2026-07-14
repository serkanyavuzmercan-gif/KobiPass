"""KobiPass premium karşılama ekranı — marka alanı + kasa işlem paneli."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from kobipass.i18n import i18n, tr
from kobipass.resources import hero_left_pixmap, logo_pixmap
from kobipass.settings import get_recent_files
from kobipass.ui.icons import (
    icon_file_new,
    icon_folder_open,
    icon_home,
    icon_info,
    icon_key,
    icon_shield,
    icon_sun,
    icon_theme,
)

_FEATURE_ACCENT = QColor("#8296ff")
_HERO_RADIUS = 22
from kobipass.ui.theme import theme_manager


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


class LandingPage(QWidget):
    recent_file_chosen = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("landingPage")
        self._latest_path = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 12, 22, 22)
        outer.setSpacing(14)

        # Üstte yalnız yardımcı işlemler; ana hiyerarşiye rakip olmaz.
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addStretch()

        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("themeBtn")
        self.btn_theme.setFixedWidth(44)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_theme_icon()
        theme_manager.theme_changed.connect(self._update_theme_icon)

        self.btn_lang = QPushButton("TR/EN")
        self.btn_lang.setObjectName("langBtn")
        self.btn_lang.setFixedWidth(50)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_security = QPushButton()
        self.btn_security.setObjectName("headerSecurityBtn")
        self.btn_security.setIcon(icon_shield())
        self.btn_security.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_about = QPushButton()
        self.btn_about.setObjectName("helpBtn")
        self.btn_about.setIcon(icon_info())
        self.btn_about.setCursor(Qt.CursorShape.PointingHandCursor)

        top.addWidget(self.btn_theme)
        top.addWidget(self.btn_lang)
        top.addWidget(self.btn_security)
        top.addWidget(self.btn_about)
        outer.addLayout(top)

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

        self._actions_title = QLabel()
        self._actions_title.setObjectName("landingActionsTitle")
        actions_layout.addWidget(self._actions_title)

        self._actions_subtitle = QLabel()
        self._actions_subtitle.setObjectName("landingActionsSubtitle")
        self._actions_subtitle.setWordWrap(True)
        actions_layout.addWidget(self._actions_subtitle)

        self._latest_card = QFrame()
        self._latest_card.setObjectName("landingLatestCard")
        self._latest_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        latest_layout = QVBoxLayout(self._latest_card)
        latest_layout.setContentsMargins(18, 16, 18, 16)
        latest_layout.setSpacing(6)

        self._latest_kicker = QLabel()
        self._latest_kicker.setObjectName("landingLatestKicker")
        latest_layout.addWidget(self._latest_kicker)

        self._latest_name = QLabel()
        self._latest_name.setObjectName("landingLatestName")
        self._latest_name.setWordWrap(True)
        latest_layout.addWidget(self._latest_name)

        self._latest_path_label = QLabel()
        self._latest_path_label.setObjectName("landingLatestPath")
        self._latest_path_label.setWordWrap(True)
        latest_layout.addWidget(self._latest_path_label)

        self._open_latest = QPushButton()
        self._open_latest.setObjectName("landingPrimaryBtn")
        self._open_latest.setIcon(icon_folder_open(size=20))
        self._open_latest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_latest.clicked.connect(self._open_latest_path)
        latest_layout.addWidget(self._open_latest)
        actions_layout.addWidget(self._latest_card)

        self.btn_open_file = QPushButton()
        self.btn_open_file.setObjectName("landingSecondaryBtn")
        self.btn_open_file.setIcon(icon_folder_open(size=20))
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.btn_open_file)

        self.btn_create_file = QPushButton()
        self.btn_create_file.setObjectName("landingCreateBtn")
        self.btn_create_file.setIcon(icon_file_new(size=22))
        self.btn_create_file.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(self.btn_create_file)

        self._recent_title = QLabel()
        self._recent_title.setObjectName("landingRecentTitle")
        actions_layout.addWidget(self._recent_title)

        self._recent_list = QListWidget()
        self._recent_list.setObjectName("landingRecentList")
        self._recent_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recent_list.setMaximumHeight(150)
        self._recent_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        self._recent_list.itemClicked.connect(self._on_recent_activated)
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

    def _update_theme_icon(self) -> None:
        self.btn_theme.setIcon(
            icon_sun() if theme_manager.is_dark() else icon_theme()
        )

    def _open_latest_path(self) -> None:
        if self._latest_path:
            self.recent_file_chosen.emit(self._latest_path)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_file_chosen.emit(str(path))

    def refresh_recent(self) -> None:
        self._recent_list.clear()
        recent = [p for p in get_recent_files() if Path(p).exists()]
        self._latest_path = recent[0] if recent else ""
        self._latest_card.setVisible(bool(recent))
        self._recent_list.setVisible(bool(recent))
        self._recent_title.setVisible(bool(recent))
        self._recent_empty.setVisible(not recent)

        if recent:
            latest = Path(recent[0])
            self._latest_name.setText(latest.name)
            self._latest_path_label.setText(str(latest.parent))
            self._latest_path_label.setToolTip(str(latest))
        for path in recent[:5]:
            item = QListWidgetItem(Path(path).name)
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._recent_list.addItem(item)

    def retranslate(self) -> None:
        self._apply_hero_image()
        self.btn_theme.setToolTip(tr("btn_theme_tip"))
        self.btn_lang.setToolTip(tr("btn_lang_tip"))
        self.btn_security.setText(tr("landing_security"))
        self.btn_security.setToolTip(tr("security_badge_tip"))
        self.btn_about.setText(tr("about_us_title"))
        self.btn_about.setToolTip(tr("btn_about_tip"))

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
        self.btn_open_file.setText(tr("landing_open_other"))
        self.btn_create_file.setText(tr("landing_create_title"))
        self.btn_create_file.setToolTip(tr("landing_create_sub"))
        self._recent_title.setText(tr("landing_recent"))
        self._recent_empty.setText(tr("landing_recent_empty"))
