"""
KobiPass Güvenlik Protokolü ve Hakkında (Credits) Penceresi.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from kobipass import __version__
from kobipass.i18n import tr


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("helpDialog")
        self.setWindowTitle(tr("about_title"))
        self.resize(500, 420)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("aboutTabs")

        self.tab_security = QWidget()
        sec_layout = QVBoxLayout(self.tab_security)
        sec_layout.setContentsMargins(0, 10, 0, 0)

        self.sec_browser = QTextBrowser()
        self.sec_browser.setObjectName("helpBrowser")
        self.sec_browser.setOpenExternalLinks(True)
        sec_layout.addWidget(self.sec_browser)

        self.tab_credits = QWidget()
        cred_layout = QVBoxLayout(self.tab_credits)
        cred_layout.setContentsMargins(0, 10, 0, 0)

        self.cred_browser = QTextBrowser()
        self.cred_browser.setObjectName("helpBrowser")
        self.cred_browser.setOpenExternalLinks(True)
        cred_layout.addWidget(self.cred_browser)

        self.tabs.addTab(self.tab_security, "")
        self.tabs.addTab(self.tab_credits, "")

        layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.close_btn = QPushButton(tr("help_close"))
        self.close_btn.setMinimumWidth(100)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(tr("about_title"))
        self.tabs.setTabText(0, tr("about_tab_security"))
        self.tabs.setTabText(1, tr("about_tab_credits"))
        self.sec_browser.setHtml(self._get_security_html())
        self.cred_browser.setHtml(self._get_credits_html())
        self.close_btn.setText(tr("help_close"))

    def _get_security_html(self) -> str:
        return """
        <h3 style="color: #3b82f6; margin-bottom: 5px;">KobiPass Güvenlik Mimarisi</h3>
        <p style="margin-top: 0;">Verileriniz endüstri standartlarında kriptografik algoritmalarla korunmaktadır.</p>
        <ul style="line-height: 1.6;">
            <li><b>Sıfır Bilgi (Zero-Knowledge):</b> Kasa dosyalarınız (.enc) tamamen bu cihazda kilitlenir. İnternete veya hiçbir sunucuya veri gönderilmez.</li>
            <li><b>Askeri Sınıf Şifreleme:</b> Verileriniz, uluslararası güvenlik standardı olan <strong>AES-256-GCM</strong> algoritması ile şifrelenir.</li>
            <li><b>Zırhlı Parola Koruma:</b> Girdiğiniz parolalar <strong>PBKDF2-HMAC-SHA256</strong> (100.000 iterasyon) ile kaba kuvvet saldırılarına (brute-force) karşı kilitlenir.</li>
            <li><b>Zarf Şifreleme (Envelope Encryption):</b> Yönetici ve kullanıcı parolaları ana veri anahtarını (DEK) ayrı ayrı sararak, yetki izolasyonunu maksimum seviyede tutar.</li>
            <li><b>Değişiklik İzi (Audit Log):</b> Kasada yapılan her değişiklik, şifreli ve zaman damgalı olarak kayıt altına alınır.</li>
        </ul>
        """

    def _get_credits_html(self) -> str:
        return f"""
        <h3 style="color: #e07020; margin-bottom: 5px;">KobiPass v{__version__}</h3>
        <p style="margin-top: 0; color: gray;">KOBİ'ler için güvenli, rol tabanlı parola kasası.</p>
        <hr style="border: 1px solid #3d4450;">
        <h4 style="margin-bottom: 2px;">Geliştirici</h4>
        <p style="margin-top: 0;">Tüm Hakları Saklıdır &copy; 2026</p>

        <h4 style="margin-bottom: 2px; margin-top: 15px;">Açık Kaynak Altyapı (Credits)</h4>
        <p style="margin-top: 0;">Bu yazılım, aşağıdaki açık kaynaklı teknolojilerin gücüyle geliştirilmiştir:</p>
        <ul style="line-height: 1.6;">
            <li><b>PyQt6:</b> Masaüstü arayüz motoru (GPLv3).</li>
            <li><b>Python Cryptography:</b> Şifreleme ve PBKDF2 işlemleri.</li>
        </ul>
        <br>
        <p><i>Güvenliğiniz önceliğimizdir.</i></p>
        """
