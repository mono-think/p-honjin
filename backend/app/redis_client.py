import redis
import os

# Docker環境内ではホスト名 "redis" で繋がります
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# デコードを有効にして文字列として扱えるように設定
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    db=0, 
    decode_responses=True
)