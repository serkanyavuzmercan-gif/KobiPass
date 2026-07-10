"""
Kasa dışa aktarma — JSON / CSV (yalnızca yönetici).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from kobipass.vault_model import KobiVault


def export_vault_json(vault: KobiVault, path: Path) -> None:
    payload = {
        "version": 1,
        "field_labels": {
            key: value
            for key, value in vault.resolved_field_labels().items()
            if value
        },
        "entries": [entry.to_dict() for entry in vault.entries],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_vault_csv(vault: KobiVault, path: Path) -> None:
    labels = vault.resolved_field_labels()
    max_info = 1
    for entry in vault.entries:
        max_info = max(max_info, entry.max_info_index())

    headers = [labels.get("name") or "name"]
    for index in range(1, max_info + 1):
        key = f"info{index}"
        headers.append(labels.get(key) or key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for entry in vault.entries:
            row = [entry.name, entry.info1]
            for index in range(2, max_info + 1):
                row.append(entry.field_value(f"info{index}"))
            writer.writerow(row)


def export_format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    return "json"
