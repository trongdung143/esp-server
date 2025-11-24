import os
import asyncio

from src.log import logger


async def stream_music(file_path: str, chunk_size: int = 2024):
    """
    Stream file mp3 theo chunk bất đồng bộ và xóa file sau khi stream xong.
    """
    try:
        with open(file_path, "rb") as f:
            while chunk := await asyncio.to_thread(f.read, chunk_size):
                yield chunk
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.info("Finished streaming music")
