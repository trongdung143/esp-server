import os

from src.log import logger


class ClientSupaBase:
    def __init__(self, client_id: str):
        self._client_id = client_id

    async def _ensure_client(self):
        from src.db.connection import init_supabase

        client = await init_supabase()
        return client

    async def download_pdf(self, pdf_id: str) -> str | None:
        os.makedirs("src/data/pdf", exist_ok=True)
        path = f"src/data/pdf/{self._client_id}.pdf"
        if os.path.exists(path):
            return path

        try:
            con = await self._ensure_client()
            with open(path, "wb+") as f:
                response = await con.storage.from_("pdf_data").download(
                    f"{self._client_id}/{pdf_id}.pdf"
                )
                f.write(response)
        except Exception:
            logger.exception("Đã có lỗi khi tải file")
            return None

        return path

    async def get_list_summary_pdf(self) -> list[tuple[str, str]]:
        try:
            con = await self._ensure_client()
            response = await (
                con.table("pdf_summary")
                .select("*")
                .eq("client_id", self._client_id)
                .execute()
            )
            if response.data is None:
                return []

            return response.data

        except Exception:
            logger.exception("Đã có lỗi khi lấy danh sách summary")
            return []

    async def is_client_exists(self) -> bool:
        try:
            con = await self._ensure_client()
            response = await (
                con.table("clients_info")
                .select("client_id")
                .eq("client_id", self._client_id)
                .execute()
            )
            if response.data == []:
                return False
            return True
        except Exception:
            logger.exception("Đã có lỗi khi kiểm tra client_id")
            return False

    async def add_client(self):
        try:
            con = await self._ensure_client()
            await (
                con.table("clients_info")
                .insert({"client_id": self._client_id})
                .execute()
            )

        except Exception:
            logger.exception("Đã có lỗi khi thêm client_id")
