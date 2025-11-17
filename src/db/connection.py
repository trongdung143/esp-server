import redis.asyncio as aioredis
from src.config.setup import REDIS_HOST, REDIS_PASSWORD

# r = aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
r = aioredis.Redis(
    host=REDIS_HOST,
    port=19190,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)
