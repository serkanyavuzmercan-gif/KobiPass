"""
CSV dışa aktarma — kasadaki kayıtları düz metin CSV'ye çevirir.

TASARIM NOTU — bu özellik bir dönem bilinçli olarak KAPALIYDI ("güvenlik gereği
dışa aktarma yoktur"). Yasak geri alındı, çünkü korumadığı bir şeyi engelliyordu:
yönetici zaten her parolayı ekranda görebiliyor, tek tek kopyalayabiliyor. Dışa
aktarmayı kapatmak yeteneği değil yalnızca kolaylığı engelliyordu; buna karşılık
kasadan çıkış yolunun olmaması gerçek bir risk (dosya bozulur, format unutulur,
program bırakılır → veri rehin kalır). Ciddi parola yöneticilerinin tamamında
(Bitwarden, 1Password, KeePass) export bulunmasının sebebi budur: veri
taşınabilirliği bir açık değil, kullanıcı hakkıdır.

Gerçek risk export'un kendisi değil, DİSKTE KALAN ŞİFRESİZ DOSYADIR. Bu yüzden:
- yalnızca yönetici çağırabilir (arayüz katmanı zorlar),
- gizli sekmeler varsayılan olarak DIŞARIDA kalır, açıkça işaretlenmelidir,
- işlem değişiklik geçmişine yazılır,
- arayüz dosyanın şifresiz olduğunu söyler ve kullanım sonrası silinmesini önerir.

Bu modül Qt'den bağımsızdır; saf mantık burada, arayüz ``ui/export_dialog``'da.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from kobipass.vault_model import KobiVault, VaultTab

# Excel (özellikle Türkçe yerelinde) noktalı virgülle açılır; virgül ise
# Bitwarden gibi araçların beklediği standart biçimdir.
DELIMITER_EXCEL = ";"
DELIMITER_STANDARD = ","
# BOM: Excel'in UTF-8'i tanıması için gerekir, yoksa Türkçe karakterler bozulur.
_BOM = "﻿"


@dataclass
class ExportPlan:
    """Dışa aktarılacak içeriğin özeti — onay ekranı bunu gösterir."""

    headers: list[str]
    rows: list[list[str]]
    tab_count: int
    hidden_tab_count: int

    @property
    def record_count(self) -> int:
        return len(self.rows)


def _column_label(vault: KobiVault, index: int) -> str:
    """Kolon başlığı: kasanın özel etiketi varsa o, yoksa varsayılan ad."""
    from kobipass.i18n import tr

    key = "name" if index == 0 else f"info{index}"
    custom = vault.label_for(key)
    if custom:
        return custom
    if index == 0:
        return tr("field_name")
    if index == 1:
        return tr("field_info1")
    return tr("field_info_n", n=index)


def _exported_tabs(vault: KobiVault, *, include_hidden: bool) -> list[VaultTab]:
    if include_hidden:
        return list(vault.tabs)
    return [tab for tab in vault.tabs if not tab.hidden]


def build_export(vault: KobiVault, *, include_hidden: bool = False) -> ExportPlan:
    """Kasayı satırlara çevirir. Boş kayıtlar atlanır.

    İlk kolon SEKME adıdır: tek dosyada birden çok sekme taşındığı için, hangi
    kaydın nereye ait olduğu kaybolmamalı.
    """
    from kobipass.i18n import tr

    tabs = _exported_tabs(vault, include_hidden=include_hidden)
    width = 0
    for tab in tabs:
        for entry in tab.entries:
            if entry.has_content():
                width = max(width, len(entry.info_values()))

    headers = [tr("export_col_tab"), _column_label(vault, 0)]
    headers += [_column_label(vault, i) for i in range(1, width + 1)]

    rows: list[list[str]] = []
    for tab in tabs:
        for entry in tab.entries:
            if not entry.has_content():
                continue
            values = entry.info_values()
            padded = values + [""] * (width - len(values))
            rows.append([tab.name, entry.name, *padded])

    return ExportPlan(
        headers=headers,
        rows=rows,
        tab_count=len(tabs),
        hidden_tab_count=sum(1 for tab in tabs if tab.hidden),
    )


def to_csv_bytes(plan: ExportPlan, *, delimiter: str = DELIMITER_EXCEL) -> bytes:
    """Planı UTF-8 (BOM'lu) CSV baytlarına çevirir.

    ``lineterminator`` açıkça CRLF: Windows'ta Excel ve Not Defteri satırları
    böyle bekler, varsayılan platforma bırakılırsa dosya platforma göre değişir.
    """
    buffer = io.StringIO()
    writer = csv.writer(
        buffer,
        delimiter=delimiter,
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
    )
    writer.writerow(plan.headers)
    writer.writerows(plan.rows)
    return (_BOM + buffer.getvalue()).encode("utf-8")
