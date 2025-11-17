import re
import logging
import asyncio
import re
from yt_dlp import YoutubeDL
import os
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn
from src.config.setup import GOOGLE_API_KEY
import unicodedata
from tavily import AsyncTavilyClient
from src.config.setup import TAVILY_API_KEY
from src.db.connection import get_supabase
from langchain_community.vectorstores import FAISS
from src.model import embedding_model
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


sreacher = AsyncTavilyClient(api_key=TAVILY_API_KEY)

import logging

logger = logging.getLogger("chat_logger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def remove_vietnamese_accents(text):
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    return text


def force_ipv4():
    def allowed_gai_family():
        return socket.AF_INET

    urllib3_cn.allowed_gai_family = allowed_gai_family


def clean_txt(txt: str) -> str:
    txt = (
        txt.replace("\\n", " ").replace("\n", " ").replace("\t", " ").replace("\r", " ")
    )

    txt = re.sub(r"[^A-Za-zÀ-ỹ0-9\s]", " ", txt)

    txt = re.sub(r"\s+", " ", txt).strip()

    return txt


async def find_music(music_name: str) -> tuple[str, str]:
    """
    Tìm video bài theo tên bài nhạc.
    """
    force_ipv4()
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={music_name}&key={GOOGLE_API_KEY}&maxResults=10"

    def _get():
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()

    data = await asyncio.to_thread(_get)

    video = data["items"][0]
    video_id = video["id"]["videoId"]
    video_title = video["snippet"]["title"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    return video_title, video_url


async def download_audio(url: str, client_id: str, bitrate: str = "128") -> str:
    """
    Tải audio từ YouTube về file và lưu.
    """
    force_ipv4()
    save_path = f"src/data/music/{client_id}"
    os.makedirs("src/data/music", exist_ok=True)
    ytdl_opts = {
        "format": "bestaudio[ext=webm][abr<=64]/bestaudio/best",
        "outtmpl": save_path,
        "quiet": False,
        "force_ipv4": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }
        ],
    }

    def _download():
        with YoutubeDL(ytdl_opts) as ydl:
            ydl.download([url])

    await asyncio.to_thread(_download)
    return save_path


async def download_pdf(client_id: str) -> str:
    """
    Tải file pdf từ supabase và trả về đường dẫn trong thư mục local.
    """
    path = f"src/data/pdf/{client_id}.pdf"
    if os.path.exists(path):
        return path
    supabase = await get_supabase()
    with open(path, "wb+") as f:
        response = await supabase.storage.from_("pdf_data").download(
            f"public/{client_id}.pdf"
        )
        f.write(response)

    return path


async def read_content(path: str, query: str) -> str:
    """
    Đưa file pdf vào embedding và trả về nội dung cần theo query.
    """
    loader = PyPDFLoader(path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=100
    )
    documents_splits = text_splitter.split_documents(documents)

    vectorstore = await FAISS.afrom_documents(
        documents=documents_splits,
        embedding=embedding_model,
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
    )

    response = await retriever.ainvoke(query)

    content = ""

    for doc in response:
        content += doc.page_content + "\n\n"

    return content
