# ESP32 Chatbot Server

Một máy chủ chatbot thông minh được xây dựng bằng FastAPI, LangGraph, và các công nghệ AI hiện đại. Dự án này cung cấp các khả năng xử lý ngôn ngữ tự nhiên, nhận dạng giọng nói, tổng hợp giọng nói, và quản lý cuộc hội thoại thông qua WebSocket.

## 🎯 

- **Chat Agent**: Tương tác qua API REST và WebSocket
- **Speech-to-Text (STT)**: Chuyển đổi giọng nói thành văn bản sử dụng Faster Whisper
- **Text-to-Speech (TTS)**: Tổng hợp giọng nói từ văn bản bằng ElevenLabs và Edge TTS
- **Wake Word Detection**: Phát hiện từ khóa để kích hoạt bot
- **LangGraph Workflow**: Xây dựng quy trình xử lý phức tạp với AI agents
- **Redis Cache**: Lưu trữ và quản lý trạng thái phiên
- **Database Integration**: Kết nối Supabase và PostgreSQL

## 📋 Yêu cầu hệ thống

- Python 3.9+
- Redis (để caching)
- PostgreSQL hoặc Supabase (để lưu trữ dữ liệu)
- API keys từ:
  - Google Generative AI (Gemini)
  - Tavily Search
  - ElevenLabs (tùy chọn)
  - Supabase (nếu sử dụng)

## 🚀 Cài đặt

### 1. Clone dự án
```bash
git clone <repository-url>
cd esp32_server
```

### 2. Tạo Virtual Environment
```bash
python -m venv venv

# Trên Windows
venv\Scripts\activate

# Trên macOS/Linux
source venv/bin/activate
```

### 3. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình Environment Variables
Tạo file `.env` trong thư mục gốc với các biến sau:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key (tùy chọn)

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Redis
REDIS_URL=redis://localhost:6379

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### 5. Khởi tạo Database
```bash
# Tạo bảng và cấu trúc database (nếu cần)
# Chi tiết xem trong src/db/connection.py
```

## 📁 Cấu trúc dự án

```
esp32_server/
├── src/
│   ├── main.py                 # Entry point FastAPI
│   ├── log.py                  # Cấu hình logging
│   ├── model.py                # Data models
│   ├── ws_manager.py           # WebSocket manager
│   │
│   ├── agents/                 # LangGraph agents
│   │   ├── base.py             # Base agent class
│   │   ├── state.py            # State definition
│   │   ├── workflow.py         # Workflow orchestration
│   │   ├── wake_word.py        # Wake word detection
│   │   └── chat/               # Chat agent
│   │       ├── chat.py         # Main chat logic
│   │       ├── prompt.py       # Prompts & templates
│   │       ├── tool.py         # Tools cho chat agent
│   │       └── utils.py        # Utility functions
│   │
│   ├── api/                    # API endpoints
│   │   ├── chat.py             # Chat endpoints
│   │   ├── home.py             # Home/health endpoints
│   │   ├── stream.py           # Streaming endpoints
│   │   └── utils/
│   │       ├── stream_chat.py  # Chat streaming logic
│   │       ├── stream_music.py # Music streaming logic
│   │       └── stt.py          # Speech-to-text
│   │
│   ├── config/                 # Configuration
│   │   └── setup.py            # Setup utilities
│   │
│   ├── db/                     # Database operations
│   │   ├── connection.py       # DB connections
│   │   ├── redis_operation.py  # Redis operations
│   │   └── supabase_operation.py # Supabase operations
│   │
│   └── data/                   # Data directories
│       ├── music/              # Music cache
│       └── pdf/                # PDF storage
│
├── requirements.txt            # Python dependencies
├── langgraph.json              # LangGraph configuration
├── render.yml                  # Deployment configuration
├── LICENSE                     # License
└── README.md                   # Documentation
```

## 🔧 Sử dụng

### 1. Khởi động Server
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại `http://localhost:8000`

### 2. API Endpoints

#### Health Check
```bash
GET /
```
Trả về trạng thái máy chủ.

#### Chat API
```bash
POST /chat
Content-Type: application/json

{
  "client_id": "user_123",
  "message": "Xin chào, bạn tên gì?",
  "conversation_id": "conv_456"
}
```

#### WebSocket Chat
```
WS ws://localhost:8000/ws/chat/{client_id}
```
Kết nối WebSocket để chat real-time.

#### STT Stream
```bash
POST /stream/stt
Content-Type: audio/wav

[binary audio data]
```
Gửi audio stream và nhận text response.

#### Music Stream
```bash
GET /stream/music?query=artist+song
```
Lấy stream nhạc từ YouTube.

### 3. Ví dụ sử dụng Python

```python
import requests

# Chat
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "client_id": "user_123",
        "message": "Bạn biết gì về AI?",
        "conversation_id": "conv_1"
    }
)
print(response.json())

# WebSocket
import asyncio
import websockets
import json

async def chat_ws():
    async with websockets.connect("ws://localhost:8000/ws/chat/user_123") as websocket:
        await websocket.send(json.dumps({"message": "Xin chào"}))
        response = await websocket.recv()
        print(response)

asyncio.run(chat_ws())
```

## 🤖 Agents & Workflow

### Chat Agent
- Xử lý cuộc hội thoại
- Sử dụng Google Generative AI (Gemini)
- Hỗ trợ các tools như tìm kiếm web, phân tích PDF, phát nhạc, ...

### Wake Word Detection
- Phát hiện từ khóa để kích hoạt bot
- Trạng thái sleep/wake được lưu trong Redis

### State Management
Mỗi conversation có một state chứa:
- `messages`: Lịch sử tin nhắn
- `client_id`: ID của client
- `conversation_id`: ID của conversation
- `is_sleep`: Trạng thái ngủ của bot

## 🗄️ Database

### Redis
- Lưu trữ trạng thái phiên
- Cache dữ liệu tạm thời
- Quản lý sleep state

### PostgreSQL/Supabase
- Lưu trữ lịch sử cuộc hội thoại
- Lưu embedding vector
- Quản lý dữ liệu người dùng

## 📚 Dependencies chính

| Thư viện | Mục đích |
|---------|---------|
| `FastAPI` | Framework web |
| `LangGraph` | Orchestration agents |
| `LangChain` | LLM integration |
| `faster-whisper` | Speech-to-text |
| `elevenlabs` | Text-to-speech |
| `redis` | Caching & session |
| `faiss-cpu` | Vector search |
| `supabase` | Database |
| `uvicorn` | ASGI server |

## 🔐 Bảo mật

- **CORS**: Chỉ cho phép localhost (cấu hình trong `main.py`)
- **Malicious Request Filter**: Chặn các request nghi ngờ
- **Environment Variables**: Không commit credentials
- **Input Validation**: Sử dụng Pydantic models

## 🧪 Testing

Chạy tests:
```bash
pytest tests/ -v
```

Xem file `test.py` và `test.ipynb` để các ví dụ test.

## 📝 Logging

Logging được cấu hình trong `src/log.py`. Các log được lưu vào:
- Console output
- File logs (nếu cấu hình)

Xem cấu hình trong `src/log.py` để tuỳ chỉnh.

## 🚢 Deployment

### Render.yml
Cấu hình triển khai tự động. Xem `render.yml` để chi tiết.

### Environment cho Production
```env
DEBUG=False
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
```

## 🐛 Troubleshooting

### Redis Connection Error
```
Error: Connection to Redis failed
```
**Giải pháp**: Đảm bảo Redis đang chạy
```bash
redis-server
```

### Database Connection Error
```
Error: Can't connect to database
```
**Giải pháp**: Kiểm tra `DATABASE_URL` và thông tin đăng nhập

### API Key Errors
```
Error: Invalid API key
```
**Giải pháp**: Cập nhật API keys trong `.env`

### Port Already in Use
```
Error: Address already in use
```
**Giải pháp**: Dùng port khác
```bash
python -m uvicorn src.main:app --port 8001
```

## 📖 Thêm tài liệu

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)


## 📜 Giấy Phép

Copyright (C) 2025 TrongDung143

Dự án này được cấp phép theo **GNU General Public License v3.0 (GPLv3)**.

Xem file [LICENSE](LICENSE) để biết toàn bộ nội dung giấy phép.

## 👨‍💻 Tác Giả

**TrongDung143**

## 📞 Liên Hệ & Hỗ Trợ
[facebook](https://www.facebook.com/ltd.nma.143)
[email](trongdung143@gmail.com)