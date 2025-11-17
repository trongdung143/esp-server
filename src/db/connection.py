import redis.asyncio as aioredis
from src.config.setup import REDIS_HOST, REDIS_PASSWORD
from supabase import create_async_client
from src.config.setup import SUPABASE_URL, SUPABASE_KEY
import asyncio

# r = aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
r = aioredis.Redis(
    host=REDIS_HOST,
    port=19190,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)


async def get_supabase():
    supabase = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase
