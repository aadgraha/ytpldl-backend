from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
import uuid
import threading
import time
import yt_dlp

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}

def get_final_name(info, mode):
    title = info.get("title", "unknown")
    ext = "m4a" if mode == "audio" else "mp4"
    return f"{title}.{ext}"


# -----------------------------
# SMOOTH MERGE PROGRESS
# -----------------------------
def smooth_merge(folder_id, filename):
    for i in range(90, 99):
        time.sleep(0.2)

        if filename in jobs[folder_id]["files"]:
            jobs[folder_id]["files"][filename]["progress"] = i / 100
            jobs[folder_id]["files"][filename]["status"] = "processing"


# -----------------------------
# DOWNLOAD LOGIC
# -----------------------------
def run_download(folder_id: str, url: str, mode: str):
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)

    jobs[folder_id] = {
        "status": "downloading",
        "files": {},
    }

    # -----------------------------
    # PROGRESS HOOK
    # -----------------------------
    def progress_hook(d):
        info = d.get("info_dict", {})
        final_name = get_final_name(info, mode)

        if final_name not in jobs[folder_id]["files"]:
            jobs[folder_id]["files"][final_name] = {
                "progress": 0.0,
                "status": "downloading",
            }

        # downloading phase
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)

            raw_progress = downloaded / total

            # scale to 0 → 0.9
            jobs[folder_id]["files"][final_name]["progress"] = raw_progress * 0.9

        # download finished → start merge smoothing
        elif d["status"] == "finished":
            jobs[folder_id]["files"][final_name]["progress"] = 0.9
            jobs[folder_id]["files"][final_name]["status"] = "processing"

            threading.Thread(
                target=smooth_merge,
                args=(folder_id, final_name),
                daemon=True
            ).start()

    # -----------------------------
    # POST HOOK (FINAL)
    # -----------------------------
    def post_hook(d):
        if d["status"] == "finished":
            info = d.get("info_dict", {})
            final_name = get_final_name(info, mode)

            jobs[folder_id]["files"][final_name] = {
                "progress": 1.0,
                "status": "finished",
            }

    # -----------------------------
    # YT-DLP OPTIONS
    # -----------------------------
    ydl_opts = {
        "outtmpl": os.path.join(folder_path, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [post_hook],
        "restrictfilenames": True,
    }

    if mode == "audio":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }],
            "keepvideo": False,  # remove temp mp4/webm
        })

    elif mode == "video":
        ydl_opts.update({
            "format": "bv*[ext=mp4]+ba[ext=m4a]/mp4",
            "merge_output_format": "mp4",
        })

    # -----------------------------
    # RUN
    # -----------------------------
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

    threading.Thread(
        target=run_download,
        args=(folder_id, url, mode),
        daemon=True
    ).start()

    return {"folder": folder_id}


# -----------------------------
# STATUS
# -----------------------------
@app.get("/status/{folder_id}")
def get_status(folder_id: str):
    if folder_id not in jobs:
        return {"error": "job not found"}

    files = [
        {
            "name": name,
            "progress": data["progress"],
            "status": data["status"]
        }
        for name, data in jobs[folder_id]["files"].items()
    ]

    return {
        "status": jobs[folder_id]["status"],
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