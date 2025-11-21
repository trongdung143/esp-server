from fastapi import APIRouter
from src.db.supabase_operation import ClientSupaBase
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/")
async def home():
    return {"message": "hello"}


@router.get("/handshake")
async def handshake(client_id: str):
    supabase = ClientSupaBase(client_id)
    exists = await supabase.is_client_exists()
    if not exists:
        return PlainTextResponse("false")
    return PlainTextResponse("true")
