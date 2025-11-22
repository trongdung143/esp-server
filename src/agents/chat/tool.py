from langchain.tools import tool, ToolRuntime
from datetime import datetime

from src.db.redis_operation import ClientRedis
from src.agents.base import BaseAgent
from src.agents.chat.prompt import prompt_rag
from src.agents.chat.utils import (
    find_music,
    download_audio,
    remove_vietnamese_accents,
    sreacher,
    read_content,
)
from src.log import logger
from src.db.supabase_operation import ClientSupaBase


@tool
async def play_music(music_name: str, runtime: ToolRuntime) -> str:
    """
    Phát bài nhạc theo tên từ YouTube.

    Args:
        music_name (str): Tên bài hát cần phát.

    """
    writer = runtime.stream_writer
    client_id = runtime.state.get("client_id")

    writer("đang tìm nhạc")
    title, url = await find_music(music_name)

    writer("đang chuẩn bị phát nhạc")
    await download_audio(url, client_id)

    writer(f"chuẩn bị mở {title} sau 3 giây")
    writer(f"music_name:{remove_vietnamese_accents(title)}")
    writer("stream_music")
    return f"đã mở"


@tool
async def play_yt(query: str, runtime: ToolRuntime) -> str:
    """
    Phát bất kỳ audio YouTube nào dựa trên tên yêu cầu.

    Args:
        query (str): Tên yêu cầu video nội dung.

    """
    writer = runtime.stream_writer
    client_id = runtime.state.get("client_id")

    writer("Đang tìm kiếm")
    title, url = await find_music(query)

    writer("Đang chuẩn bị phát")
    await download_audio(url, client_id)

    writer(f"Chuẩn bị mở '{title}' sau 3 giây")
    writer(f"video_name:{remove_vietnamese_accents(title)}")
    writer("stream_music")

    return "Đã mở"


@tool
def get_time(runtime: ToolRuntime) -> str:
    """
    Lấy thời gian hiện tại.

    Returns:
        str: Thời gian hiện tại.
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    return f"{hour} giờ {minute} phút"


@tool
async def set_speaking_speed(speed: str, runtime: ToolRuntime) -> str:
    """
    Dùng để thay đổi tốc độ nói.

    Args:
        speed (str): up (nói nhanh hơn) or down (nói chậm hơn).
    """
    client_id = runtime.state.get("client_id")
    redis = ClientRedis(client_id)

    speed_val = await redis.get_speaking_speed()
    if speed.strip() == "up":
        await redis.set_speaking_speed(int(speed_val + 30))
        return "đã nói nhanh hơn."
    else:
        await redis.set_speaking_speed(int(speed_val - 30))
        return "đã nói chậm hơn."


@tool
async def sreach(query: str, runtime: ToolRuntime) -> str:
    """
    Dùng để tìm kiếm thông tin, tin tức mới.

    Args:
        query (str): Nội dung cần tìm kiếm

    Returns:
        str: Nội dung tìm kiếm được.
    """

    writer = runtime.stream_writer

    writer("đang tìm kiếm thông tin")
    response = await sreacher.search(
        query=query, include_raw_content="text", max_results=3
    )
    results = response.get("results")
    content = ""

    for result in results:
        content += result.get("content") + "\n\n"
    return content


@tool
async def set_volume(volume: str, runtime: ToolRuntime) -> str:
    """
    Dùng để thay đổi âm lượng nói.

    Args:
        speed (str): up (nói to hơn) or down (nói nhỏ hơn).
    """

    client_id = runtime.state.get("client_id")
    writer = runtime.stream_writer
    redis = ClientRedis(client_id)

    volume_val = await redis.get_volume()
    if volume.strip() == "up":
        await redis.set_volume(volume_val + 5)
        writer(f"volume:{volume_val + 5}")
        return "đã nói to hơn."
    else:
        await redis.set_volume(volume_val - 5)
        writer(f"volume:{volume_val - 5}")
        return "đã nói nhỏ hơn."


@tool
async def rag(query: str, pdf_id: str, runtime: ToolRuntime) -> str:
    """
    Dùng để lấy thông tin từ tệp pdf có của người dùng.

    Args:
        query (str): Thông tin cần hỏi.
        pdf_id (str): Id của file pdf cần lấy thông tin.

    Returns:
        Nội dung trả.
    """

    client_id = runtime.state.get("client_id")
    supabase = ClientSupaBase(client_id)
    writer = runtime.stream_writer
    agent = BaseAgent("rag", None, None)
    chain = prompt_rag | agent.get_model()

    path = await supabase.download_pdf(pdf_id.strip())

    if path is None:
        writer("đã có lỗi khi lấy tài liệu")
        return "đã có lỗi"

    context = await read_content(path, query)
    if context is None:
        writer("đã có lỗi khi đọc tài liệu")
        return "đã có lỗi"

    writer("đang đọc tài liệu")
    try:
        response = await chain.ainvoke({"query": query, "context": context})
    except:
        logger.exception("[RagAgent] Exception occurred")
        return "đã có lỗi"
    return response.content


@tool
async def get_list_summary_pdf(runtime: ToolRuntime):
    """
    Dùng để xem nội dung tóm tắt các file pdf trước khi chọn file dùng để xử lý yêu cầu của người.

    Returns:
        str: Nội dung tóm tắt các file pdf, id của file ở đầu mỗi tóm tắt và thời gian tải file lên.
    """
    client_id = runtime.state.get("client_id")
    writer = runtime.stream_writer
    writer("đang tìm tài liệu")
    supabase = ClientSupaBase(client_id)
    summaries = await supabase.get_list_summary_pdf()
    if summaries == []:
        return "chưa có tài liệu nào được tải lên"
    content = ""
    for item in summaries:
        pdf_id = item.get("pdf_id")
        summary = item.get("summary")
        time = pdf_id.split("_")
        str_time = f"{time[2]} giờ {time[1]} phút ngày {time[3]}-{time[4]}-{time[5]}"
        content += (
            f"id: {pdf_id}\nthời gian tải lên: {str_time}\ntóm tắt: {summary}\n\n"
        )
    return content


tools = [get_time, play_music, set_volume, play_yt, rag, sreach, get_list_summary_pdf]
