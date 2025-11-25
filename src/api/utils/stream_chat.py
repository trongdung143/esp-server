import re

import asyncio
from langchain_core.messages import AIMessageChunk, AIMessage

import edge_tts


from src.db.redis_operation import ClientRedis
from src.ws_manager import ws_client
from src.log import logger


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

            logger.info(f"TTS: {message}")
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
                # logger.info("AI: " + sentence)
                await redis.push_queue(queue_name, sentence)
        buffer_text = re.sub(r"^.*[.?!,]", "", buffer_text)

    return buffer_text


async def stream_message(graph, input_state, config, client_id):
    redis = ClientRedis(client_id)
    is_sleep = await redis.get_is_sleep()
    if not await redis.is_empty_queue("messages"):
        await redis.clear_queue("messages")

    logger.info("Started streaming TTS")
    await ws_client.send_text(client_id, "stream_chat")

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
            if chunk.strip().startswith("stream_music"):
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
            elif chunk.strip().startswith("start_sleep"):
                await ws_client.send_text(client_id, f"start_sleep")
            else:
                await redis.push_queue("messages", chunk)
        elif data_type == "updates":
            pass

    if is_sleep and buffer_text != "false":
        logger.info(f"End sleep from {client_id}")
        await ws_client.send_text(client_id, "end_sleep")
        await redis.set_is_sleep(False)
        await process_buffer_text(buffer_text, redis, "messages")
    await redis.push_queue("messages", "__END__")

    logger.info("Finished streaming TTS")
    if music == True:
        await asyncio.sleep(7)
        logger.info("Started streaming music")
        await ws_client.send_text(client_id, "stream_music")


async def end_chat(client_id: str):
    await ws_client.send_text(client_id, "end_chat")
