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

QPushButton#helpBtn {
    min-width: 0;
    padding: 8px 12px;
}

QPushButton#langBtn {
    min-width: 0;
    max-width: 52px;
    padding: 8px 8px;
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
"""
