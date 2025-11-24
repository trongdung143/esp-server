import re
import os
import itertools
import os
import random

import httpx
import asyncio
from langchain_core.messages import AIMessageChunk, AIMessage
import numpy as np
import edge_tts
import soundfile as sf

from src.db.redis_operation import ClientRedis
from src.ws_manager import ws_client
from src.config.setup import STT_01_URL, STT_02_URL

STT_SERVERS = [
    STT_01_URL,
    STT_02_URL,
]

STT_ITER = itertools.cycle(STT_SERVERS)
STT_LOCK = asyncio.Lock()


async def set_sleep(client_id):
    redis = ClientRedis(client_id)
    await redis.set_is_sleep(True)


def clean_txt(txt: str) -> str:
    txt = (
        txt.replace("\\n", " ").replace("\n", " ").replace("\t", " ").replace("\r", " ")
    )
    txt = re.sub(r"[^A-Za-zÀ-ỹ0-9\s%]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


async def stream_chat(client_id: str):
    redis = ClientRedis(client_id)
    language = await redis.get_language()
    speed_val = await redis.get_speaking_speed()
    speed = f"{speed_val-100:+d}%"
    chunk_mp3_queue = asyncio.Queue()

    async def producer():
        while True:
            message = await redis.pop_queue("messages")
            if message == "__END__":
                await chunk_mp3_queue.put(None)
                break
            if not message:
                await asyncio.sleep(0.05)
                continue

            message = clean_txt(message)

            print("TTS: ", message)
            voice = "vi-VN-HoaiMyNeural" if language == "vi" else "en-US-AriaNeural"
            communicate = edge_tts.Communicate(message, voice, volume="+0%", rate=speed)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    await chunk_mp3_queue.put(chunk["data"])

    asyncio.create_task(producer())

    while True:
        chunk_mp3 = await chunk_mp3_queue.get()
        if chunk_mp3 is None:
            break
        yield chunk_mp3


async def pcm_to_wav_bytes(
    client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
) -> str:
    """
    Chuyển thành file wav và lưu file.
    """
    os.makedirs("src/data/audio_message", exist_ok=True)
    path = f"src/data/audio_message/{client_id}.wav"
    if not pcm_buffer:
        print("Empty buffer, skipping.")
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

    if os.path.exists(path):
        os.remove(path)
    return message


async def process_buffer_text(buffer_text: str, redis, queue_name="messages"):
    """
    Tách buffer_text thành từng câu, push vào Redis queue và trả về phần còn lại chưa được push.
    """
    pattern = re.compile(r"[^.?!,]*[.?!,]")
    matches = pattern.findall(buffer_text)

    if matches:
        for sent in matches:
            sentence = sent.strip()
            if sentence:
                print("AI: " + sentence)
                await redis.push_queue(queue_name, sentence)
        buffer_text = re.sub(r"^.*[.?!,]", "", buffer_text)

    return buffer_text


async def stream_message(graph, input_state, config, client_id):
    redis = ClientRedis(client_id)
    is_sleep = await redis.get_is_sleep()
    if not await redis.is_empty_queue("messages"):
        await redis.clear_queue("messages")

    print("Started streaming TTS")
    await ws_client.send_text(client_id, "stream_message")

    buffer_text = ""
    music = False
    async for event in graph.astream(
        input=input_state,
        config=config,
        stream_mode=["messages", "updates", "custom"],
        subgraphs=True,
    ):
        subgraph, data_type, chunk = event
        if data_type == "messages":
            response, meta = chunk
            langgraph_node = meta.get("langgraph_node")
            if is_sleep:
                if isinstance(response, AIMessage):
                    buffer_text = response.content.strip()

            elif subgraph:
                if langgraph_node != "tools" and isinstance(response, AIMessageChunk):
                    text = response.content
                    if isinstance(text, list):
                        if response.content:
                            text = response.content[0]["text"]
                        else:
                            text = ""
                    if not text.strip():
                        continue
                    buffer_text += text

                    buffer_text = await process_buffer_text(
                        buffer_text, redis, "messages"
                    )
        elif data_type == "custom":
            if chunk.strip() == "stream_music":
                music = True
            elif chunk.strip().startswith("volume"):
                volume = chunk.strip().split(":")[1]
                await ws_client.send_text(client_id, f"volume:{volume}")
            elif chunk.strip().startswith("music_name"):
                music_name = chunk.strip().split(":")[1]
                await ws_client.send_text(client_id, f"music_name:{music_name}")
            elif chunk.strip().startswith("video_name"):
                video_name = chunk.strip().split(":")[1]
                await ws_client.send_text(client_id, f"music_name:{video_name}")
            else:
                await redis.push_queue("messages", chunk)
        elif data_type == "updates":
            pass

    if is_sleep and buffer_text != "false":
        print(f"End sleep from {client_id}")
        await ws_client.send_text(client_id, "end_sleep")
        await redis.set_is_sleep(False)
        await process_buffer_text(buffer_text, redis, "messages")
    await redis.push_queue("messages", "__END__")

    print("Finished streaming TTS")
    if music == True:
        await asyncio.sleep(7)
        print("Started streaming music")
        await ws_client.send_text(client_id, "stream_music")


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
        print("Finished streaming music")
