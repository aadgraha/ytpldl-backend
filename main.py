from fastapi import FastAPI
from fastapi.responses import FileResponse
import subprocess
import os
import uuid

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.get("/download")
def download(url: str, mode: str = "video"):
    folder_id = str(uuid.uuid4())
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)
    os.makedirs(folder_path, exist_ok=True)

    if mode == "audio":
        command = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "m4a",
            "--audio-quality", "0",
            "--embed-thumbnail", 
            "--add-metadata",
            "-o", os.path.join(folder_path, "%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    elif mode == "video":
        command = [
            "yt-dlp",
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/mp4",
            "--merge-output-format", "mp4",
            "-o", os.path.join(folder_path, "%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    else:
        return {"error": "invalid mode"}

    subprocess.run(command)

    files = sorted([
        f for f in os.listdir(folder_path)
        if f.endswith(".mp4") or f.endswith(".m4a")
    ])

    return {
        "folder": folder_id,
        "files": files,
    }

@app.get("/file/{folder}/{filename}")
def get_file(folder: str, filename: str):
    path = os.path.join(DOWNLOAD_DIR, folder, filename)
    return FileResponse(path)