from src.db.connection import r


class ClientRedis:
    def __init__(self, client_id: str):
        self._client_id = client_id
        self._r = r

    def _queue_key(self, queue_type: str) -> str:
        return f"client:{self._client_id}:queue:{queue_type}"

    def _language_key(self) -> str:
        return f"client:{self._client_id}:language"

    def _volume_key(self) -> str:
        return f"client:{self._client_id}:volume"

    def _speaking_speed_key(self) -> str:
        return f"client:{self._client_id}:speaking_speed"

    def _wake_word_key(self) -> str:
        return f"client:{self._client_id}:wake_word"

    def _is_sleep_key(self) -> str:
        return f"client:{self._client_id}:is_sleep"

    def _pattern_all(self) -> str:
        return f"client:{self._client_id}:*"

    async def push_queue(self, queue_type: str, value: str) -> int:
        return await self._r.rpush(self._queue_key(queue_type), value)

    async def pop_queue(self, queue_type: str) -> str | None:
        return await self._r.lpop(self._queue_key(queue_type))

    async def clear_queue(self, queue_type: str):
        pattern = f"client:{self._client_id}:queue:{queue_type}*"
        keys = await self._r.keys(pattern)
        if keys:
            await self._r.delete(*keys)

    async def is_empty_queue(self, queue_type: str) -> bool:
        length = await self._r.llen(self._queue_key(queue_type))
        return length == 0

    async def set_language(self, language: str):
        await self._r.set(self._language_key(), language)

    async def get_language(self) -> str:
        lang = await self._r.get(self._language_key())
        if lang is None:
            return "vi"
        return lang

    async def set_volume(self, volume: int):
        await self._r.set(self._volume_key(), volume)

    async def get_volume(self) -> int:
        volume = await self._r.get(self._volume_key())
        if volume is None:
            return 0
        return int(volume)

    async def set_speaking_speed(self, speed: int):
        await self._r.set(self._speaking_speed_key(), speed)

    async def get_speaking_speed(self) -> int:
        speed = await self._r.get(self._speaking_speed_key())
        if speed is None:
            return 100
        return int(speed)

    async def clear_all_data(self):
        pattern = self._pattern_all()
        keys = await self._r.keys(pattern)
        if keys:
            await self._r.delete(*keys)

    async def set_wake_word(self):
        await self._r.set(self._wake_word_key(), "hey friday or friday")

    async def get_wake_word(self):
        return await self._r.get(self._wake_word_key())

    async def set_is_sleep(self, is_sleep: bool):
        is_sleep_str = None
        if is_sleep:
            is_sleep_str = "true"
        else:
            is_sleep_str = "false"
        await self._r.set(self._is_sleep_key(), is_sleep_str)

    async def get_is_sleep(self):
        is_sleep = await self._r.get(self._is_sleep_key())
        if is_sleep == "true":
            return True
        return False
