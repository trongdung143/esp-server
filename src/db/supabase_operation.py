from src.db.connection import supabase
import os
from src.log import logger


class ClientSupaBase:
    def __init__(self, client_id: str):
        self._con = supabase
        self._client_id = client_id

    def download_pdf(self) -> str | None:
        path = f"src/data/pdf/{self._client_id}.pdf"
        if os.path.exists(path):
            return path

        try:
            with open(path, "wb+") as f:
                response = self._con.storage.from_("pdf_data").download(
                    f"public/{self._client_id}.pdf"
                )
                f.write(response)
        except:
            logger.exception("đã có lỗi khi tải file")
            return None
        return path
