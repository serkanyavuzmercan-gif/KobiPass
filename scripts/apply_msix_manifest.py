#!/usr/bin/env python3
"""
MSIX paketi için AppxManifest.xml üretir — kimlik değerlerini
msix/identity.json'dan alır ve şablondaki yer tutucuları doldurur.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="MSIX için AppxManifest.xml üretir")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--version", default="1.1.1.0")
    args = parser.parse_args()

    identity = json.loads(
        (args.root / "msix" / "identity.json").read_text(encoding="utf-8")
    )
    template = (args.root / "msix" / "AppxManifest.xml").read_text(encoding="utf-8")

    manifest = (
        template.replace("__PACKAGE_NAME__", identity["PackageName"])
        .replace("__PUBLISHER__", identity["Publisher"])
        .replace("__VERSION__", args.version)
        .replace("__PUBLISHER_DISPLAY_NAME__", identity["PublisherDisplayName"])
        .replace("__DISPLAY_NAME__", identity["DisplayName"])
    )

    output = args.layout / "AppxManifest.xml"
    output.write_text(manifest, encoding="utf-8")
    print(f"Yazildi: {output}")


if __name__ == "__main__":
    main()
