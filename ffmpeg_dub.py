import subprocess
import json
from pathlib import Path


def get_duration(file_path):
    """Get duration of media file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def dub_video(
    video_path,
    voice_path,
    srt_path,
    output_path,
    video_audio_volume=0.0,
    font_name="Inter",
    font_size=16,
    outline=2,
    shadow=1,
    margin_v=80,
):
    video_path = Path(video_path)
    voice_path = Path(voice_path)
    srt_path = Path(srt_path)
    output_path = Path(output_path)

    for p in (video_path, voice_path, srt_path):
        if not p.exists():
            raise FileNotFoundError(p)

    # Get durations
    video_duration = get_duration(video_path)
    audio_duration = get_duration(voice_path)

    # Calculate loop count
    loop_count = int(audio_duration / video_duration) if audio_duration > video_duration else 0

    print(f"Video duration: {video_duration:.2f}s")
    print(f"Audio duration: {audio_duration:.2f}s")
    print(f"Loop count: {loop_count}")

    subtitle_style = (
        f"FontName={font_name}\\,"
        f"FontSize={font_size}\\,"
        f"Outline={outline}\\,"
        f"Shadow={shadow}\\,"
        f"Alignment=2\\,"
        f"MarginV={margin_v}"
    )

    # Check if video has audio
    # it is possible the video does not have an audio
    cmd_probe = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "json", str(video_path)]
    result = subprocess.run(cmd_probe, capture_output=True, text=True)
    video_has_audio = bool(json.loads(result.stdout).get("streams"))

    # Build audio filter
    if video_has_audio and video_audio_volume > 0:
        audio_filter = (
            f"[0:a]atrim=0:{audio_duration},volume={video_audio_volume}[va];"
            f"[1:a]volume=1.0[ta];"
            f"[va][ta]amix=inputs=2:dropout_transition=0,atrim=0:{audio_duration}[outa]"
        )
        map_audio = ["-map", "[outa]"]
    else:
        audio_filter = f"[1:a]atrim=0:{audio_duration},volume=1.0[outa]"
        map_audio = ["-map", "[outa]"]

    cmd = ["ffmpeg", "-y"]
    
    if loop_count > 0:
        cmd.extend(["-stream_loop", str(loop_count)])
    
    cmd.extend([
        "-i", str(video_path),
        "-i", str(voice_path),
        "-vf", f"subtitles='{srt_path.as_posix()}':force_style={subtitle_style}",
        "-filter_complex", audio_filter,
        "-map", "0:v:0",
    ] + map_audio + [
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path)
    ])

    subprocess.run(cmd, check=True)
