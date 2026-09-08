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
# BOM → kodlama. Sıralı deneme tek başına yetmez: bir UTF-16 dosyasının
# baytları utf-8 olarak çözülemez ama cp1254'te GEÇERLİDİR (\xff=ÿ, \xfe=ş).
# Sonuç sessizce her karakterin arasına NUL serpiştirilmiş çöp metin olur ve
# bozuk parolalar uyarısız kasaya yazılır. Excel'in "Unicode Metin (*.txt)"
# çıktısı tam olarak UTF-16LE'dir ve dosya filtresi *.txt içerir.
_BOMS = (
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)
# Aday ayraçlar — Türkçe Excel çoğu zaman ';' kullanır (virgül ondalık ayracı).
_DELIMITERS = ";,\t|"
# Bir kayıt için en fazla bilgi alanı. Sınırsız bırakıldığında 1000 kolonlu bir
# CSV, satır başına 998 alan üretiyor; EntryRowWidget her alan eklemede tüm alt
# bileşenleri gezdiği için maliyet kuadratik oluyor ve arayüz dakikalarca
# donuyordu (önizleme diyaloğu bu maliyeti hiç göstermiyor).
MAX_IMPORT_FIELDS = 24

# Kullanıcıya gösterilecek uyarı anahtarları (i18n).
WARN_UNBALANCED_QUOTES = "import_csv_warn_quotes"
WARN_TOO_MANY_COLUMNS = "import_csv_warn_columns"
WARN_DECODE_FALLBACK = "import_csv_warn_encoding"


@dataclass
class CsvDocument:
    """Ayrıştırılmış ham CSV: boş olmayan tüm satırlar + saptanan biçim."""

    rows: list[list[str]]
    delimiter: str
    encoding: str
    # Kullanıcıya gösterilecek uyarılar (i18n anahtarları). Sessiz veri kaybını
    # görünür kılar; içe aktarmayı engellemez.
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportPlan:
    """Bir içe aktarma planı: kolon başlıkları, üretilecek kayıtlar, etiketler."""

    headers: list[str]
    entries: list[VaultEntry] = field(default_factory=list)
    field_labels: dict[str, str] = field(default_factory=dict)


def _decode(data: bytes) -> tuple[str, str, bool]:
    """(metin, kodlama, tahmin_mi) döndürür.

    Önce BOM'a bakılır — bu kesin bilgidir. BOM yoksa liste sırayla denenir;
    ``latin-1`` hiçbir zaman hata vermediği için son eleman DAİMA başarılıdır,
    yani "çözülemedi" diye bir durum oluşmaz. Bu yüzden latin-1'e düşüldüğünde
    sonucun bir TAHMİN olduğu ayrıca bildirilir.
    """
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            try:
                return data.decode(encoding), encoding, False
            except UnicodeDecodeError:
                break
    for encoding in _ENCODINGS:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        # NUL karakteri, yanlış kodlamayla çözülmüş UTF-16'nın imzasıdır.
        if "\x00" in text:
            continue
        return text, encoding, encoding == "latin-1"
    return data.decode("latin-1", errors="replace"), "latin-1", True


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
    text, encoding, guessed = _decode(data)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    delimiter = _sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]

    warnings: list[str] = []
    if guessed:
        warnings.append(WARN_DECODE_FALLBACK)

    # Kapanmayan tırnak: csv okuyucu, kaçışsız bir " gördüğünde dosyanın
    # sonuna kadar tüm satırları TEK hücreye yutar ve hata vermez. Kullanıcı
    # "içe aktardıktan sonra CSV'yi silin" notuna uyarsa kayıp kalıcı olur.
    # Mantıksal satır sayısını fiziksel satır sayısıyla karşılaştırarak yakala.
    physical = sum(1 for line in text.split("\n") if line.strip())
    swallowed = any("\n" in cell for row in rows for cell in row)
    if swallowed and physical > len(rows) + 1:
        warnings.append(WARN_UNBALANCED_QUOTES)

    if any(len(row) > MAX_IMPORT_FIELDS + 1 for row in rows):
        warnings.append(WARN_TOO_MANY_COLUMNS)

    return CsvDocument(
        rows=rows, delimiter=delimiter, encoding=encoding, warnings=warnings
    )


def rows_to_entries(rows: list[list[str]]) -> list[VaultEntry]:
    """Her satırı bir VaultEntry'ye çevirir: 1. hücre İsim, gerisi bilgi alanı.

    Parola yaşı bilinmediği için ``pw_updated_at`` boş bırakılır (sahte 'taze'
    göstermemek için). Tamamen boş satırlar atlanır; sondaki boş bilgi hücreleri
    kırpılır.

    YALNIZCA ``name`` kırpılır. Parola (info1) ve diğer bilgi alanları olduğu
    gibi korunur — uygulamanın kendi düzenleme yolu da böyle davranır
    (EntryRowWidget.to_entry). Hepsi kırpılınca baş/son boşluğu olan bir parola
    CSV'den geldiğinde sessizce değişiyor ve doğrudan çalışmayan bir kimlik
    bilgisine dönüşüyordu.

    Alan sayısı ``MAX_IMPORT_FIELDS`` ile sınırlıdır; fazlası atılır (bkz.
    WARN_TOO_MANY_COLUMNS).
    """
    entries: list[VaultEntry] = []
    for row in rows:
        cells = [(cell if isinstance(cell, str) else "") for cell in row]
        if not any(cell.strip() for cell in cells):
            continue
        name = cells[0].strip() if cells else ""
        info1 = cells[1] if len(cells) > 1 else ""
        more = list(cells[2 : 2 + MAX_IMPORT_FIELDS - 1])
        while more and not more[-1].strip():
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
