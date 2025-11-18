from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.utils import stream_chat, stream_music


router = APIRouter()


@router.get("/stream_music")
async def stream_music_ep(client_id: str):
    file_path = f"src/data/music/{client_id}.mp3"
    return StreamingResponse(stream_music(file_path), media_type="audio/mpeg")


@router.get("/stream_chat")
async def stream_chat_ep(client_id: str):
    return StreamingResponse(stream_chat(client_id), media_type="audio/mpeg")
