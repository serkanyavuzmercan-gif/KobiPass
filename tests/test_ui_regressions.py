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


def test_loading_rows_does_not_mark_vault_dirty(window):
    """Kayıtları yüklemek kasayı 'kaydedilmemiş değişiklik' durumuna sokmamalı.

    Regresyon: ek alanı olan her kaydın yüklenmesi satırın changed sinyalini
    yayıyordu (block_signals yalnızca QLineEdit.textChanged'i bloke ediyor).
    reset_dirty=False yollarında (sekme değiştirme) ve sonsuz kaydırmada bu
    temizlenmediği için kasa hiç düzenlenmeden kirli görünüyordu.
    """
    vault = KobiVault()
    vault.tabs = [
        VaultTab(id="t1", name="A", entries=[VaultEntry(name="a", info1="p")]),
        VaultTab(
            id="t2",
            name="B",
            entries=[VaultEntry(name="b", info1="q", more_infos=["x", "y", "z"])],
        ),
    ]
    vault.active_index = 0
    window._load_vault_data(vault)
    window._clear_dirty()
    assert window._dirty is False

    # Sekme değiştir (reset_dirty=False yolu) — hiçbir şey düzenlenmedi.
    vault.active_index = 1
    window._reload_active_tab(reset_dirty=False)
    assert window._dirty is False, "yalnızca yükleme kasayı kirli yaptı"


def test_loaded_rows_show_password_strength(window):
    """Kasa açıldığında güç göstergesi boş kalmamalı."""
    vault = KobiVault()
    vault.entries = [VaultEntry(name="a", info1="q")]  # çok zayıf
    window._load_vault_data(vault)

    meter = window._row_widgets[0]._info1._strength_meter
    assert meter is not None
    assert "transparent" not in meter.styleSheet()


def test_audit_filter_searches_displayed_text(app):
    """Değişiklik geçmişi filtresi EKRANDA GÖRÜNEN metinde aramalı.

    Regresyon: filtre ham saklanan metinde arıyordu — kaydın yazıldığı andaki
    dil ve o zamanki kullanıcı adı. Tablo ise güncel etiketi ve aktif dile
    çevrilmiş özeti gösteriyor; ekranda okunan hiçbir kelime eşleşmiyordu.
    """
    from kobipass.ui.audit_log_dialog import AuditLogDialog
    from kobipass.vault_model import AuditEntry

    vault = KobiVault()
    vault.user_slot_labels = ["Muhasebe", "Alt Kullanıcı 2", "Alt Kullanıcı 3"]
    vault.audit_log = [
        AuditEntry(
            at="2026-01-01T00:00:00Z",
            user_slot=1,
            user_label="ESKI-AD",  # kayıt anındaki ad
            action="vault_save",
            entry_name="",
            field="",
            summary="eski dilde yazılmış özet",
        )
    ]
    dlg = AuditLogDialog(vault)
    try:
        # Kullanıcı ekranda "Muhasebe" görüyor; onu arayabilmeli.
        dlg._apply_filter("muhasebe")
        assert dlg._table.rowCount() == 1
        # Aktif dildeki özet de aranabilmeli.
        dlg._apply_filter("kaydedildi")
        assert dlg._table.rowCount() == 1
    finally:
        dlg.deleteLater()


def test_english_default_slot_label_is_localized():
    """İngilizce kurulmuş varsayılan etiket 'özel ad' sanılmamalı."""
    from kobipass.ui.audit_log_dialog import _is_default_slot_label

    assert _is_default_slot_label("Alt Kullanıcı 2", 2)
    assert _is_default_slot_label("Sub-user 2", 2)
    assert _is_default_slot_label("Kullanıcı 2", 2)
    assert not _is_default_slot_label("Muhasebe", 2)
    # Başka slotun varsayılanı bu slot için özel ad sayılmaz — karışmasın.
    assert not _is_default_slot_label("Sub-user 3", 2)


def test_user_password_missing_message_names_the_card():
    """Eksik ALT KULLANICI parolası yönetici parolasını işaret etmemeli."""
    from kobipass.i18n import tr
    from kobipass.ui.dialogs import _validate_password_pair

    generic = _validate_password_pair("", "", required=True)
    assert generic == tr("pwd_admin_required")

    targeted = _validate_password_pair(
        "", "", required=True, missing_message=tr("pwd_user_required", name="Muhasebe")
    )
    assert "Muhasebe" in targeted
    assert targeted != generic


def test_delete_then_scroll_does_not_duplicate_rows(window):
    """Satır silip aşağı kaydırmak satırları ÇİFTLEMEMELİ.

    Regresyon: _remove_row _display_entries'i güncellemiyordu; _load_next_batch
    bayat listeyi kaynak, satır sayısını da ofset olarak kullandığı için zaten
    görüntülenen kayıtları tekrar satır olarak ekliyor ve vault_index'ler
    çakışıyordu.
    """
    from kobipass.ui.main_window import _FILTER_PAGE_SIZE

    total = _FILTER_PAGE_SIZE + 10
    vault = KobiVault()
    vault.entries = [VaultEntry(name=f"k{i:03d}", info1="p") for i in range(total)]
    window._load_vault_data(vault)
    assert len(window._row_widgets) == _FILTER_PAGE_SIZE

    for _ in range(3):
        window._remove_row(window._row_widgets[0])
    window._load_next_batch()
    window._load_next_batch()

    names = [row.to_entry().name for row in window._row_widgets]
    assert len(names) == len(set(names)), f"çift satır: {names}"
    indexes = [row.vault_index for row in window._row_widgets if row.vault_index is not None]
    assert len(indexes) == len(set(indexes)), "vault_index çakışması"
    assert names == [e.name for e in vault.entries[: len(names)]]


def test_search_result_rows_map_to_correct_records(window):
    """Arama sonucundaki satırlar doğru kayda bağlanmalı (içerik-özdeş kayıtlar).

    Regresyon: _vault_entry_index eşitlikle arıyordu ve VaultEntry eşitliği
    uid'i yok sayıyor; filtrelenmiş iki özdeş satır da BİRİNCİ kaydın indeksini
    alıyor, ikinci satırdaki düzenleme birincinin üzerine yazılıyordu.
    """
    vault = KobiVault()
    vault.entries = [
        VaultEntry(name="ortak", info1="p", uid="u1"),
        VaultEntry(name="başka", info1="q", uid="u2"),
        VaultEntry(name="ortak", info1="p", uid="u3"),
    ]
    window._load_vault_data(vault)

    # Arama sonucunu doğrudan uygula (arka plan iş parçacığını beklemeden).
    matches = [vault.entries[0], vault.entries[2]]
    window._apply_filter_results(matches, window._filter_request_id)
    assert len(window._row_widgets) == 2
    assert [row.vault_index for row in window._row_widgets] == [0, 2]

    window._row_widgets[1]._name.setText("ikinci-değişti")
    window._merge_row_edits_into_vault()
    assert vault.entries[0].name == "ortak"
    assert vault.entries[2].name == "ikinci-değişti"


def test_user_save_path_does_not_duplicate_audit_for_new_row(window, tmp_path):
    """Alt kullanıcı yeni kayıt ekleyip kaydedince audit'e ÇİFT satır yazılmamalı.

    Regresyon: _save_vault önce _sync_vault_entries() ile yeni satırı modele
    ekliyor, hemen ardından _collect_entries()'i TEKRAR çağırıyordu; satır hâlâ
    vault_index=None taşıdığı için aynı kayıt listeye ikinci kez giriyor ve
    diff her alan değişikliğini iki kez logluyordu.
    """
    from kobipass.crypto import read_vault_file, write_vault_file
    from kobipass.session import session_from_unlock
    from kobipass.ui import main_window as mw
    from kobipass.vault_model import UserPermissions

    shown: list = []
    original_info, original_error = mw.show_info, mw.show_error
    mw.show_info = lambda *a, **k: shown.append(("info", a[1:]))
    mw.show_error = lambda *a, **k: shown.append(("error", a[1:]))
    try:
        path = tmp_path / "kasa.enc"
        vault = KobiVault()
        vault.entries = [VaultEntry(name="var olan", info1="p", uid="u1")]
        vault.set_slot_permissions(
            [UserPermissions(name="write", info="write", can_add_entry=True).normalized()]
        )
        write_vault_file(path, vault, "admin-parola", [(True, "kullanici-parola")])

        unlock = read_vault_file(path, "kullanici-parola")
        window._session = session_from_unlock(unlock, "kullanici-parola", unlock.vault)
        window._current_path = path
        window._load_vault_data(unlock.vault)

        window._add_row(None, vault_index=None, refresh_session=False)
        window._row_widgets[-1]._name.setText("yeni kayıt")
        window._row_widgets[-1]._info1.setText("yeni parola")
        window._mark_dirty()
        window._save_vault()

        saved = read_vault_file(path, "admin-parola").vault
        assert [e.name for e in saved.entries] == ["var olan", "yeni kayıt"]
        name_edits = [
            a
            for a in saved.audit_log
            if a.action == "field_edit" and a.field == "name" and a.entry_name == "yeni kayıt"
        ]
        assert len(name_edits) == 1, f"mükerrer audit: {len(name_edits)}"
        assert len([a for a in saved.audit_log if a.action == "vault_save"]) == 1
    finally:
        mw.show_info, mw.show_error = original_info, original_error


def test_masked_field_cannot_be_copied(app):
    """'Maskeli görüntüleyebilir' alanın parolası kopyalanamamalı.

    Regresyon: aynı satırdaki iki düğme birbirini çürütüyordu — göz düğmesi
    kapalı ve echo modu zorla maskede, ama kopyala düğmesi etkin: tek tıkla
    açık metin panoya gidiyordu.
    """
    from kobipass.permissions import can_copy
    from kobipass.ui.entry_row import EntryRowWidget
    from kobipass.vault_model import UserPermissions

    assert can_copy("read")
    assert can_copy("write")
    assert not can_copy("hidden_read")
    assert not can_copy("none")

    row = EntryRowWidget()
    try:
        row.load_entry(VaultEntry(name="A", info1="COK-GIZLI"))
        row.apply_permissions(UserPermissions(name="read", info="hidden_read"))
        assert row._info1._eye_btn is not None
        assert not row._info1._eye_btn.isEnabled()
        assert not row._info1._copy_btn.isEnabled(), "maskeli alan kopyalanabiliyor"
    finally:
        row.deleteLater()


def test_clipboard_is_cleared_on_lock_and_home(window):
    """Kilitleme ve ana ekrana dönüş panodaki parolayı temizlemeli."""
    from PyQt6.QtGui import QGuiApplication

    from kobipass.clipboard import copy_text
    from kobipass.session import AdminSession

    vault = KobiVault()
    vault.entries = [VaultEntry(name="a", info1="p")]
    window._session = AdminSession(admin_password="pw")
    window._load_vault_data(vault)

    copy_text("PANODAKI-PAROLA")
    assert QGuiApplication.clipboard().text() == "PANODAKI-PAROLA"
    window._guvenlik_kilidini_aktif_et()
    assert QGuiApplication.clipboard().text() != "PANODAKI-PAROLA"

    window._kilitli_mi = False
    copy_text("IKINCI-PAROLA")
    window._dirty = False
    window._go_home()
    assert QGuiApplication.clipboard().text() != "IKINCI-PAROLA"


def test_lock_accepts_pending_new_admin_password(window):
    """Yeni yönetici parolası kaydedilmeden kilit gelirse yeni parola geçmeli.

    Regresyon: kilit ekranı dosyadaki ESKİ sarmalayıcıyla doğruluyordu;
    kullanıcıya "uygulandı" denen yeni parola reddediliyor, kilitliyken
    kaydetmek de mümkün olmadığı için oturum ve kaydedilmemiş veri erişilemez
    hale geliyordu.
    """
    from kobipass.crypto import read_vault_file, write_vault_file
    from kobipass.session import session_from_unlock

    import tempfile

    tmp = Path(tempfile.mkdtemp())
    path = tmp / "kasa.enc"
    vault = KobiVault()
    vault.entries = [VaultEntry(name="a", info1="p")]
    write_vault_file(path, vault, "eski-parola", [(True, "kullanici-parola")])
    unlock = read_vault_file(path, "eski-parola")
    window._session = session_from_unlock(unlock, "eski-parola", unlock.vault)
    window._session.keys = unlock.keys
    window._current_path = path
    window._load_vault_data(unlock.vault)

    keys = unlock.keys
    assert window._lock_password_matches_session(keys, "eski-parola")
    assert not window._lock_password_matches_session(keys, "yeni-parola")

    # Parola değiştirildi ama HENÜZ kaydedilmedi.
    window._pending_admin_password = "yeni-parola"
    window._session.admin_password = "yeni-parola"
    assert window._lock_password_matches_session(keys, "yeni-parola")
    assert not window._lock_password_matches_session(keys, "rastgele")


def test_summary_panel_counts_all_records_not_just_loaded(window):
    """Kayıt özeti TÜM kayıtları saymalı, yalnızca ekrana yüklenenleri değil."""
    from kobipass.ui.main_window import _FILTER_PAGE_SIZE

    total = _FILTER_PAGE_SIZE + 17
    vault = KobiVault()
    vault.entries = [VaultEntry(name=f"k{i:03d}", info1="p") for i in range(total)]
    window._load_vault_data(vault)
    assert len(window._row_widgets) == _FILTER_PAGE_SIZE

    window._update_summary_panel()
    assert window._summary_panel._value_rows.text() == str(total)


def test_audit_timestamps_are_shown_in_local_time():
    """Değişiklik geçmişi zaman damgası yerel saate çevrilmeli."""
    from datetime import datetime, timezone

    from kobipass.ui.audit_log_dialog import _audit_time_display

    shown = _audit_time_display("2026-01-15T09:30:00Z")
    expected = (
        datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc)
        .astimezone()
        .strftime("%d.%m.%Y %H:%M")
    )
    assert shown == expected
    assert _audit_time_display("") == ""
    assert _audit_time_display("bozuk") == "bozuk"


def test_prune_empty_cells_asks_and_removes(window, monkeypatch):
    """'Boş Hücreleri Sil' onay sormalı ve yalnızca boş hücreleri kaldırmalı."""
    from kobipass.session import AdminSession
    from kobipass.ui import main_window as mw

    asked: list = []
    infos: list = []
    monkeypatch.setattr(mw, "ask_yes_no", lambda *a, **k: (asked.append(a[2]), True)[1])
    monkeypatch.setattr(mw, "show_info", lambda *a, **k: infos.append(a[2]))

    vault = KobiVault()
    vault.entries = [
        # 2 bos hucre (ortada ve sonda) -> kalanlar sola kayar
        VaultEntry(name="A", info1="p", more_infos=["", "x", ""], uid="u1"),
        # bos hucre yok
        VaultEntry(name="B", info1="q", more_infos=["y"], uid="u2"),
        # ilk hucre bos -> sonraki sola kayar
        VaultEntry(name="C", info1="", more_infos=["z"], uid="u3"),
    ]
    window._session = AdminSession(admin_password="pw")
    window._load_vault_data(vault)

    window._prune_empty_cells()

    assert asked, "onay sorulmadı"
    assert "3" in asked[0], f"hücre sayısı yanlış: {asked[0]}"
    assert vault.entries[0].info_values() == ["p", "x"]
    assert vault.entries[1].info_values() == ["q", "y"]  # dokunulmadı
    assert vault.entries[2].info_values() == ["z"]
    assert window._dirty is True, "değişiklik kirli işaretlenmedi"


def test_prune_empty_cells_can_be_cancelled(window, monkeypatch):
    """Onayda 'Hayır' denince hiçbir şey değişmemeli."""
    from kobipass.session import AdminSession
    from kobipass.ui import main_window as mw

    monkeypatch.setattr(mw, "ask_yes_no", lambda *a, **k: False)
    monkeypatch.setattr(mw, "show_info", lambda *a, **k: None)

    vault = KobiVault()
    vault.entries = [VaultEntry(name="A", info1="p", more_infos=["", "x"], uid="u1")]
    window._session = AdminSession(admin_password="pw")
    window._load_vault_data(vault)
    window._clear_dirty()

    window._prune_empty_cells()
    assert vault.entries[0].info_values() == ["p", "", "x"]
    assert window._dirty is False


def test_prune_empty_cells_keeps_one_cell_per_record(window, monkeypatch):
    """Tüm hücreleri boş olan kayıtta tek boş hücre kalmalı (kayıt silinmez)."""
    from kobipass.session import AdminSession
    from kobipass.ui import main_window as mw

    monkeypatch.setattr(mw, "ask_yes_no", lambda *a, **k: True)
    monkeypatch.setattr(mw, "show_info", lambda *a, **k: None)

    vault = KobiVault()
    vault.entries = [VaultEntry(name="Sadece isim", info1="", more_infos=["", ""], uid="u1")]
    window._session = AdminSession(admin_password="pw")
    window._load_vault_data(vault)

    window._prune_empty_cells()
    assert len(vault.entries) == 1, "kayıt silindi"
    assert vault.entries[0].info_values() == [""]
    assert vault.entries[0].name == "Sadece isim"


def test_prune_empty_cells_hidden_for_read_only_user(window):
    """Alanlarda yazma yetkisi olmayan kullanıcıda düğme görünmemeli."""
    from kobipass.crypto import read_vault_file, write_vault_file
    from kobipass.session import session_from_unlock
    from kobipass.vault_model import UserPermissions

    import tempfile

    tmp = Path(tempfile.mkdtemp())
    path = tmp / "kasa.enc"
    vault = KobiVault()
    vault.entries = [VaultEntry(name="A", info1="p", uid="u1")]
    vault.set_slot_permissions([UserPermissions(name="read", info="read").normalized()])
    write_vault_file(path, vault, "admin-parola", [(True, "kullanici-parola")])

    unlock = read_vault_file(path, "kullanici-parola")
    window._session = session_from_unlock(unlock, "kullanici-parola", unlock.vault)
    window._current_path = path
    window._load_vault_data(unlock.vault)
    window._apply_session_ui()

    assert window._btn_prune_empty.isVisible() is False


# ── Satır içi yatay gezinme ────────────────────────────────────────────────
def _row_with_fields(app, count, width=1860, writable=True):
    """Verilen sayıda bilgi hücresi taşıyan, gerçek genişlikte bir satır kurar."""
    from PyQt6.QtWidgets import QVBoxLayout, QWidget

    from kobipass.ui.entry_row import EntryRowWidget
    from kobipass.ui.theme import theme_manager
    from kobipass.vault_model import UserPermissions

    # Stil sayfası ~4200 satır; her satır kurulumunda tüm uygulamaya yeniden
    # uygulamak test paketini dakikalarca uzatıyordu. Bir kez yeter.
    if not app.styleSheet():
        app.setStyleSheet(theme_manager.stylesheet())
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    row = EntryRowWidget()
    layout.addWidget(row)
    host.resize(width, 200)
    host.show()
    if writable:
        row.apply_permissions(UserPermissions(name="write", info="write"))
    row.load_entry(
        VaultEntry(name="Kayıt", info1="p", more_infos=[f"v{i}" for i in range(count - 1)])
    )
    for _ in range(14):
        app.processEvents()
    return host, row


def test_six_fields_fit_without_scrolling(app):
    """Kullanıcının bildirdiği vaka: 6 alanlı satır normal pencerede taşmamalı.

    Regresyon: hücre genişliği HER ZAMAN viewport/3 idi, yani 4. alandan
    itibaren satır kaçınılmaz olarak taşıyordu. INFO_VISIBLE_COLUMNS artık
    sabit bölen değil ASGARİ kolon sayısı: 4+ alanlı satırlar daralarak sığmaya
    çalışıyor, 1-3 alanlı satırların görünümü değişmiyor.
    """
    for count in (4, 5, 6):
        host, row = _row_with_fields(app, count, width=1860)
        try:
            bar = row._scroll.horizontalScrollBar()
            assert bar.maximum() == 0, f"{count} alan hâlâ taşıyor (max={bar.maximum()})"
        finally:
            host.close()
            host.deleteLater()
            app.processEvents()


def test_small_rows_keep_their_column_width(app):
    """1-3 alanlı satırların hücre genişliği DEĞİŞMEMELİ (görünüm korunur)."""
    from kobipass.ui.entry_row import INFO_VISIBLE_COLUMNS, info_column_width

    for viewport in (600, 900, 1200, 1600, 2400):
        base = info_column_width(viewport, INFO_VISIBLE_COLUMNS)
        for count in (1, 2, 3):
            assert info_column_width(viewport, count) == base, (
                f"viewport={viewport} alan={count}: {info_column_width(viewport, count)} != {base}"
            )


def test_overflowing_row_gets_reachable_edge_arrows(app):
    """Gerçekten taşan satırda kenar okları çıkmalı ve İŞE YARAMALI.

    Regresyon: taşan hücreye ulaşmanın tek yolu 4px'lik, pratikte görünmez ve
    yakalanamaz bir çubuk ile keşfedilemez Shift+tekerlekti.
    """
    host, row = _row_with_fields(app, 12, width=1860)
    try:
        bar = row._scroll.horizontalScrollBar()
        assert bar.maximum() > 0, "12 alan taşmadı; senaryo geçersiz"
        assert row._next_edge_btn is not None, "kenar oku yaratılmadı"
        assert row._next_edge_btn.isVisibleTo(row._scroll)
        assert not row._prev_edge_btn.isVisibleTo(row._scroll), "başta geri ok görünmemeli"

        row._next_edge_btn.click()
        for _ in range(4):
            app.processEvents()
        assert bar.value() > 0, "ileri ok kaydırmadı"
        assert row._prev_edge_btn.isVisibleTo(row._scroll), "kaydırınca geri ok çıkmalı"

        row._prev_edge_btn.click()
        for _ in range(4):
            app.processEvents()
        assert bar.value() == 0, "geri ok başa döndürmedi"
    finally:
        host.close()
        host.deleteLater()
        app.processEvents()


def test_fitting_row_pays_nothing_for_edge_arrows(app):
    """Taşmayan satır kenar oku YARATMAMALI (widget bütçesi).

    1.3.0'daki "her satırda duran garip çubuk" şikâyetinin tekrarlamaması da
    buna bağlı: sığan satırda hiçbir gezinme süsü çıkmaz.
    """
    for count in (1, 3, 6):
        host, row = _row_with_fields(app, count, width=1860)
        try:
            assert row._scroll.horizontalScrollBar().maximum() == 0
            assert row._next_edge_btn is None, f"{count} alanda gereksiz ok yaratıldı"
            assert row._scroll.edge_gutter() == 0, "gereksiz kenar koridoru açıldı"
        finally:
            host.close()
            host.deleteLater()
            app.processEvents()


def test_tab_reveals_field_but_window_return_does_not_scroll(app):
    """Tab ile gidilen hücre görünür olmalı; pencereye dönüş konumu KORUMALI.

    Regresyon 1: Tab ile son alana odaklanmak onu görünür kılmıyordu — klavye
    kullanıcısı görmediği bir alana yazıyordu.
    Regresyon 2 (düzeltmenin kendisinin doğurabileceği): her FocusIn'de
    kaydırmak, kullanıcı hücreyi kopyalayıp tarayıcıya geçip döndüğünde satırı
    başa sarıyordu — bir parola yöneticisinin en sık akışı budur.
    """
    from PyQt6.QtCore import Qt

    host, row = _row_with_fields(app, 12, width=1860)
    try:
        bar = row._scroll.horizontalScrollBar()
        bar.setValue(0)
        for _ in range(3):
            app.processEvents()

        last = row._extra_fields[-1]
        last.focus_edit().setFocus(Qt.FocusReason.TabFocusReason)
        for _ in range(8):
            app.processEvents()
        assert bar.value() > 0, "Tab ile odaklanan alan görünür kılınmadı"
        viewport = row._scroll.viewport().width()
        assert last.x() >= bar.value() - 2
        assert last.x() + last.width() <= bar.value() + viewport + 2

        kept = bar.value()
        last.focus_edit().setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        for _ in range(6):
            app.processEvents()
        assert bar.value() == kept, "pencereye dönüş satırı başa sardı"

        last.focus_edit().setFocus(Qt.FocusReason.MouseFocusReason)
        for _ in range(6):
            app.processEvents()
        assert bar.value() == kept, "fare tıklaması hücreyi imlecin altından kaydırdı"
    finally:
        host.close()
        host.deleteLater()
        app.processEvents()


def test_row_height_does_not_grow_with_field_count(app):
    """Satır yüksekliği alan sayısından ve kaydırma çubuğundan bağımsız olmalı.

    138 kayıtlı bir listede satır başına birkaç piksel büyüme toplamda yüzlerce
    piksel eder. Çubuğun eski :hover kuralı 4px'ten 9px'e büyüyüp viewport'u
    kısaltıyor ve hücreyi kırpıyordu.
    """
    heights = set()
    for count in (1, 3, 6, 12):
        host, row = _row_with_fields(app, count, width=1860)
        try:
            heights.add(row.sizeHint().height())
            bar_h = row._scroll.horizontalScrollBar().height()
            viewport_h = row._scroll.viewport().height()
            assert viewport_h >= 42, f"hücre kırpıldı (viewport={viewport_h})"
            assert bar_h <= 5, f"çubuk satırı büyütüyor ({bar_h}px)"
        finally:
            host.close()
            host.deleteLater()
            app.processEvents()
    assert len(heights) == 1, f"satır yüksekliği alan sayısıyla değişiyor: {heights}"


def test_scroll_rail_only_inks_on_the_hovered_row(app):
    """Ray durgunken sönük, imleç o satırdayken belirgin olmalı.

    1.3.0'da her satırda duran çubuk "garip" bulunmuştu; ayrım bu.
    """
    host, row = _row_with_fields(app, 12, width=1860)
    try:
        bar = row._scroll.horizontalScrollBar()

        def handle_colors():
            from collections import Counter

            from PyQt6.QtGui import QPixmap

            pixmap = QPixmap(bar.size())
            bar.render(pixmap)
            image = pixmap.toImage()
            counter = Counter(
                image.pixelColor(x, y).name()
                for x in range(0, image.width(), 7)
                for y in range(image.height())
            )
            return [name for name, _ in counter.most_common(3)]

        row.setProperty("hovered", False)
        row._sync_scroll_handle()
        for _ in range(3):
            app.processEvents()
        idle = handle_colors()

        row.setProperty("hovered", True)
        row._sync_scroll_handle()
        for _ in range(3):
            app.processEvents()
        hovered = handle_colors()

        assert idle != hovered, f"ray hover'da değişmiyor: {idle}"
    finally:
        host.close()
        host.deleteLater()
        app.processEvents()
