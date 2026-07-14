"""
Parola güç göstergesi — bir QLineEdit'e renkli etiket bağlar.
Ana parola alanlarında (kurulum + yönetici değişimi) kullanılır.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QLineEdit

from kobipass.i18n import tr
from kobipass.password_tools import MEDIUM, STRONG, WEAK, strength_bucket, strength_color

_LABEL_KEY = {WEAK: "strength_weak", MEDIUM: "strength_medium", STRONG: "strength_strong"}


def attach_strength_label(edit: QLineEdit) -> QLabel:
    """QLineEdit'e bağlı, yazdıkça güncellenen renkli güç etiketi döndürür."""
    label = QLabel("")
    label.setObjectName("strengthLabel")

    def update(text: str) -> None:
        bucket = strength_bucket(text)
        if not bucket:
            label.setText("")
            label.setStyleSheet("")
            return
        label.setText(tr(_LABEL_KEY[bucket]))
        label.setStyleSheet(
            f"color: {strength_color(text)}; font-size: 11px; font-weight: 600;"
        )

    edit.textChanged.connect(update)
    update(edit.text())
    return label
