from fastapi import APIRouter, WebSocket, Query
from langchain_core.messages import HumanMessage

from src.api.utils.stt import stt_from_pcm
from src.api.utils.stream_chat import stream_message, end_chat
from src.db.redis_operation import ClientRedis
from src.agents.workflow import graph
from src.ws_manager import ws_client
from src.log import logger

router = APIRouter()


async def set_sleep(client_id):
    redis = ClientRedis(client_id)
    await redis.set_is_sleep(True)


@router.websocket("/chat")
async def chat_ep(websocket: WebSocket, client_id: str = Query(...)):
    await ws_client.hello_server(client_id, websocket)
    client_id = client_id
    try:
        pcm_buffer = bytearray()
        while True:
            data = await ws_client.get_data(client_id)

            if data == "disconnect":
                logger.info(f"Disconnected: {client_id}")
                break

            if "text" in data:
                msg = data["text"].strip()

                if msg.startswith("START_CHAT"):
                    logger.info(f"Start from {client_id}")
                    pcm_buffer.clear()
                    continue

                elif msg == "END_CHAT":
                    logger.info(f"End from {client_id}")
                    text = await stt_from_pcm(client_id, pcm_buffer)
                    # if text == "...":
                    #     await end_chat(client_id)
                    #     continue
                    logger.info(f"USER: {text}")
                    input_state = {
                        "client_id": client_id,
                        "messages": HumanMessage(content=text),
                    }

                    config = {
                        "configurable": {
                            "thread_id": client_id,
                        }
                    }
                    await stream_message(graph, input_state, config, client_id)
                    pcm_buffer.clear()
                    continue
                elif msg == "START_SLEEP":
                    logger.info(f"Start sleep from {client_id}")
                    await set_sleep(client_id)

            elif "bytes" in data:
                chunk = data["bytes"]
                pcm_buffer.extend(chunk)

    except RuntimeError as e:
        pass

    finally:
        logger.info(f"Closed connection for {client_id}")
