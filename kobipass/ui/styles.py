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
    background-color: #15181d;
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
    border-radius: 8px;
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
    color: #6b7280;
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
    border-color: #3d7eea;
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
    border-color: #4a85e0;
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
    background-color: #e07020;
    border-color: #c45e15;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #f08030;
    border-color: #e07020;
}

QPushButton#primaryBtn:pressed {
    background-color: #c45e15;
    border-color: #a84e10;
}

QPushButton#primaryBtn:disabled {
    background-color: #5c4030;
    border-color: #4a3528;
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
    color: #38bdf8;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton#headerSecurityBtn:hover {
    background-color: #0c4a6e;
    border-color: #38bdf8;
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
    border-color: #3d7eea;
}

QStatusBar {
    background-color: #15181d;
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

/* --- Karşılama Ekranı Kare Butonları --- */
QPushButton#landingSquareBtn {
    font-size: 18px;
    font-weight: bold;
    border-radius: 20px;
    background-color: #1e2229;
    border: 2px solid #3d4450;
    color: #e8eaed;
}

QPushButton#landingSquareBtn:hover {
    background-color: #252830;
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton#landingSquareBtn:pressed {
    background-color: #1a1d23;
    border-color: #2563eb;
}

QWidget#subUserCard {
    background-color: #252830;
    border: 1px solid #3d4450;
    border-radius: 12px;
}

QLabel#subUserCardTitle {
    color: #e8eaed;
    font-size: 14px;
    font-weight: 700;
}

QToolButton#subUserRemoveBtn {
    background: transparent;
    color: #9aa0a8;
    border: none;
    font-size: 14px;
    padding: 2px 6px;
}

QToolButton#subUserRemoveBtn:hover {
    color: #ffffff;
    background-color: #c42b1c;
    border-radius: 4px;
}

QLabel#sectionTitle {
    color: #e8eaed;
    font-size: 14px;
    font-weight: 600;
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
"""

LIGHT_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f3f4f6;
    color: #1f2937;
    border: 1px solid #d1d5db;
}

QWidget#customTitleBar {
    background-color: #ffffff;
    border-bottom: 1px solid #d1d5db;
}

QWidget#titleDragArea {
    background-color: transparent;
}

QPushButton#titleBtnMin,
QPushButton#titleBtnMax,
QPushButton#titleBtnClose {
    background-color: transparent;
    color: #6b7280;
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
    background-color: #e5e7eb;
    color: #1f2937;
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
    background-color: #f3f4f6;
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
    background: #d1d5db;
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
    background: #d1d5db;
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
    background: #d1d5db;
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
    background-color: #e5e7eb;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 15px;
    font-weight: 600;
    color: #1f2937;
    padding: 0;
}

QToolButton#addFieldBtn:hover,
QToolButton#removeFieldBtn:hover:enabled {
    background-color: #d1d5db;
    border-color: #9ca3af;
}

QToolButton#removeFieldBtn:disabled {
    color: #9ca3af;
    border-color: #e5e7eb;
    background-color: #f3f4f6;
}

QWidget#entriesContainer {
    background-color: #f3f4f6;
}

QWidget#entryRow {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
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
    color: #1f2937;
    padding: 0;
    margin: 0;
}

QLabel#brandSlogan {
    font-size: 11px;
    font-weight: 400;
    color: #9ca3af;
    padding: 0 0 1px 0;
    margin: 0;
}

QLineEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    min-height: 20px;
}

QLineEdit:focus {
    border-color: #3b82f6;
}

QWidget#copyGroup {
    border: 2px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    min-height: 38px;
    max-height: 38px;
}

QWidget#copyGroup[copied="true"] {
    border-color: #3b82f6;
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
    border-right: 1px solid #d1d5db;
    border-radius: 5px;
    background-color: #e5e7eb;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    margin: 0;
}

QWidget#copyGroup QToolButton#copyBtn:hover {
    background-color: #d1d5db;
}

QWidget#copyGroup[copied="true"] QToolButton#copyBtn {
    border-right: 1px solid #d1d5db;
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
    background-color: #e5e7eb;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #d1d5db;
    border-color: #9ca3af;
}

QPushButton:pressed {
    background-color: #f3f4f6;
}

QPushButton#primaryBtn {
    background-color: #e07020;
    border-color: #c45e15;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryBtn:hover {
    background-color: #f08030;
    border-color: #e07020;
}

QPushButton#primaryBtn:pressed {
    background-color: #c45e15;
    border-color: #a84e10;
}

QPushButton#primaryBtn:disabled {
    background-color: #d4a574;
    border-color: #c4956a;
    color: #f3f4f6;
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
    color: #f3f4f6;
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
    background-color: #eff6ff;
    color: #0284c7;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}

QPushButton#headerSecurityBtn:hover {
    background-color: #0ea5e9;
    border-color: #0284c7;
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
    border: 1px solid #d1d5db;
    border-radius: 8px;
}

QLabel#helpDialogTitle {
    color: #1f2937;
    font-size: 16px;
    font-weight: 600;
    padding: 0;
    margin: 0;
}

QPushButton#addRecordBtn {
    background-color: #e5e7eb;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    min-height: 38px;
    max-height: 38px;
}

QPushButton#addRecordBtn:hover {
    background-color: #d1d5db;
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
    background-color: #e5e7eb;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 4px;
}

QToolButton:hover {
    background-color: #d1d5db;
    border-color: #9ca3af;
}

QToolButton:pressed {
    background-color: #f3f4f6;
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
    border-color: #3b82f6;
}

QStatusBar {
    background-color: #ffffff;
    color: #6b7280;
    border-top: 1px solid #d1d5db;
}

QMessageBox {
    background-color: #ffffff;
}

QFileDialog {
    background-color: #f3f4f6;
}

/* --- QTabWidget (Sekmeler) Aydınlık Tema --- */
QTabWidget::pane {
    border: 1px solid #d1d5db;
    background-color: #ffffff;
    border-radius: 6px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #f3f4f6;
    color: #6b7280;
    padding: 8px 16px;
    border: 1px solid #d1d5db;
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
    background-color: #e5e7eb;
    color: #1f2937;
}

/* --- Karşılama Ekranı Kare Butonları --- */
QPushButton#landingSquareBtn {
    font-size: 18px;
    font-weight: bold;
    border-radius: 20px;
    background-color: #ffffff;
    border: 2px solid #d1d5db;
    color: #1f2937;
}

QPushButton#landingSquareBtn:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
    color: #1d2937;
}

QPushButton#landingSquareBtn:pressed {
    background-color: #dbeafe;
    border-color: #2563eb;
}

QWidget#subUserCard {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 12px;
}

QLabel#subUserCardTitle {
    color: #1f2937;
    font-size: 14px;
    font-weight: 700;
}

QToolButton#subUserRemoveBtn {
    background: transparent;
    color: #6b7280;
    border: none;
    font-size: 14px;
    padding: 2px 6px;
}

QToolButton#subUserRemoveBtn:hover {
    color: #ffffff;
    background-color: #c42b1c;
    border-radius: 4px;
}

QLabel#sectionTitle {
    color: #1f2937;
    font-size: 14px;
    font-weight: 600;
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
    border: 1px solid #d1d5db;
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
"""
