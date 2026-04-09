from fastapi import FastAPI
from fastapi.responses import FileResponse
import subprocess
import os
import uuid

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.get("/download")
def download(url: str, mode: str = "single_audio"):
    folder_id = str(uuid.uuid4())
    folder_path = os.path.join(DOWNLOAD_DIR, folder_id)
    os.makedirs(folder_path, exist_ok=True)

    # ---------------- MODE HANDLING ---------------- #

    if mode == "single_audio":
        command = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--write-thumbnail",
            "--convert-thumbnails", "jpg",
            "--embed-thumbnail",
            "--add-metadata",
            "--no-playlist",
            "-o", os.path.join(folder_path, "%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    elif mode == "single_video":
        command = [
            "yt-dlp",
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/mp4",
            "--merge-output-format", "mp4",
            "--no-playlist",
            "-o", os.path.join(folder_path, "%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    elif mode == "playlist_audio":
        command = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--write-thumbnail",
            "--convert-thumbnails", "jpg",
            "--embed-thumbnail",
            "--add-metadata",
            "-o", os.path.join(folder_path, "%(playlist_index)s-%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    elif mode == "playlist_video":
        command = [
            "yt-dlp",
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/mp4",
            "--merge-output-format", "mp4",
            "-o", os.path.join(folder_path, "%(playlist_index)s-%(title)s.%(ext)s"),
            "--restrict-filenames",
            url
        ]

    else:
        return {"error": "invalid mode"}

    # ---------------- RUN ---------------- #

    subprocess.run(command)

    # ---------------- COLLECT FILES ---------------- #

    files = sorted([
        f for f in os.listdir(folder_path)
        if f.endswith(".mp4") or f.endswith(".m4a")
    ])

    thumbnails = sorted([
        f for f in os.listdir(folder_path)
        if f.endswith(".jpg")
    ])

    return {
        "folder": folder_id,
        "files": files,
        "thumbnails": thumbnails
    }


@app.get("/file/{folder}/{filename}")
def get_file(folder: str, filename: str):
    path = os.path.join(DOWNLOAD_DIR, folder, filename)
    return FileResponse(path)