import edge_tts
import soundfile as sf
import re
import numpy as np
from src.db.operation import ClientRedis
import os
import asyncio
from langchain_core.messages import AIMessageChunk
from src.ws_manager import ws_client
import httpx
from src.config.setup import STT_URL


def clean_txt(txt: str) -> str:
    txt = (
        txt.replace("\\n", " ").replace("\n", " ").replace("\t", " ").replace("\r", " ")
    )
    txt = re.sub(r"[^A-Za-zÀ-ỹ0-9\s%]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


async def tts_task(idx, message, voice, speed, output_queue):
    if idx != 0:
        await asyncio.sleep(0.2)
    buff = []
    communicate = edge_tts.Communicate(message, voice, volume="+0%", rate=speed)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buff.append(chunk["data"])
    await output_queue.put((idx, buff))


async def stream_chat(client_id: str):
    redis = ClientRedis(client_id)
    language = await redis.get_language()
    speed_val = await redis.get_speaking_speed()
    speed = f"{speed_val-100:+d}%"
    output_queue = asyncio.Queue()
    results = []
    printed = 0
    idx = 0
    tts_tasks = []

    while True:
        message = await redis.pop_queue("messages")
        if message == "__END__":
            break
        if not message:
            await asyncio.sleep(0.05)
            continue

        message = clean_txt(message)
        print("TTS: ", message)
        voice = "vi-VN-HoaiMyNeural" if language == "vi" else "en-US-AriaNeural"
        results.append(None)
        tts_tasks.append(
            asyncio.create_task(tts_task(idx, message, voice, speed, output_queue))
        )
        idx += 1
        while not output_queue.empty():
            task_idx, buff = await output_queue.get()
            results[task_idx] = buff
            while printed < len(results) and results[printed] is not None:
                for c in results[printed]:
                    yield c
                    await asyncio.sleep(0.05)
                printed += 1

    await asyncio.gather(*tts_tasks)

    while printed < len(results):
        task_idx, buff = await output_queue.get()
        results[task_idx] = buff
        while printed < len(results) and results[printed] is not None:
            for c in results[printed]:
                yield c
                await asyncio.sleep(0)
            printed += 1

    if idx == 0:
        voice = "vi-VN-HoaiMyNeural" if language == "vi" else "en-US-AriaNeural"
        communicate = edge_tts.Communicate(
            "tôi không hiểu bạn đang nói gì", voice, volume="+0%", rate=speed
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]


async def pcm_to_wav_bytes(
    client_id: str, pcm_buffer: bytearray, sample_rate: int = 16000
) -> str:
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
    path = await pcm_to_wav_bytes(client_id, pcm_buffer)
    async with httpx.AsyncClient() as client:
        with open(path, "rb") as f:
            files = {"file": (f.name, f, "audio/wav")}
            r = await client.post(STT_URL, files=files)
    message = r.json()["text"]
    print(f"USER: {message}")
    if os.path.exists(path):
        os.remove(path)
    return message


async def process_buffer_text(buffer_text: str, redis, queue_name="messages"):
    """
    Tách buffer_text thành từng câu, push vào Redis queue,
    và trả về phần còn lại chưa được push.
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
        if subgraph:
            if data_type == "messages":
                response, meta = chunk
                langgraph_node = meta.get("langgraph_node")
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

    await redis.push_queue("messages", "__END__")
    print("Finished streaming TTS")
    if music == True:
        await asyncio.sleep(7)
        print("Started streaming music")
        await ws_client.send_text(client_id, "stream_music")


async def stream_music(file_path: str, chunk_size: int = 2024):
    """
    Stream file mp3 theo chunk bất đồng bộ.
    Xóa file sau khi gửi xong.
    """
    try:
        with open(file_path, "rb") as f:
            while chunk := await asyncio.to_thread(f.read, chunk_size):
                yield chunk
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        print("Finished streaming music")
