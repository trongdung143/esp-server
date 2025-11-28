import re
import os
import itertools
import os

import httpx
import asyncio
import numpy as np
import soundfile as sf

from src.config.setup import STT_URL
from src.log import logger


# async def pcm_to_wav_bytes(
#     client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
# ) -> str:
#     """
#     Chuyển thành file wav và lưu file.
#     """
#     os.makedirs("src/data/audio_message", exist_ok=True)
#     path = f"src/data/audio_message/{client_id}.wav"
#     if not pcm_buffer:
#         logger.info("Empty buffer, skipping.")
#         return ""

#     audio = np.frombuffer(pcm_buffer, dtype=np.int16)

#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(
#         None, lambda: sf.write(path, audio, sample_rate, format="WAV")
#     )
#     return path


async def stt_from_pcm(
    client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
) -> str:
    if not pcm_buffer:
        print("Empty audio buffer")
        return ""

    audio_np = np.frombuffer(pcm_buffer, dtype=np.int16).astype(np.float16) / 32768.0

    async with httpx.AsyncClient() as client:
        r = await client.post(
            STT_URL,
            content=audio_np.tobytes(),
            headers={"Content-Type": "application/octet-stream"},
        )

    message = r.json().get("text", "").strip()

    message = message.split(".")[0].strip()

    error_messages = [
        "Hãy đăng ký kênh để xem những video mới nhất",
        "Hãy subscribe cho kênh Ghiền Mì Gõ Để không bỏ lỡ những video hấp dẫn",
        "Hãy đăng kí cho kênh lalaschool Để không bỏ lỡ những video hấp dẫn",
        "Cảm ơn các bạn đã xem video hấp dẫn",
        "Chào các bạn và hẹn gặp lại trong các video tiếp theo"
        "hãy đăng ký kênh để đăng ký để không bỏ lỡ những video mới nhé",
        "Hãy đăng ký kênh để xem những video tiếp theo",
        "Hẹn gặp lại ở các video tiếp theo",
    ]
    if message in error_messages or not message:
        return "..."

    return message
