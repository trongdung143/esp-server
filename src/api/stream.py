from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.utils.stream_chat import stream_chat
from src.api.utils.stream_music import stream_music


router = APIRouter()


music_streams = {}


@router.get("/stream_music")
async def stream_music_ep(client_id: str, music_id: str):
    file_path = f"src/data/music/{music_id}.mp3"
    gen = stream_music(file_path)
    music_streams[client_id] = gen
    return StreamingResponse(gen, media_type="audio/mpeg")


@router.get("/stop_stream_music")
async def stop_stream_music_ep(client_id: str):
    gen = music_streams.get(client_id)
    if gen:
        await gen.aclose()
        del music_streams[client_id]
    return {"status": "stopped"}


@router.get("/stream_chat")
async def stream_chat_ep(client_id: str):
    return StreamingResponse(stream_chat(client_id), media_type="audio/mpeg")
