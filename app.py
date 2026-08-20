import os
import uuid
import threading
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort

from processor import process_video

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/bilingual-translator/uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/bilingual-translator/outputs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "500"))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

jobs = {}
lock = threading.Lock()


@app.get("/")
def index():
    return render_template("index.html", max_upload_mb=MAX_UPLOAD_MB)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/upload")
def upload():
    video = request.files.get("video")
    if not video or not video.filename:
        return jsonify({"error": "请选择视频文件"}), 400

    allowed = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    suffix = Path(video.filename).suffix.lower()
    if suffix not in allowed:
        return jsonify({"error": "支持 MP4 / MOV / MKV / WEBM / AVI / M4V"}), 400

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}{suffix}"
    video.save(input_path)

    with lock:
        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "任务已加入队列",
            "download_url": None,
            "error": None,
        }

    thread = threading.Thread(
        target=run_job,
        args=(job_id, input_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


def run_job(job_id, input_path):
    def update(progress, message):
        with lock:
            if job_id in jobs:
                jobs[job_id]["status"] = "processing"
                jobs[job_id]["progress"] = progress
                jobs[job_id]["message"] = message

    try:
        output_path = process_video(
            input_path=input_path,
            output_dir=OUTPUT_DIR,
            progress=update,
        )
        with lock:
            jobs[job_id].update({
                "status": "done",
                "progress": 100,
                "message": "处理完成",
                "download_url": f"/download/{job_id}",
            })
    except Exception as exc:
        traceback.print_exc()
        with lock:
            jobs[job_id].update({
                "status": "error",
                "message": "处理失败",
                "error": str(exc),
            })
    finally:
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/api/status/<job_id>")
def status(job_id):
    with lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(job)


@app.get("/download/<job_id>")
def download(job_id):
    output_path = OUTPUT_DIR / f"{job_id}.mp4"
    if not output_path.exists():
        abort(404)
    return send_file(
        output_path,
        as_attachment=True,
        download_name=f"bilingual_{job_id}.mp4",
        mimetype="video/mp4",
    )


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": f"视频太大，最大 {MAX_UPLOAD_MB} MB"}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
