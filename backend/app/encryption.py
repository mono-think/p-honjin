import os
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ==========================================
# 暗号化設定 (※本番稼働時は .env などの環境変数に移行します)
# ==========================================
# AES-GCM用の32バイト(256bit)マスターキー。開発用に固定値を使用します。
ENCRYPTION_KEY_BASE64 = "16cIuI1VfXzT-V-MhJ4d5_xO_R1z5Ew1x4z0p2EaL5c=" 
ENCRYPTION_KEY = base64.urlsafe_b64decode(ENCRYPTION_KEY_BASE64)

# ブラインドインデックス(HMAC)用のシークレットキー
BLIND_INDEX_KEY = b"honjin-blind-index-super-secret-key"

def encrypt_pii(plaintext: str | None) -> str | None:
    """PII（個人情報）をAES-GCMで暗号化する"""
    if not plaintext:
        return None
    
    aesgcm = AESGCM(ENCRYPTION_KEY)
    nonce = os.urandom(12)  # AES-GCMの推奨nonce長は12バイト
    
    # 暗号化の実行 (nonce + 暗号文 を結合してBase64文字列として保存)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    encrypted_data = nonce + ciphertext
    
    return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')

def decrypt_pii(encrypted_b64: str | None) -> str | None:
    """暗号化されたPII（Base64文字列）を復号化する"""
    if not encrypted_b64:
        return None
    
    try:
        encrypted_data = base64.urlsafe_b64decode(encrypted_b64)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        aesgcm = AESGCM(ENCRYPTION_KEY)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    except Exception as e:
        # 復号化失敗時（キー違いやデータ破損など）
        print(f"復号化エラー: {e}")
        return None

def generate_blind_index(plaintext: str | None) -> str | None:
    """
    DBでの完全一致検索用のブラインドインデックス（HMAC-SHA256）を生成する。
    """
    if not plaintext:
        return None
    
    # 検索時の揺らぎを吸収するため、前後の空白を削除し小文字に統一（正規化）
    normalized_text = plaintext.strip().lower()
    
    h = hmac.new(BLIND_INDEX_KEY, normalized_text.encode('utf-8'), hashlib.sha256)
    return h.hexdigest()