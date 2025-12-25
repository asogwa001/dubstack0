#!/usr/bin/env python

import argparse
import json
import shutil
import subprocess
import uuid
from pathlib import Path


VIDEOS_DIR = Path("videos")
VIDEOS_JSON = Path("videos/videos.json")

PREVIEW_HEIGHT = 640
PREVIEW_FPS = 20
PREVIEW_DURATION = 3


def ensure_environment():
    VIDEOS_DIR.mkdir(exist_ok=True)

    if not VIDEOS_JSON.exists():
        VIDEOS_JSON.write_text(json.dumps({"videos": []}, indent=2))
        return

    if VIDEOS_JSON.stat().st_size == 0:
        VIDEOS_JSON.write_text(json.dumps({"videos": []}, indent=2))
        return

    try:
        json.loads(VIDEOS_JSON.read_text())
    except json.JSONDecodeError:
        VIDEOS_JSON.write_text(json.dumps({"videos": []}, indent=2))


def get_video_duration(path: Path) -> str:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    seconds = float(result.stdout.strip())

    mins = int(seconds // 60)
    secs = int(seconds % 60)

    return f"{mins:02d}:{secs:02d}"


def generate_preview(input_path: Path, preview_path: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-t", str(PREVIEW_DURATION),
        "-vf", f"scale=-2:{PREVIEW_HEIGHT},fps={PREVIEW_FPS}",
        "-an",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(preview_path)
    ]

    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Add video to gallery")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("-tags", help="Comma-separated tags", default="")
    parser.add_argument("-url", help="Base URL for preview storage", default="")

    args = parser.parse_args()

    input_video = Path(args.video)
    if not input_video.exists():
        raise FileNotFoundError(f"Video not found: {input_video}")

    ensure_environment()

    video_name = input_video.stem
    video_ext = input_video.suffix

    stored_video_name = input_video.name
    preview_name = f"{video_name}_preview.mp4"

    stored_video_path = VIDEOS_DIR / stored_video_name
    preview_path = VIDEOS_DIR / preview_name

    shutil.copy2(input_video, stored_video_path)

    generate_preview(stored_video_path, preview_path)

    duration = get_video_duration(stored_video_path)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.url:
        base = args.url.rstrip("/")
        preview_url = f"{base}/{preview_name}"
    else:
        preview_url = f"videos/{preview_name}"

    entry = {
        "id": str(uuid.uuid4()),
        "name": stored_video_name,
        "url": preview_url,
        "duration": duration,
        "tags": tags
    }

    # if any entry exists with the same name, overwrite it
    data = json.loads(VIDEOS_JSON.read_text())
    videos = data.setdefault("videos", [])
    videos[:] = [v for v in videos if v.get("name") != stored_video_name]
    videos.append(entry)

    VIDEOS_JSON.write_text(json.dumps(data, indent=2))

    print("Video added")
    print(f"   ID: {entry['id']}")
    print(f"   Preview: {preview_path}")
    print(f"   Duration: {duration}")


if __name__ == "__main__":
    main()
