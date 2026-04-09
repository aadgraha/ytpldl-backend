from fastapi import FastAPI
from fastapi.responses import FileResponse
import subprocess
import os
import uuid

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/download")
def download(url: str):
    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    command = [
        "yt-dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/mp4",
        "--merge-output-format", "mp4",
        "-o", filepath,
        "--no-playlist",
        "--restrict-filenames",
        url
    ]

    subprocess.run(command)

    return {"file": filename}


@app.get("/file/{filename}")
def get_file(filename: str):
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    return FileResponse(filepath, media_type="video/mp4")