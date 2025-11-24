import re
import os
import itertools
import os

import httpx
import asyncio
import numpy as np
import soundfile as sf

from src.config.setup import STT_01_URL, STT_02_URL
from src.log import logger

STT_SERVERS = [
    STT_01_URL,
    STT_02_URL,
]

STT_ITER = itertools.cycle(STT_SERVERS)
STT_LOCK = asyncio.Lock()


def clean_txt(txt: str) -> str:
    txt = (
        txt.replace("\\n", " ").replace("\n", " ").replace("\t", " ").replace("\r", " ")
    )
    txt = re.sub(r"[^A-Za-zÀ-ỹ0-9\s%]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


async def pcm_to_wav_bytes(
    client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
) -> str:
    """
    Chuyển thành file wav và lưu file.
    """
    os.makedirs("src/data/audio_message", exist_ok=True)
    path = f"src/data/audio_message/{client_id}.wav"
    if not pcm_buffer:
        logger.info("Empty buffer, skipping.")
        return ""

    audio = np.frombuffer(pcm_buffer, dtype=np.int16)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, lambda: sf.write(path, audio, sample_rate, format="WAV")
    )
    return path


async def stt_from_pcm(
    client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
) -> str:
    if not pcm_buffer:
        print("Empty audio buffer")
        return ""

    async with STT_LOCK:
        STT_URL = next(STT_ITER)

    path = await pcm_to_wav_bytes(client_id, pcm_buffer)
    async with httpx.AsyncClient() as client:
        with open(path, "rb") as f:
            files = {"file": (f.name, f, "audio/wav")}
            r = await client.post(STT_URL, files=files)

    message = r.json()["text"]
    message = message.strip()
    error_messages = [
        "Hãy đăng ký kênh để xem những video mới nhất",
        "Hãy subscribe cho kênh Ghiền Mì Gõ Để không bỏ lỡ những video hấp dẫn",
        "Hãy đăng kí cho kênh lalaschool Để không bỏ lỡ những video hấp dẫn",
    ]
    if message in error_messages:
        return "..."
    if not message:
        return "..."
    if os.path.exists(path):
        os.remove(path)
    return message
