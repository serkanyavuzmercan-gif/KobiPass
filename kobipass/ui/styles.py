"""
kobiPass koyu tema (dark mode) QSS stilleri.
"""

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #1a1d23;
    color: #e8eaed;
    border: 1px solid #2d3340;
}

QWidget#customTitleBar {
    background-color: #1e293b;
    border-bottom: 1px solid #2d3340;
}

QWidget#titleDragArea {
    background-color: transparent;
}

QPushButton#titleBtnMin,
QPushButton#titleBtnMax,
QPushButton#titleBtnClose {
    background-color: transparent;
    color: #9aa0a8;
    border: none;
    border-radius: 0;
    padding: 0;
    font-family: "Segoe UI Symbol", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 400;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#titleBtnMin:hover,
QPushButton#titleBtnMax:hover {
    background-color: #2d3340;
    color: #e8eaed;
}

QPushButton#titleBtnClose:hover {
    background-color: #c42b1c;
    color: #ffffff;
}

QPushButton#titleBtnClose:pressed {
    background-color: #9e2216;
}

QScrollArea {
    border: none;
    background-color: #1a1d23;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0 2px 0 0;
}

QScrollBar:vertical:hover {
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #343a46;
    border-radius: 2px;
    min-height: 24px;
}

QScrollBar:vertical:hover QScrollBar::handle:vertical,
QScrollBar::handle:vertical:hover {
    background: #4d5566;
    border-radius: 5px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0 0 2px 0;
}

QScrollBar:horizontal:hover {
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #343a46;
    border-radius: 2px;
    min-width: 24px;
}

QScrollBar:horizontal:hover QScrollBar::handle:horizontal,
QScrollBar::handle:horizontal:hover {
    background: #4d5566;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}

QScrollArea#entryFieldsScroll QScrollBar:vertical {
    width: 0;
    background: transparent;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 2px 0 0 0;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal:hover {
    height: 12px;
    margin: 0;
}

QScrollArea#entryFieldsScroll QScrollBar::handle:horizontal {
    background: #343a46;
    border-radius: 2px;
    min-width: 24px;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal:hover QScrollBar::handle:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::handle:horizontal:hover {
    background: #4d5566;
    border-radius: 5px;
}

QScrollArea#entryFieldsScroll QScrollBar::add-line:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollArea#entryFieldsScroll QScrollBar::add-page:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::sub-page:horizontal {
    background: none;
}

QScrollArea#entryFieldsScroll {
    background-color: transparent;
}

QWidget#entryExtrasHost {
    background-color: transparent;
}

QWidget#fieldStepColumn {
    background-color: transparent;
}

QToolButton#addFieldBtn,
QToolButton#removeFieldBtn {
    background-color: #2d3340;
    border: 1px solid #3d4450;
    border-radius: 4px;
    font-size: 15px;
    font-weight: 600;
    color: #e8eaed;
    padding: 0;
}

QToolButton#addFieldBtn:hover,
QToolButton#removeFieldBtn:hover:enabled {
    background-color: #383f4d;
    border-color: #4d5566;
}

QToolButton#removeFieldBtn:disabled {
    color: #6b7280;
    border-color: #343a46;
    background-color: #252830;
}

QWidget#entriesContainer {
    background-color: #1a1d23;
}

QWidget#entryRow {
    background-color: #252830;
    border: 1px solid #343a46;
    border-radius: 10px;
}

QLabel {
    color: #9aa0a8;
    font-size: 11px;
    padding: 0 2px;
}

QLabel#rowTitle {
    color: #e8eaed;
    font-size: 12px;
    font-weight: 600;
}

QLabel#brandTitle {
    font-size: 18px;
    font-weight: 700;
    color: #e8eaed;
    padding: 0;
    margin: 0;
}

QLabel#brandSlogan {
    font-size: 11px;
    font-weight: 400;
    color: #94a3b8;
    padding: 0 0 1px 0;
    margin: 0;
}

QLineEdit {
    background-color: #1e2229;
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    min-height: 20px;
}

QLineEdit:focus {
    border-color: #4b68f4;
}

/* Kopyala + giriş kutusu tek çerçeve (satır yüksekliği 38px ile hizalı) */
QWidget#copyGroup {
    border: 2px solid #3d4450;
    border-radius: 8px;
    background-color: #1e2229;
    min-height: 38px;
    max-height: 38px;
}

QWidget#copyGroup[copied="true"] {
    border-color: #4b68f4;
    background-color: #252d3d;
}

QWidget#copyGroup QLineEdit {
    border: none;
    border-radius: 0;
    background-color: transparent;
    padding: 0 8px 0 4px;
    min-height: 0;
    max-height: 32px;
}

QWidget#copyGroup QLineEdit:focus {
    border: none;
    background-color: transparent;
}

QWidget#copyGroup QLineEdit[readOnlyPerm="true"] {
    color: #888ea0;
}

QWidget#copyGroup QToolButton#copyBtn {
    border: none;
    border-right: 1px solid #3d4450;
    border-radius: 5px;
    background-color: #2d3340;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    margin: 0;
}

QWidget#copyGroup QToolButton#copyBtn:hover {
    background-color: #383f4d;
}

QWidget#copyGroup[copied="true"] QToolButton#copyBtn {
    border-right: 1px solid #3d4450;
    background-color: #2a3348;
}

QWidget#copyGroup QToolButton#fieldEyeBtn {
    border: none;
    background: transparent;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    margin: 0;
}

QWidget#copyGroup QToolButton#fieldEyeBtn:hover {
    background-color: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
}

QLineEdit:disabled {
    color: #6b7280;
}

QPushButton {
    background-color: #2d3340;
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #383f4d;
    border-color: #4d5566;
}

QPushButton:pressed {
    background-color: #252830;
}

QPushButton#primaryBtn {
    background-color: #4b68f4;
    border-color: #3854e0;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #3854e0;
    border-color: #2d47c8;
}

QPushButton#primaryBtn:pressed {
    background-color: #2d47c8;
    border-color: #2d47c8;
}

QPushButton#primaryBtn:disabled {
    background-color: #2f3557;
    border-color: #2a2f47;
    color: #9aa0a8;
}

QPushButton#clearBtn {
    background-color: #c42b1c;
    border-color: #a42318;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 18px;
}

QPushButton#clearBtn:hover {
    background-color: #d63526;
    border-color: #c42b1c;
}

QPushButton#clearBtn:pressed {
    background-color: #a42318;
    border-color: #8b1d14;
}

QPushButton#clearBtn:disabled {
    background-color: #5c3030;
    border-color: #4a2828;
    color: #9aa0a8;
}

QPushButton#helpBtn {
    min-width: 0;
    padding: 8px 12px;
}

QPushButton#langBtn {
    min-width: 0;
    max-width: 52px;
    padding: 8px 8px;
}

QPushButton#themeBtn {
    min-width: 0;
    max-width: 56px;
    padding: 8px 8px;
}

QPushButton#securityBadge {
    background-color: transparent;
    color: #4ade80;
    border: 1px solid #22c55e;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#securityBadge:hover {
    background-color: #14532d;
    color: #ffffff;
}

QPushButton#headerSecurityBtn {
    background-color: #1e293b;
    color: #8aabf0;
    border: 1px solid #4b68f4;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton#headerSecurityBtn:hover {
    background-color: #334155;
    border-color: #6b83f6;
    color: #ffffff;
}

QTextBrowser#helpBrowser {
    background-color: transparent;
    color: #e8eaed;
    font-size: 13px;
    border: none;
}

QDialog#helpDialog {
    background-color: #252830;
    border: 1px solid #3d4450;
    border-radius: 8px;
}

/* --- Gömülü yardım paneli (hider Info yapısı) ---
   Panel iki temada da navy chrome üzerindedir; renkler sabittir. */
QWidget#helpPanel {
    background-color: #1e293b;
    border-bottom: 1px solid #0f172a;
}

QLabel#helpStepBadge {
    background-color: #4b68f4;
    color: #ffffff;
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
    padding: 0;
}

QLabel#helpStepText {
    color: #cbd5e1;
    font-size: 13px;
}

QLabel#helpWarnBox {
    background-color: #2d2820;
    color: #c8a84b;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
}

QWidget#helpCreditsCard {
    background-color: #1a2035;
    border-radius: 8px;
}

QLabel#helpCreditsName {
    color: #e8eaed;
    font-size: 15px;
    font-weight: 700;
}

QLabel#helpCreditsBy {
    color: #c8d0e8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#helpCreditsText {
    color: #7a8aac;
    font-size: 12px;
}

QLabel#helpCreditsFooter {
    color: #5a6a8a;
    font-size: 11px;
}

QWidget#helpFeatureCard {
    background-color: #192030;
    border: 1px solid #2a3346;
    border-radius: 8px;
}

QLabel#helpCardTitle {
    color: #e8eaed;
    font-size: 12px;
    font-weight: 700;
}

QLabel#helpCardText {
    color: #94a3b8;
    font-size: 11px;
}

QLabel#helpDialogTitle {
    color: #e8eaed;
    font-size: 16px;
    font-weight: 600;
    padding: 0;
    margin: 0;
}

QPushButton#addRecordBtn {
    background-color: #2d3340;
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 6px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#addRecordBtn:hover {
    background-color: #383f4d;
    border-color: #4d5566;
}

QPushButton#dangerBtn {
    background-color: #4a2c2c;
    border-color: #6b3a3a;
    color: #f0a0a0;
    padding: 0 14px;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#dangerBtn:hover {
    background-color: #5c3838;
}

QToolButton {
    background-color: #2d3340;
    border: 1px solid #3d4450;
    border-radius: 6px;
    padding: 4px;
}

QToolButton:hover {
    background-color: #383f4d;
    border-color: #4d5566;
}

QToolButton:pressed {
    background-color: #252830;
}

QToolButton#copyBtn,
QToolButton#eyeBtn {
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    padding: 0;
}

QToolButton#eyeBtn:checked {
    background-color: #2a3548;
    border-color: #4b68f4;
}

QStatusBar {
    background-color: #1e293b;
    color: #9aa0a8;
    border-top: 1px solid #2d3340;
}

QMessageBox {
    background-color: #252830;
}

QFileDialog {
    background-color: #1a1d23;
}

/* --- QTabWidget (Sekmeler) Karanlık Tema --- */

/* --- Değişiklik Geçmişi tablosu (koyu tema) --- */
QTableWidget {
    background-color: #1e2229;
    alternate-background-color: #23272f;
    color: #e8eaed;
    gridline-color: #2d3340;
    border: 1px solid #3d4450;
    border-radius: 6px;
}

QTableWidget::item {
    color: #e8eaed;
    padding: 4px 6px;
}

QTableWidget::item:selected {
    background-color: #2d3f66;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #252830;
    color: #cbd5e1;
    border: none;
    border-right: 1px solid #2d3340;
    border-bottom: 1px solid #3d4450;
    padding: 6px 8px;
    font-weight: 600;
}

QTableCornerButton::section {
    background-color: #252830;
    border: none;
}

QTabWidget::pane {
    border: 1px solid #3d4450;
    background-color: #1e2229;
    border-radius: 6px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #252830;
    color: #9aa0a8;
    padding: 8px 16px;
    border: 1px solid #3d4450;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e2229;
    color: #e8eaed;
    font-weight: bold;
    border-bottom: 1px solid #1e2229;
}

QTabBar::tab:hover:!selected {
    background-color: #2d3340;
    color: #e8eaed;
}

/* --- Karşılama Ekranı: ikiye bölen paneller --- */
QFrame#landingPanel {
    background-color: #1e2229;
    border: 1px solid #343a46;
    border-radius: 18px;
}

QFrame#landingPanel:hover {
    background-color: #252d3d;
    border: 1px solid #4b68f4;
}

QLabel#landingPanelIcon {
    font-size: 46px;
}

QLabel#landingPanelTitle {
    font-size: 22px;
    font-weight: 700;
    color: #e8eaed;
}

QLabel#landingPanelSubtitle {
    font-size: 13px;
    color: #9aa0a8;
}

QLabel#landingRecentTitle {
    color: #9aa0a8;
    font-size: 13px;
    font-weight: 600;
}

QLabel#landingRecentEmpty {
    color: #6b7280;
    font-size: 12px;
}

QListWidget#landingRecentList {
    background-color: #1e2229;
    border: 1px solid #3d4450;
    border-radius: 10px;
    color: #e8eaed;
    padding: 6px;
}

QListWidget#landingRecentList::item {
    padding: 8px 10px;
    border-radius: 6px;
}

QListWidget#landingRecentList::item:hover,
QListWidget#landingRecentList::item:selected {
    background-color: #2d3340;
}

/* --- Grup kutuları, onay kutuları, açılır menüler (koyu tema) --- */
QGroupBox {
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #cbd5e1;
}

QCheckBox {
    color: #e8eaed;
    spacing: 7px;
    font-weight: 400;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4d5566;
    border-radius: 4px;
    background-color: #1e2229;
}

QCheckBox::indicator:hover {
    border-color: #4b68f4;
}

QCheckBox::indicator:checked {
    background-color: #4b68f4;
    border-color: #4b68f4;
}

QComboBox {
    background-color: #1e2229;
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 18px;
}

QComboBox:hover {
    border-color: #4d5566;
}

QComboBox:focus {
    border-color: #4b68f4;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #1e2229;
    color: #e8eaed;
    border: 1px solid #3d4450;
    border-radius: 6px;
    selection-background-color: #2d3f66;
    selection-color: #ffffff;
    outline: none;
}

/* --- Kullanıcı İzinleri penceresi: kompakt form alanları --- */
QDialog#userAdminDialog QLineEdit {
    padding: 5px 8px;
    min-height: 16px;
}

QDialog#userAdminDialog QGroupBox {
    margin-top: 12px;
    padding-top: 4px;
}

QGroupBox#userSlotCard {
    border-radius: 8px;
}
"""

LIGHT_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f4f6fb;
    color: #1f2937;
    border: 1px solid #dde3f0;
}

QWidget#customTitleBar {
    background-color: #1e293b;
    border-bottom: 1px solid #0f172a;
}

QWidget#titleDragArea {
    background-color: transparent;
}

QPushButton#titleBtnMin,
QPushButton#titleBtnMax,
QPushButton#titleBtnClose {
    background-color: transparent;
    color: #cbd5e1;
    border: none;
    border-radius: 0;
    padding: 0;
    font-family: "Segoe UI Symbol", "Segoe UI", sans-serif;
    font-size: 14px;
    font-weight: 400;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#titleBtnMin:hover,
QPushButton#titleBtnMax:hover {
    background-color: #334155;
    color: #ffffff;
}

QPushButton#titleBtnClose:hover {
    background-color: #dc2626;
    color: #ffffff;
}

QPushButton#titleBtnClose:pressed {
    background-color: #b91c1c;
}

QScrollArea {
    border: none;
    background-color: #f4f6fb;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0 2px 0 0;
}

QScrollBar:vertical:hover {
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #dde3f0;
    border-radius: 2px;
    min-height: 24px;
}

QScrollBar:vertical:hover QScrollBar::handle:vertical,
QScrollBar::handle:vertical:hover {
    background: #9ca3af;
    border-radius: 5px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0 0 2px 0;
}

QScrollBar:horizontal:hover {
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #dde3f0;
    border-radius: 2px;
    min-width: 24px;
}

QScrollBar:horizontal:hover QScrollBar::handle:horizontal,
QScrollBar::handle:horizontal:hover {
    background: #9ca3af;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}

QScrollArea#entryFieldsScroll QScrollBar:vertical {
    width: 0;
    background: transparent;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 2px 0 0 0;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal:hover {
    height: 12px;
    margin: 0;
}

QScrollArea#entryFieldsScroll QScrollBar::handle:horizontal {
    background: #dde3f0;
    border-radius: 2px;
    min-width: 24px;
}

QScrollArea#entryFieldsScroll QScrollBar:horizontal:hover QScrollBar::handle:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::handle:horizontal:hover {
    background: #9ca3af;
    border-radius: 5px;
}

QScrollArea#entryFieldsScroll QScrollBar::add-line:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::sub-line:horizontal {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollArea#entryFieldsScroll QScrollBar::add-page:horizontal,
QScrollArea#entryFieldsScroll QScrollBar::sub-page:horizontal {
    background: none;
}

QScrollArea#entryFieldsScroll {
    background-color: transparent;
}

QWidget#entryExtrasHost {
    background-color: transparent;
}

QWidget#fieldStepColumn {
    background-color: transparent;
}

QToolButton#addFieldBtn,
QToolButton#removeFieldBtn {
    background-color: #edf0fa;
    border: 1px solid #dde3f0;
    border-radius: 4px;
    font-size: 15px;
    font-weight: 600;
    color: #1f2937;
    padding: 0;
}

QToolButton#addFieldBtn:hover,
QToolButton#removeFieldBtn:hover:enabled {
    background-color: #dde3f0;
    border-color: #9ca3af;
}

QToolButton#removeFieldBtn:disabled {
    color: #9ca3af;
    border-color: #edf0fa;
    background-color: #f4f6fb;
}

QWidget#entriesContainer {
    background-color: #f4f6fb;
}

QWidget#entryRow {
    background-color: #ffffff;
    border: 1px solid #dde3f0;
    border-radius: 10px;
}

QLabel {
    color: #6b7280;
    font-size: 11px;
    padding: 0 2px;
}

QLabel#rowTitle {
    color: #1f2937;
    font-size: 12px;
    font-weight: 600;
}

QLabel#brandTitle {
    font-size: 18px;
    font-weight: 700;
    color: #f1f5f9;
    padding: 0;
    margin: 0;
}

QLabel#brandSlogan {
    font-size: 11px;
    font-weight: 400;
    color: #94a3b8;
    padding: 0 0 1px 0;
    margin: 0;
}

QLineEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    min-height: 20px;
}

QLineEdit:focus {
    border-color: #4b68f4;
}

QWidget#copyGroup {
    border: 2px solid #dde3f0;
    border-radius: 8px;
    background-color: #ffffff;
    min-height: 38px;
    max-height: 38px;
}

QWidget#copyGroup[copied="true"] {
    border-color: #4b68f4;
    background-color: #eff6ff;
}

QWidget#copyGroup QLineEdit {
    border: none;
    border-radius: 0;
    background-color: transparent;
    padding: 0 8px 0 4px;
    min-height: 0;
    max-height: 32px;
}

QWidget#copyGroup QLineEdit:focus {
    border: none;
    background-color: transparent;
}

QWidget#copyGroup QLineEdit[readOnlyPerm="true"] {
    color: #6b7280;
}

QWidget#copyGroup QToolButton#copyBtn {
    border: none;
    border-right: 1px solid #dde3f0;
    border-radius: 5px;
    background-color: #edf0fa;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    margin: 0;
}

QWidget#copyGroup QToolButton#copyBtn:hover {
    background-color: #dde3f0;
}

QWidget#copyGroup[copied="true"] QToolButton#copyBtn {
    border-right: 1px solid #dde3f0;
    background-color: #dbeafe;
}

QWidget#copyGroup QToolButton#fieldEyeBtn {
    border: none;
    background: transparent;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    margin: 0;
}

QWidget#copyGroup QToolButton#fieldEyeBtn:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
}

QLineEdit:disabled {
    color: #9ca3af;
}

QPushButton {
    background-color: #edf0fa;
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #dde3f0;
    border-color: #9ca3af;
}

QPushButton:pressed {
    background-color: #f4f6fb;
}

QPushButton#primaryBtn {
    background-color: #4b68f4;
    border-color: #3854e0;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #3854e0;
    border-color: #2d47c8;
}

QPushButton#primaryBtn:pressed {
    background-color: #2d47c8;
    border-color: #2d47c8;
}

QPushButton#primaryBtn:disabled {
    background-color: #b9c4f6;
    border-color: #a9b6f2;
    color: #f4f6fb;
}

QPushButton#clearBtn {
    background-color: #dc2626;
    border-color: #b91c1c;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 18px;
}

QPushButton#clearBtn:hover {
    background-color: #ef4444;
    border-color: #dc2626;
}

QPushButton#clearBtn:pressed {
    background-color: #b91c1c;
    border-color: #991b1b;
}

QPushButton#clearBtn:disabled {
    background-color: #fca5a5;
    border-color: #f87171;
    color: #f4f6fb;
}

QPushButton#helpBtn {
    min-width: 0;
    padding: 8px 12px;
}

QPushButton#langBtn,
QPushButton#themeBtn {
    min-width: 0;
    max-width: 56px;
    padding: 8px 8px;
}

QPushButton#securityBadge {
    background-color: transparent;
    color: #16a34a;
    border: 1px solid #22c55e;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#securityBadge:hover {
    background-color: #dcfce7;
    color: #14532d;
}

QPushButton#headerSecurityBtn {
    background-color: #eef1fe;
    color: #3854e0;
    border: 1px solid #4b68f4;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton#headerSecurityBtn:hover {
    background-color: #4b68f4;
    border-color: #3854e0;
    color: #ffffff;
}

QTextBrowser#helpBrowser {
    background-color: transparent;
    color: #1f2937;
    font-size: 13px;
    border: none;
}

QDialog#helpDialog {
    background-color: #ffffff;
    border: 1px solid #dde3f0;
    border-radius: 8px;
}

/* --- Gömülü yardım paneli — AYDINLIK tema: panel de temayla değişir --- */
QWidget#helpPanel {
    background-color: #ffffff;
    border-bottom: 1px solid #dde3f0;
}

QLabel#helpStepBadge {
    background-color: #4b68f4;
    color: #ffffff;
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
    padding: 0;
}

QLabel#helpStepText {
    color: #374151;
    font-size: 13px;
}

QLabel#helpWarnBox {
    background-color: #fffbeb;
    color: #92400e;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
}

QWidget#helpCreditsCard {
    background-color: #1e293b;
    border-radius: 8px;
}

QLabel#helpCreditsName {
    color: #f1f5f9;
    font-size: 15px;
    font-weight: 700;
}

QLabel#helpCreditsBy {
    color: #c8d0e8;
    font-size: 12px;
    font-weight: 600;
}

QLabel#helpCreditsText {
    color: #94a3b8;
    font-size: 12px;
}

QLabel#helpCreditsFooter {
    color: #64748b;
    font-size: 11px;
}

QWidget#helpFeatureCard {
    background-color: #f4f6fb;
    border: 1px solid #dde3f0;
    border-radius: 8px;
}

QLabel#helpCardTitle {
    color: #111827;
    font-size: 12px;
    font-weight: 700;
}

QLabel#helpCardText {
    color: #4b5563;
    font-size: 11px;
}

QLabel#helpDialogTitle {
    color: #1f2937;
    font-size: 16px;
    font-weight: 600;
    padding: 0;
    margin: 0;
}

QPushButton#addRecordBtn {
    background-color: #edf0fa;
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#addRecordBtn:hover {
    background-color: #dde3f0;
    border-color: #9ca3af;
}

QPushButton#dangerBtn {
    background-color: #fee2e2;
    border-color: #fca5a5;
    color: #b91c1c;
    padding: 0 14px;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#dangerBtn:hover {
    background-color: #fecaca;
}

QToolButton {
    background-color: #edf0fa;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    padding: 4px;
}

QToolButton:hover {
    background-color: #dde3f0;
    border-color: #9ca3af;
}

QToolButton:pressed {
    background-color: #f4f6fb;
}

QToolButton#copyBtn,
QToolButton#eyeBtn {
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    padding: 0;
}

QToolButton#eyeBtn:checked {
    background-color: #dbeafe;
    border-color: #4b68f4;
}

QStatusBar {
    background-color: #1e293b;
    color: #94a3b8;
    border-top: 1px solid #0f172a;
}

QMessageBox {
    background-color: #ffffff;
}

QFileDialog {
    background-color: #f4f6fb;
}

/* --- QTabWidget (Sekmeler) Aydınlık Tema --- */

/* --- Değişiklik Geçmişi tablosu (aydınlık tema) --- */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f4f6fb;
    color: #1f2937;
    gridline-color: #e5e9f2;
    border: 1px solid #dde3f0;
    border-radius: 6px;
}

QTableWidget::item {
    color: #1f2937;
    padding: 4px 6px;
}

QTableWidget::item:selected {
    background-color: #dbe4fd;
    color: #1f2937;
}

QHeaderView::section {
    background-color: #eef1fa;
    color: #374151;
    border: none;
    border-right: 1px solid #dde3f0;
    border-bottom: 1px solid #dde3f0;
    padding: 6px 8px;
    font-weight: 600;
}

QTableCornerButton::section {
    background-color: #eef1fa;
    border: none;
}

QTabWidget::pane {
    border: 1px solid #dde3f0;
    background-color: #ffffff;
    border-radius: 6px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #f4f6fb;
    color: #6b7280;
    padding: 8px 16px;
    border: 1px solid #dde3f0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1f2937;
    font-weight: bold;
    border-bottom: 1px solid #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #edf0fa;
    color: #1f2937;
}

/* --- Karşılama Ekranı: ikiye bölen paneller --- */
QFrame#landingPanel {
    background-color: #ffffff;
    border: 1px solid #dde3f0;
    border-radius: 18px;
}

QFrame#landingPanel:hover {
    background-color: #eef1fe;
    border: 1px solid #4b68f4;
}

QLabel#landingPanelIcon {
    font-size: 46px;
}

QLabel#landingPanelTitle {
    font-size: 22px;
    font-weight: 700;
    color: #1f2937;
}

QLabel#landingPanelSubtitle {
    font-size: 13px;
    color: #6b7280;
}

QLabel#landingRecentTitle {
    color: #4b5563;
    font-size: 13px;
    font-weight: 600;
}

QLabel#landingRecentEmpty {
    color: #9ca3af;
    font-size: 12px;
}

QListWidget#landingRecentList {
    background-color: #ffffff;
    border: 1px solid #dde3f0;
    border-radius: 10px;
    color: #1f2937;
    padding: 6px;
}

QListWidget#landingRecentList::item {
    padding: 8px 10px;
    border-radius: 6px;
}

QListWidget#landingRecentList::item:hover,
QListWidget#landingRecentList::item:selected {
    background-color: #eff6ff;
}

/* --- Grup kutuları, onay kutuları, açılır menüler (aydınlık tema) --- */
QGroupBox {
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #374151;
}

QCheckBox {
    color: #1f2937;
    spacing: 7px;
    font-weight: 400;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cdd4ee;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #4b68f4;
}

QCheckBox::indicator:checked {
    background-color: #4b68f4;
    border-color: #4b68f4;
}

QComboBox {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 18px;
}

QComboBox:hover {
    border-color: #b9c4f6;
}

QComboBox:focus {
    border-color: #4b68f4;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #dde3f0;
    border-radius: 6px;
    selection-background-color: #dbe4fd;
    selection-color: #1f2937;
    outline: none;
}

/* --- Kullanıcı İzinleri penceresi: kompakt form alanları --- */
QDialog#userAdminDialog QLineEdit {
    padding: 5px 8px;
    min-height: 16px;
}

QDialog#userAdminDialog QGroupBox {
    margin-top: 12px;
    padding-top: 4px;
}

QGroupBox#userSlotCard {
    border-radius: 8px;
}
"""
