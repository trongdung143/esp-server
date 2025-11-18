import redis.asyncio as aioredis
from supabase import create_client

from src.config.setup import REDIS_HOST, REDIS_PASSWORD
from src.config.setup import SUPABASE_URL, SUPABASE_KEY

r = aioredis.Redis(
    host=REDIS_HOST,
    port=19190,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
