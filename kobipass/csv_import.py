"""
CSV içe aktarma — mevcut (Excel vb.) parolaları KobiPass'e taşımak için.

Yalnızca İÇERİ yöndür: veri kasaya alınır, dışarı verilmez ("export yok"
güvenlik ilkesi korunur). Ayrıştırma Türkçe Excel dostudur: hem ``,`` hem
``;`` ayracı, ``utf-8-sig`` ve ``cp1254`` (Windows Türkçe) kodlaması otomatik
denenir.

Eşleme sabittir: 1. kolon → İsim, kalan kolonlar sırayla → 1. Bilgi, 2. Bilgi…
İlk satır başlık kabul edildiğinde alan etiketlerini de verir.

Bu modül Qt'den bağımsızdır; saf mantık burada, arayüz ``ui/import_dialog``'da.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from kobipass.vault_model import VaultEntry

# Sırayla denenen kodlamalar: BOM'lu UTF-8, Windows Türkçe, son çare Latin-1.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1254", "latin-1")
# Aday ayraçlar — Türkçe Excel çoğu zaman ';' kullanır (virgül ondalık ayracı).
_DELIMITERS = ";,\t|"


@dataclass
class CsvDocument:
    """Ayrıştırılmış ham CSV: boş olmayan tüm satırlar + saptanan biçim."""

    rows: list[list[str]]
    delimiter: str
    encoding: str


@dataclass
class ImportPlan:
    """Bir içe aktarma planı: kolon başlıkları, üretilecek kayıtlar, etiketler."""

    headers: list[str]
    entries: list[VaultEntry] = field(default_factory=list)
    field_labels: dict[str, str] = field(default_factory=dict)


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def _sniff_delimiter(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    sample = "\n".join(lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_DELIMITERS)
        if dialect.delimiter in _DELIMITERS:
            return dialect.delimiter
    except csv.Error:
        pass
    # Yedek: ilk satırda en çok geçen aday ayracı seç; hiçbiri yoksa virgül.
    first = lines[0] if lines else ""
    counts = {d: first.count(d) for d in _DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def parse_csv(data: bytes) -> CsvDocument:
    """Ham baytları çözer, ayracı saptar ve boş olmayan satırları döndürür."""
    text, encoding = _decode(data)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    delimiter = _sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    return CsvDocument(rows=rows, delimiter=delimiter, encoding=encoding)


def rows_to_entries(rows: list[list[str]]) -> list[VaultEntry]:
    """Her satırı bir VaultEntry'ye çevirir: 1. hücre İsim, gerisi bilgi alanı.

    Parola yaşı bilinmediği için ``pw_updated_at`` boş bırakılır (sahte 'taze'
    göstermemek için). Tamamen boş satırlar atlanır; sondaki boş bilgi hücreleri
    kırpılır.
    """
    entries: list[VaultEntry] = []
    for row in rows:
        cells = [(cell.strip() if isinstance(cell, str) else "") for cell in row]
        if not any(cells):
            continue
        name = cells[0] if cells else ""
        info1 = cells[1] if len(cells) > 1 else ""
        more = list(cells[2:])
        while more and not more[-1]:
            more.pop()
        entries.append(VaultEntry(name=name, info1=info1, more_infos=more))
    return entries


def labels_from_headers(headers: list[str]) -> dict[str, str]:
    """Başlık satırından alan etiketleri: 0→name, 1→info1, 2→info2…"""
    labels: dict[str, str] = {}
    for index, header in enumerate(headers):
        text = header.strip()
        if not text:
            continue
        key = "name" if index == 0 else f"info{index}"
        labels[key] = text
    return labels


def build_import(document: CsvDocument, *, has_header: bool = True) -> ImportPlan:
    """Belgeyi, başlık tercihine göre bir içe aktarma planına dönüştürür."""
    if not document.rows:
        return ImportPlan(headers=[])
    if has_header:
        headers = [cell.strip() for cell in document.rows[0]]
        data_rows = document.rows[1:]
        labels = labels_from_headers(headers)
    else:
        width = max((len(row) for row in document.rows), default=0)
        headers = ["" for _ in range(width)]
        data_rows = document.rows
        labels = {}
    return ImportPlan(
        headers=headers,
        entries=rows_to_entries(data_rows),
        field_labels=labels,
    )
