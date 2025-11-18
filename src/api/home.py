from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


router = APIRouter()


@router.get("/")
async def home():
    return {"message": "hello"}


@router.get("/handshake")
async def handshake(client_id: str):
    return {"type": "true"}
