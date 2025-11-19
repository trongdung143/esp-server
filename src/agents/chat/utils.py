import asyncio
import os
import re
import socket
import unicodedata

import requests
import requests.packages.urllib3.util.connection as urllib3_cn
from yt_dlp import YoutubeDL
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tavily import AsyncTavilyClient

from src.config.setup import GOOGLE_API_KEY, TAVILY_API_KEY
from src.model import embedding_model
from src.log import logger

sreacher = AsyncTavilyClient(api_key=TAVILY_API_KEY)


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


async def read_content(path: str, query: str) -> str | None:
    """
    Đưa file pdf vào embedding và trả về nội dung cần theo query.
    """
    content = ""
    try:
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

        for doc in response:
            content += doc.page_content + "\n\n"

        if os.path.exists(path):
            os.remove(path)

    except:
        logger.exception("đã có lỗi khi đọc tài liệu")
        return None
    return content
