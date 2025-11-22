import os
import asyncio

from fastapi import WebSocket

from src.db.redis_operation import ClientRedis
from src.log import logger


class WebSocketManager:
    def __init__(self):
        self._clients: dict[str, WebSocket] = {}

    async def _add_client(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self._clients[client_id] = ws

    def _get_ws(self, client_id: str):
        ws = self._clients.get(client_id)
        if ws and ws.client_state.value == 1:
            return ws

        if client_id in self._clients:
            self._remove_client(client_id)
        return None

    def _remove_client(self, client_id: str):
        del self._clients[client_id]

    async def send_text(self, client_id: str, text: str):
        ws = self._get_ws(client_id)
        if ws:
            try:
                await ws.send_text(text)
            except RuntimeError as e:
                logger.exception(e)

    async def hello_server(self, client_id: str, ws: WebSocket):
        try:
            redis = ClientRedis(client_id)
            await self._add_client(client_id, ws)
            await redis.set_speaking_speed(int(120))
            await redis.set_volume(10)
            await self.send_text(client_id, "volume:10")
        except Exception as e:
            logger.exception(e)

    async def get_data(self, client_id: str):
        ws = self._get_ws(client_id)

        redis = ClientRedis(client_id)
        data = None
        if ws:
            try:
                data = await ws.receive()
                return data
            except asyncio.TimeoutError:
                pass
        else:
            await redis.clear_queue("messages")
            paths = [
                f"src/data/music/{client_id}.mp3",
                f"src/data/pdf/{client_id}.pdf",
                f"src/data/audio_message/{client_id}.wav",
            ]

            for path in paths:
                if os.path.exists(path):
                    os.remove(path)
            return "disconnect"


ws_client = WebSocketManager()
