from fastapi import APIRouter, WebSocket, HTTPException, Query
from src.api.utils import stt_from_pcm, stream_chat, stream_message, stream_music
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from src.agents.workflow import graph
from src.db.operation import ClientRedis
from src.ws_manager import ws_client

router = APIRouter()


@router.get("/")
async def home():
    return {"message": "hello"}


@router.websocket("/chat")
async def chat_ep(websocket: WebSocket, client_id: str = Query(...)):
    await ws_client.hello_server(client_id, websocket)
    client_id = client_id
    try:
        pcm_buffer = bytearray()
        while True:
            data = await ws_client.get_data(client_id)

            if data == "disconnect":
                print(f"Disconnected: {client_id}")
                break

            if "text" in data:
                msg = data["text"].strip()

                if msg.startswith("start_chat"):
                    print(f"Start from {client_id}")
                    pcm_buffer.clear()
                    continue

                elif msg == "end_chat":
                    print(f"End from {client_id}")
                    text = await stt_from_pcm(pcm_buffer)
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

            elif "bytes" in data:
                chunk = data["bytes"]
                pcm_buffer.extend(chunk)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        print(f"Closed connection for {client_id}")
