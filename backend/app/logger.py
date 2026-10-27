import json
import logging
import sys
from datetime import datetime, timezone

class SecureJsonFormatter(logging.Formatter):
    """
    ログをJSON形式で出力し、機密情報を自動でマスクするカスタムフォーマッター
    """
    # マスク対象のキーワード（部分一致ではなく完全一致で判定します）
    MASK_KEYS = {"password", "token", "access_token", "authorization", "secret"}

    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "lineNo": record.lineno,
        }

        # 例外（エラー）があればスタックトレースを追加
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # extra_dataという名前で辞書が渡された場合、機密情報をマスクして結合
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_record["data"] = self._mask_dict(record.extra_data)

        return json.dumps(log_record, ensure_ascii=False)

    def _mask_dict(self, data: dict) -> dict:
        masked = {}
        for k, v in data.items():
            if k.lower() in self.MASK_KEYS:
                masked[k] = "*****"
            elif isinstance(v, dict):
                masked[k] = self._mask_dict(v)
            else:
                masked[k] = v
        return masked

def get_logger(name: str = "honjin"):
    logger = logging.getLogger(name)
    
    # ハンドラの重複登録を防止（自動リロード時の二重出力対策）
    if not logger.handlers:
        logger.setLevel(logging.INFO)  # 本番稼働時はINFO、開発時はDEBUG
        
        # ログを標準出力(stdout)へ流す
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SecureJsonFormatter())
        logger.addHandler(handler)
        
        # ルートロガーへの伝播を防止
        logger.propagate = False

    return logger

# アプリケーション全体で使い回すデフォルトロガー
logger = get_logger()