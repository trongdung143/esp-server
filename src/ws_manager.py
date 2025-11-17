from fastapi import WebSocket
from src.db.operation import ClientRedis


class WebSocketManager:
    def __init__(self):
        self._clients: dict[str, WebSocket] = {}

    def _add_client(self, client_id: str, ws: WebSocket):
        if client_id not in self._clients:
            self._clients[client_id] = ws

    def _get_ws(self, client_id: str):
        if client_id in self._clients:
            return self._clients[client_id]

    def _remove_client(self, client_id: str):
        if client_id in self._clients:
            del self._clients[client_id]

    async def send_text(self, client_id: str, text: str):
        ws = self._get_ws(client_id)
        await ws.send_text(text)

    async def hello_server(self, client_id: str, ws: WebSocket):
        self._add_client(client_id, ws)
        await ws.accept()
        client_id = client_id
        redis = ClientRedis(client_id)
        await redis.set_speaking_speed(int(150))
        await redis.set_volume(15)
        await self.send_text(client_id, "volume:15")

    async def get_data(self, client_id: str):
        ws = self._get_ws(client_id)
        redis = ClientRedis(client_id)
        data = await ws.receive()
        if data["type"] == "websocket.receive":
            return data
        if data["type"] == "websocket.disconnect":
            self._remove_client(client_id)
            await redis.clear_all_data()
            return "disconnect"


ws_client = WebSocketManager()
