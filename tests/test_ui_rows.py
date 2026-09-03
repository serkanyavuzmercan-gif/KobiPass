"""Arayüz satır yönetimi testleri — kademeli (parça parça) yükleme davranışı.

Bu testler performans iyileştirmesinin DAVRANIŞI bozmadığını doğrular:
satırlar doğru içerikle ve doğru kasa indeksiyle yükleniyor mu, düzenlemeler
kayboluyor mu, arama/silme/sıralama doğru kaydı buluyor mu.

Qt 'offscreen' modda çalışır; ekran gerekmez.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from kobipass.session import admin_permissions  # noqa: E402
from kobipass.vault_model import (  # noqa: E402
    KobiVault,
    UserPermissions,
    VaultEntry,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _drain(window, app) -> None:
    """Kademeli yükleme kuyruğu boşalana kadar olay döngüsünü çevirir."""
    guard = 0
    while window._pending_rows:
        app.processEvents()
        guard += 1
        assert guard < 5000, "kademeli yükleme bitmedi"
    app.processEvents()


def _make_window(app, entries: list[VaultEntry]):
    from kobipass.ui.main_window import MainWindow

    vault = KobiVault()
    vault.entries = entries
    window = MainWindow()
    window._load_vault_data(vault)
    _drain(window, app)
    return window, vault


def _entry(name: str, info1: str = "", extras: list[str] | None = None) -> VaultEntry:
    return VaultEntry(name=name, info1=info1, more_infos=list(extras or []))


def test_rows_load_with_correct_content_and_index(qapp) -> None:
    entries = [_entry(f"Kayit {i}", f"parola{i}", [f"ek{i}"]) for i in range(25)]
    window, _vault = _make_window(qapp, entries)

    assert len(window._row_widgets) == 25
    for index, row in enumerate(window._row_widgets):
        assert row.vault_index == index
        loaded = row.to_entry()
        assert loaded.name == f"Kayit {index}"
        assert loaded.info1 == f"parola{index}"
        assert loaded.more_infos == [f"ek{index}"]


def test_page_size_limits_initial_rows_and_scroll_loads_rest(qapp) -> None:
    from kobipass.ui.main_window import _FILTER_PAGE_SIZE

    total = _FILTER_PAGE_SIZE + 12
    window, _vault = _make_window(qapp, [_entry(f"K{i}") for i in range(total)])

    assert len(window._row_widgets) == _FILTER_PAGE_SIZE
    window._load_next_batch()
    _drain(window, qapp)
    assert len(window._row_widgets) == total
    # Kayıtlar tekrarlanmamalı ve sıra korunmalı.
    names = [row.to_entry().name for row in window._row_widgets]
    assert names == [f"K{i}" for i in range(total)]


def test_duplicate_entries_get_distinct_indexes(qapp) -> None:
    """Aynı içerikli iki kayıt AYNI kasa indeksini almamalı.

    Eskiden indeks ``list.index(entry)`` ile bulunuyordu; VaultEntry eşitliği
    içeriğe baktığı için ikinci kopya birincinin indeksini alıyor ve
    düzenleme yanlış satıra yazılıyordu.
    """
    entries = [_entry("Ayni", "ayni-parola") for _ in range(4)]
    window, _vault = _make_window(qapp, entries)

    window._reload_visible_rows()
    _drain(window, qapp)
    indexes = [row.vault_index for row in window._row_widgets]
    assert sorted(indexes) == [0, 1, 2, 3]


def test_edits_survive_merge_into_vault(qapp) -> None:
    entries = [_entry(f"K{i}", f"p{i}") for i in range(10)]
    window, vault = _make_window(qapp, entries)

    row = window._row_widgets[3]
    row.focus_edits()[0].setText("Degisti")
    window._merge_row_edits_into_vault()

    assert vault.entries[3].name == "Degisti"
    assert vault.entries[2].name == "K2"
    assert vault.entries[4].name == "K4"


def test_typing_marks_dirty(qapp) -> None:
    """Yazınca 'kaydedilmemiş' durumu işaretlenmeli (güncelleme ertelense de)."""
    window, _vault = _make_window(qapp, [_entry("K0", "p0")])
    window._clear_dirty()
    assert window._dirty is False

    window._row_widgets[0].focus_edits()[0].setText("yeni")
    assert window._dirty is True


def test_loading_rows_does_not_mark_dirty(qapp) -> None:
    """Kasa açılışı bir kullanıcı düzenlemesi değildir; kirli işaretlenmemeli."""
    entries = [_entry(f"K{i}", f"p{i}", [f"a{i}", f"b{i}"]) for i in range(15)]
    window, _vault = _make_window(qapp, entries)
    assert window._dirty is False


def test_status_record_count_matches_filled_entries(qapp) -> None:
    entries = [_entry(f"K{i}", f"p{i}") for i in range(12)]
    entries.append(_entry("", ""))  # boş kayıt sayılmamalı
    window, _vault = _make_window(qapp, entries)

    window._update_status()
    assert window._filled_entry_count() == 12


def test_status_count_sees_live_row_edits(qapp) -> None:
    """Ekranda boşaltılan kayıt sayımdan düşmeli (modele yazılmamış olsa da)."""
    window, _vault = _make_window(qapp, [_entry("K0", "p0"), _entry("K1", "p1")])
    assert window._filled_entry_count() == 2

    row = window._row_widgets[0]
    row.focus_edits()[0].setText("")
    row.focus_edits()[1].setText("")
    assert window._filled_entry_count() == 1


def test_search_filters_rows_and_keeps_vault_indexes(qapp) -> None:
    entries = [_entry(f"Firma {i}", f"parola{i}") for i in range(30)]
    window, vault = _make_window(qapp, entries)

    window._search_bar.setText("Firma 7")
    window._run_filter()
    window._worker.wait()
    qapp.processEvents()
    _drain(window, qapp)

    names = [row.to_entry().name for row in window._row_widgets]
    assert names == ["Firma 7"]
    row = window._row_widgets[0]
    assert vault.entries[row.vault_index].name == "Firma 7"


def test_search_then_clear_restores_all_rows(qapp) -> None:
    entries = [_entry(f"Firma {i}") for i in range(20)]
    window, _vault = _make_window(qapp, entries)

    window._search_bar.setText("Firma 5")
    window._run_filter()
    window._worker.wait()
    qapp.processEvents()
    _drain(window, qapp)
    assert len(window._row_widgets) == 1

    window._search_bar.setText("")
    window._run_filter()
    window._worker.wait()
    qapp.processEvents()
    _drain(window, qapp)
    assert len(window._row_widgets) == 20


def test_search_during_pending_load_does_not_mix_rows(qapp) -> None:
    """Yükleme sürerken arama yapılırsa eski kuyruk iptal edilmeli."""
    from kobipass.ui.main_window import MainWindow, _FILTER_PAGE_SIZE

    vault = KobiVault()
    vault.entries = [_entry(f"Firma {i}", f"p{i}") for i in range(_FILTER_PAGE_SIZE)]
    window = MainWindow()
    window._load_vault_data(vault)
    # Kuyruk BİTMEDEN arama çalıştır.
    assert window._pending_rows
    window._search_bar.setText("Firma 3")
    window._run_filter()
    window._worker.wait()
    qapp.processEvents()
    _drain(window, qapp)

    names = [row.to_entry().name for row in window._row_widgets]
    assert names, "arama sonucu boş kalmamalı"
    assert all(name.startswith("Firma 3") for name in names)
    assert len(names) == len(set(names)), "satırlar tekrarlanmamalı"


def test_remove_row_deletes_correct_entry(qapp) -> None:
    entries = [_entry(f"K{i}", f"p{i}") for i in range(6)]
    window, vault = _make_window(qapp, entries)

    window._remove_row(window._row_widgets[2])
    qapp.processEvents()

    assert [e.name for e in vault.entries] == ["K0", "K1", "K3", "K4", "K5"]
    assert [row.vault_index for row in window._row_widgets] == [0, 1, 2, 3, 4]


def test_add_field_interactively_still_signals_change(qapp) -> None:
    """Kullanıcı '+' ile alan eklerse 'changed' YAYILMALI (yükleme değil)."""
    window, _vault = _make_window(qapp, [_entry("K0", "p0")])
    window._clear_dirty()

    row = window._row_widgets[0]
    row.apply_permissions(admin_permissions(), view_only=False)
    before = len(row.to_entry().more_infos)
    row._add_extra_field()
    qapp.processEvents()

    assert len(row.to_entry().more_infos) == before + 1
    assert window._dirty is True


def test_readonly_permissions_apply_to_progressively_loaded_rows(qapp) -> None:
    """Kademeli yüklenen satırlar da izinleri almalı — hepsi, sadece ilk grup değil."""
    entries = [_entry(f"K{i}", f"p{i}") for i in range(25)]
    window, vault = _make_window(qapp, entries)

    vault.user_permissions = UserPermissions(
        name="read", info="read", can_add_entry=False, can_delete_entry=False
    )
    from kobipass.session import UserSession

    window._session = UserSession(
        user_slot=1, user_label="Alt Kullanici 1", user_password="x", keys=None
    )
    vault.set_slot_permissions([vault.user_permissions] * 3)
    window._apply_session_ui()
    qapp.processEvents()

    for row in window._row_widgets:
        for edit in row.focus_edits():
            assert edit.isReadOnly() or not edit.isEnabled(), (
                "salt-okunur oturumda alan düzenlenebilir kalmış"
            )


def test_permissions_reapply_after_change(qapp) -> None:
    """İzin imzası önbelleği, izin GERÇEKTEN değişince yenilemeyi engellememeli."""
    window, _vault = _make_window(qapp, [_entry("K0", "p0")])
    row = window._row_widgets[0]

    row.apply_permissions(admin_permissions(), view_only=False)
    assert row.focus_edits()[0].isReadOnly() is False

    row.apply_permissions(
        UserPermissions(name="read", info="read"), view_only=False
    )
    edit = row.focus_edits()[0]
    assert edit.isReadOnly() or not edit.isEnabled()

    row.apply_permissions(admin_permissions(), view_only=False)
    assert row.focus_edits()[0].isReadOnly() is False


def test_reorder_moves_the_right_entry(qapp) -> None:
    entries = [_entry(f"K{i}", f"p{i}") for i in range(5)]
    window, vault = _make_window(qapp, entries)

    # Sürükle-bırak ana yolu satır taşıma mantığını _handle_row_drop içinde
    # tutuyor; burada modeli taşıyıp satırların doğru yeniden yüklendiğini
    # doğruluyoruz (indeksler dahil).
    window._merge_row_edits_into_vault()
    moved = vault.entries.pop(0)
    vault.entries.insert(3, moved)
    window._display_entries = list(vault.entries)
    window._reload_visible_rows()
    _drain(window, qapp)

    assert [row.to_entry().name for row in window._row_widgets] == [
        "K1",
        "K2",
        "K3",
        "K0",
        "K4",
    ]
    assert [row.vault_index for row in window._row_widgets] == [0, 1, 2, 3, 4]


def test_collect_entries_has_no_duplicates_after_load(qapp) -> None:
    """Kaydetme yolu: yüklenen satırlar mükerrer kayıt üretmemeli."""
    entries = [_entry(f"K{i}", f"p{i}") for i in range(18)]
    window, _vault = _make_window(qapp, entries)

    collected = window._collect_entries()
    assert len(collected) == 18
    assert [e.name for e in collected] == [f"K{i}" for i in range(18)]


def test_empty_vault_still_offers_a_blank_row(qapp) -> None:
    """Boş kasa açılışında kullanıcı doğrudan yazmaya başlayabilmeli."""
    window, _vault = _make_window(qapp, [])
    assert len(window._row_widgets) == 1
    assert window._row_widgets[0].to_entry().has_content() is False


def test_search_without_results_shows_message_not_a_blank_row(qapp) -> None:
    """Sonuçsuz aramada boş kayıt satırı DEĞİL, 'bulunamadı' mesajı çıkmalı."""
    window, _vault = _make_window(qapp, [_entry(f"Firma {i}") for i in range(10)])

    window._search_bar.setText("boyle-bir-kayit-yok")
    window._run_filter()
    window._worker.wait()
    qapp.processEvents()
    _drain(window, qapp)

    assert window._row_widgets == []
    assert window._no_results.isVisible() or window._no_results.text()


def test_locked_vault_does_not_recount_records(qapp) -> None:
    """Kilitliyken durum çubuğu kayıt saymaya kalkmamalı."""
    window, _vault = _make_window(qapp, [_entry(f"K{i}", f"p{i}") for i in range(8)])
    window._kilitli_mi = True
    window._update_status()
    assert window._status_left.text()
    window._kilitli_mi = False


def test_pending_load_is_cancelled_on_clear(qapp) -> None:
    """Satırlar temizlenince bekleyen kuyruk da iptal edilmeli."""
    from kobipass.ui.main_window import MainWindow, _FILTER_PAGE_SIZE

    vault = KobiVault()
    vault.entries = [_entry(f"K{i}") for i in range(_FILTER_PAGE_SIZE)]
    window = MainWindow()
    window._load_vault_data(vault)
    assert window._pending_rows

    window._clear_all_rows()
    assert window._pending_rows == []
    qapp.processEvents()
    qapp.processEvents()
    assert window._row_widgets == []
