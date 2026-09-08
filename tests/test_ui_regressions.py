"""Arayüz regresyon testleri — denetimde bulunan veri kaybı yollarını kapatır.

Gerçek ``MainWindow`` örneği üzerinde çalışırlar (offscreen). Amaç görsel
doğrulama değil; satır ↔ model eşleşmesinin ve kaydetme kilidinin doğru
davrandığını kanıtlamaktır.
"""

from __future__ import annotations

import os
from pathlib import Path

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


def test_edits_in_inactive_tab_are_audited(window):
    """Başka sekmede yapılan düzenleme de değişiklik geçmişine düşmeli.

    Regresyon: _snapshot_entries yalnızca AKTİF sekmeyi tutuyor ve her sekme
    geçişinde yenileniyordu; A sekmesinde düzenleme yapıp B'ye geçen kullanıcı
    kaydettiğinde A'daki değişiklikler geçmişte HİÇ görünmüyordu.
    """
    from kobipass.session import AdminSession, admin_permissions

    vault = KobiVault()
    vault.tabs = [
        VaultTab(id="t1", name="A", entries=[VaultEntry(name="kayıt", info1="p", uid="u1")]),
        VaultTab(id="t2", name="B", entries=[VaultEntry(name="öteki", info1="q", uid="u2")]),
    ]
    vault.active_index = 0
    window._session = AdminSession(admin_password="pw")
    window._load_vault_data(vault)

    # A sekmesindeki kaydı değiştir, sonra B sekmesine geç.
    vault.tabs[0].entries[0].name = "kayıt-değişti"
    vault.active_index = 1
    window._reload_active_tab(reset_dirty=False)

    logs = window._collect_audit_logs(admin_permissions())
    edits = [item for item in logs if item.action == "field_edit"]
    assert edits, "başka sekmedeki düzenleme denetime düşmedi"
    assert all(item.tab_id == "t1" for item in edits)
    # 'Kasa kaydedildi' satırı sekme sayısından bağımsız olarak tek olmalı.
    assert len([item for item in logs if item.action == "vault_save"]) == 1


def test_go_home_releases_session_and_stops_idle_timer(window):
    """Karşılama ekranına dönmek kasayı bellekten bırakmalı.

    Regresyon: _go_home yalnızca görünümü değiştiriyordu. (1) 'Değişiklikleri
    at' dendikten sonra Ctrl+S hâlâ etkin olduğu için ATILAN veri eski dosyaya
    yazılabiliyordu; (2) oturum açık kaldığından boşta kalma sayaçı çalışmaya
    devam ediyor ve karşılama ekranının üzerine parola örtüsü açılıyordu.
    """
    from kobipass.session import AdminSession

    vault = KobiVault()
    vault.entries = [VaultEntry(name="k", info1="p")]
    window._session = AdminSession(admin_password="pw")
    window._current_path = Path("/tmp/yok.enc")
    window._load_vault_data(vault)
    window._mark_dirty()
    window._dirty = False  # onay diyaloğu açılmasın

    window._go_home()

    assert window._session is None
    assert window._vault is None
    assert window._current_path is None
    assert not window._idle_timer.isActive()
    assert window._row_widgets == []


def test_pagination_offset_ignores_unsaved_new_rows(window):
    """Yeni satır eklemek sayfalamada bir kaydın atlanmasına yol açmamalı.

    Regresyon: ofset len(_row_widgets) ile hesaplanıyordu; modelde karşılığı
    olmayan (vault_index=None) her yeni satır kaynaktan bir kaydın atlanmasına
    ve o kaydın sekme yeniden yüklenene kadar hiç görünmemesine yol açıyordu.
    """
    from kobipass.ui.main_window import _FILTER_PAGE_SIZE

    total = _FILTER_PAGE_SIZE + 5
    vault = KobiVault()
    vault.entries = [VaultEntry(name=f"k{i:03d}", info1="p") for i in range(total)]
    window._load_vault_data(vault)
    assert len(window._row_widgets) == _FILTER_PAGE_SIZE

    # Kullanıcı yeni bir (boş, modelde karşılığı olmayan) satır ekler.
    window._add_row(None, vault_index=None, refresh_session=False)
    window._load_next_batch()

    shown = [
        row.to_entry().name
        for row in window._row_widgets
        if row.vault_index is not None
    ]
    assert shown == [e.name for e in vault.entries[: len(shown)]]
    assert len(shown) == total


def test_password_age_survives_rename(window):
    """Yalnızca kayıt adını düzeltmek parola yaşını sıfırlamamalı."""
    vault = KobiVault()
    vault.entries = [
        VaultEntry(name="Eski Ad", info1="p", pw_updated_at="2020-01-01T00:00:00Z", uid="u1")
    ]
    window._load_vault_data(vault)

    renamed = [
        VaultEntry(name="Yeni Ad", info1="p", pw_updated_at="2020-01-01T00:00:00Z", uid="u1")
    ]
    window._stamp_password_ages(renamed)
    assert renamed[0].pw_updated_at == "2020-01-01T00:00:00Z"

    # Parola gerçekten değişince damga tazelenmeli.
    changed = [
        VaultEntry(name="Eski Ad", info1="q", pw_updated_at="2020-01-01T00:00:00Z", uid="u1")
    ]
    window._stamp_password_ages(changed)
    assert changed[0].pw_updated_at != "2020-01-01T00:00:00Z"


def test_failed_save_rolls_back_audit_records(window):
    """Başarısız kayıt, modele eklenen audit satırlarını geri almalı."""
    from kobipass.vault_model import AuditEntry

    vault = KobiVault()
    vault.audit_log = [
        AuditEntry(
            at="2026-01-01T00:00:00Z",
            user_slot=0,
            user_label="Y",
            action="vault_save",
            entry_name="",
            field="",
            summary="s",
        )
    ]
    window._vault = vault
    mark = len(vault.audit_log)
    vault.audit_log.append(
        AuditEntry(
            at="2026-01-02T00:00:00Z",
            user_slot=0,
            user_label="Y",
            action="field_edit",
            entry_name="x",
            field="name",
            summary="s",
        )
    )
    window._rollback_failed_save(mark, None)
    assert len(vault.audit_log) == 1


def test_tab_delete_sees_unsaved_row(window, monkeypatch):
    """Ekranda yazılmış ama kaydedilmemiş kayıt olan sekme silinememeli.

    Regresyon: 'içi boş olmalı' kontrolü yalnızca modeldeki tab.entries'e
    bakıyordu. Yeni/boş bir sekmede _refresh_empty_state'in kurduğu satıra
    yazılan kayıt modelde görünmediği için sekme, içindeki veriyle birlikte
    SESSİZCE siliniyordu.
    """
    from kobipass.ui import main_window as mw

    shown: list[tuple] = []
    monkeypatch.setattr(mw, "show_info", lambda *a, **k: shown.append(a))

    vault = KobiVault()
    vault.tabs = [
        VaultTab(id="t1", name="A", entries=[]),
        VaultTab(id="t2", name="B", entries=[VaultEntry(name="dolu", info1="p")]),
    ]
    vault.active_index = 0
    window._vault = vault
    window._active_tab_id = "t1"
    window._add_row(None, vault_index=None, refresh_session=False)
    window._row_widgets[-1]._name.setText("yazılmış ama kaydedilmemiş")

    window._on_delete_tab("t1")

    assert [t.id for t in vault.tabs] == ["t1", "t2"], "dolu sekme silindi"
    assert shown, "kullanıcı uyarılmadı"


def test_single_instance_ignores_foreign_squatter(app):
    """Adı kapan yabancı bir süreç KobiPass'i başlamaktan alıkoymamalı.

    Regresyon: sabit ve kimliksiz uç noktaya bağlanabilmek "zaten çalışıyor"
    kanıtı sayılıyordu; adı önceden oluşturan yetkisiz bir süreç uygulamayı
    oturum boyunca engelleyebiliyordu. Ayrıca dinleme başarısızlığı yakalanmamış
    RuntimeError fırlatıyor, --windowed derlemede uygulama hiçbir şey
    göstermeden ölüyordu.
    """
    from PyQt6.QtNetwork import QLocalServer
    from PyQt6.QtWidgets import QMainWindow

    from kobipass.single_instance import (
        _SERVER_NAME,
        SingleInstanceGuard,
        activate_existing_instance,
    )

    QLocalServer.removeServer(_SERVER_NAME)
    squatter = QLocalServer()
    assert squatter.listen(_SERVER_NAME)
    try:
        # Yabancı taraf el sıkışmaya yanıt vermez → "çalışıyor" sayılmaz.
        assert activate_existing_instance(200) is False
        # Guard istisna FIRLATMAMALI; koruma kurulamasa da uygulama açılır.
        win = QMainWindow()
        guard = SingleInstanceGuard(win, None)
        assert isinstance(guard.active, bool)
        win.close()
    finally:
        squatter.close()
        QLocalServer.removeServer(_SERVER_NAME)
