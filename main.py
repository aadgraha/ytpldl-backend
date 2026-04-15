from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
import uuid
import threading
import yt_dlp

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory store (use Redis/DB in production)
jobs = {}


# -----------------------------
# DOWNLOAD LOGIC (BACKGROUND)
# -----------------------------
def run_download(folder_id: str, url: str, mode: str):
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)

    jobs[folder_id] = {
        "status": "downloading",
        "files": {},  # filename -> progress
    }

    def progress_hook(d):
        filename = os.path.basename(d.get("filename", "unknown"))

        if filename not in jobs[folder_id]["files"]:
            jobs[folder_id]["files"][filename] = {
                "progress": 0.0,
                "status": "downloading",
            }

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)

            jobs[folder_id]["files"][filename]["progress"] = downloaded / total

        elif d["status"] == "finished":
            jobs[folder_id]["files"][filename]["progress"] = 1.0
            jobs[folder_id]["files"][filename]["status"] = "finished"

    ydl_opts = {
        "outtmpl": os.path.join(folder_path, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "restrictfilenames": True,
    }

    if mode == "audio":
        ydl_opts.update({
            "format": "bestaudio",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }],
        })

    elif mode == "video":
        ydl_opts.update({
            "format": "bv*[ext=mp4]+ba[ext=m4a]/mp4",
            "merge_output_format": "mp4",
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        jobs[folder_id]["status"] = "completed"

    except Exception as e:
        jobs[folder_id]["status"] = "error"
        jobs[folder_id]["error"] = str(e)


# -----------------------------
# START DOWNLOAD
# -----------------------------
@app.get("/download")
def download(url: str, mode: str = "video"):
    folder_id = str(uuid.uuid4())
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)
    os.makedirs(folder_path, exist_ok=True)

    thread = threading.Thread(
        target=run_download,
        args=(folder_id, url, mode),
        daemon=True
    )
    thread.start()

    return {
        "folder": folder_id,
    }


# -----------------------------
# CHECK STATUS + PROGRESS
# -----------------------------
@app.get("/status/{folder_id}")
def get_status(folder_id: str):
    if folder_id not in jobs:
        return {"error": "job not found"}

    files_map = jobs[folder_id]["files"]

    files_list = [
        {
            "name": name,
            "progress": data["progress"],
            "status": data["status"]
        }
        for name, data in files_map.items()
    ]

    return {
        "status": jobs[folder_id]["status"],
        "files": files_list
    }


# -----------------------------
# LIST READY FILES
# -----------------------------
@app.get("/files/{folder_id}")
def list_files(folder_id: str):
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)

    if not os.path.exists(folder_path):
        return {"error": "not found"}

    files = sorted([
        f for f in os.listdir(folder_path)
        if f.endswith(".mp4") or f.endswith(".m4a")
    ])

    return {
        "folder": folder_id,
        "files": files
    }


# -----------------------------
# DOWNLOAD FILE
# -----------------------------
@app.get("/file/{folder}/{filename}")
def get_file(folder: str, filename: str):
    path = os.path.join(DOWNLOAD_DIR, folder, filename)

    if not os.path.exists(path):
        return {"error": "file not found"}

    return FileResponse(path, filename=filename)