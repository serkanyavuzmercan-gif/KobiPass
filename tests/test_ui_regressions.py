"""Arayüz regresyon testleri — denetimde bulunan veri kaybı yollarını kapatır.

Gerçek ``MainWindow`` örneği üzerinde çalışırlar (offscreen). Amaç görsel
doğrulama değil; satır ↔ model eşleşmesinin ve kaydetme kilidinin doğru
davrandığını kanıtlamaktır.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from kobipass.ui.main_window import MainWindow  # noqa: E402
from kobipass.vault_model import KobiVault, VaultEntry, VaultTab  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def window(app):
    win = MainWindow()
    yield win
    # closeEvent kaydedilmemiş değişiklikte MODAL onay açar; offscreen testte
    # bu sonsuza kadar bloklar. Kapatmadan önce kirli bayrağını temizliyoruz.
    win._dirty = False
    win._kilitli_mi = False
    win.close()
    win.deleteLater()
    app.processEvents()


def test_duplicate_entries_map_to_distinct_rows(window):
    """Aynı içerikli iki kayıt AYRI indekslere bağlanmalı.

    VaultEntry.uid ``compare=False`` olduğundan iki kopya birbirine eşittir;
    eşitlik bazlı arama ikisini de 0. indekse bağlıyor, ikinci satırdaki
    düzenleme birinci kaydın üzerine yazıyordu.
    """
    vault = KobiVault()
    vault.entries = [
        VaultEntry(name="aynı", info1="p"),
        VaultEntry(name="aynı", info1="p"),
        VaultEntry(name="farklı", info1="q"),
    ]
    window._vault = vault

    indexes = [window._vault_entry_index(e, 0) for e in vault.entries]
    assert indexes == [0, 1, 2]


def test_duplicate_row_edit_does_not_overwrite_the_other(window):
    """İkinci kopyayı düzenlemek birincisini bozmamalı (uçtan uca).

    Satırlar ``_reload_visible_rows`` üzerinden kurulur; indeksleri
    ``_vault_entry_index`` belirler. Eşitlik bazlı aramada iki satır da 0.
    indekse bağlanıyor, ikinci satırdaki düzenleme birinci kaydı eziyordu.
    """
    vault = KobiVault()
    vault.entries = [
        VaultEntry(name="aynı", info1="p"),
        VaultEntry(name="aynı", info1="p"),
    ]
    window._load_vault_data(vault)
    window._reload_visible_rows()
    assert len(window._row_widgets) == 2
    assert [row.vault_index for row in window._row_widgets] == [0, 1]

    window._row_widgets[1]._name.setText("değişti")
    window._merge_row_edits_into_vault()

    assert vault.entries[0].name == "aynı"
    assert vault.entries[1].name == "değişti"


def test_removed_row_leaves_display_list(window):
    """Silinen kayıt görüntü listesinden de düşmeli.

    Aksi hâlde 'daha fazla yükle' silinen kaydı geri getiriyor ve modelde
    bulunmadığı için YANLIŞ bir indekse bağlanıp başka kaydın üzerine yazıyordu.
    """
    vault = KobiVault()
    vault.entries = [VaultEntry(name=f"k{i}", info1="p") for i in range(3)]
    window._load_vault_data(vault)

    doomed_uid = vault.entries[1].uid
    window._remove_row(window._row_widgets[1])

    assert len(vault.entries) == 2
    assert window._display_entries is not None
    assert all(e.uid != doomed_uid for e in window._display_entries)
    assert len(window._display_entries) == 2


def test_empty_active_tab_does_not_block_saving(window):
    """Boş sekme açıkken diğer sekmelerdeki veri kaydedilebilmeli."""
    vault = KobiVault()
    vault.tabs = [
        VaultTab(id="t1", name="Dolu", entries=[VaultEntry(name="k", info1="p")]),
        VaultTab(id="t2", name="Boş", entries=[]),
    ]
    vault.active_index = 1
    window._vault = vault

    assert window._collect_entries() == []
    assert window._any_tab_has_entries() is True


def test_empty_vault_still_blocks_saving(window):
    """Kasanın tamamı boşsa kilit korunmalı — kilit tamamen kalkmadı."""
    vault = KobiVault()
    vault.tabs = [
        VaultTab(id="t1", name="Boş 1", entries=[]),
        VaultTab(id="t2", name="Boş 2", entries=[VaultEntry(name="", info1="")]),
    ]
    vault.active_index = 0
    window._vault = vault

    assert window._any_tab_has_entries() is False
