from pathlib import Path

from kobipass.crypto import write_vault_file
from kobipass.vault_model import KobiVault, UserPermissions, VaultEntry

# 1. 5000 adet yapay kayıt oluştur
test_entries = [
    VaultEntry(name=f"Kayıt {i}", info1=f"Bilgi-{i}")
    for i in range(5000)
]

# 2. Vault yapısını kur
vault = KobiVault(
    entries=test_entries,
    user_permissions=UserPermissions(),
)

# 3. Dosyaya şifreli olarak yaz (Kendi şifrenizi girin)
write_vault_file(
    Path("test_5000.enc"),
    vault,
    "admin123",  # Yönetici şifresi
    [(False, "")] * 3,  # Kullanıcı slotları kapalı
)
print("5000 kayıtlı test dosyası oluşturuldu: test_5000.enc")
