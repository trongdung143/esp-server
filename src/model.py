from faster_whisper import WhisperModel
import os
import shutil
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from src.config.setup import GOOGLE_API_KEY

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY
)


# model_name = "small"
# download_root = f"src/models/faster-whisper-{model_name}"

# stt_model = None

# try:
#     stt_model = WhisperModel(
#         download_root, device="cpu", compute_type="int8", local_files_only=True
#     )
# except:
#     stt_model = WhisperModel(
#         model_name,
#         device="cpu",
#         compute_type="int8",
#         download_root=download_root,
#     )
#     model_folders = [f for f in os.listdir(download_root) if f.startswith("models--")]
#     if not model_folders:
#         raise FileNotFoundError("error: no model")
#     model_folder = os.path.join(download_root, model_folders[0])

#     snapshots_path = os.path.join(model_folder, "snapshots")
#     snapshots = os.listdir(snapshots_path)
#     snapshots.sort()
#     latest_snapshot = snapshots[-1]

#     src_folder = os.path.join(snapshots_path, latest_snapshot)

#     for item in os.listdir(src_folder):
#         s = os.path.join(src_folder, item)
#         d = os.path.join(download_root, item)
#         if os.path.isdir(s):
#             shutil.copytree(s, d, dirs_exist_ok=True)
#         else:
#             shutil.copy2(s, d)
# finally:
#     stt_model = WhisperModel(
#         download_root, device="cpu", compute_type="int8", local_files_only=True
#     )
