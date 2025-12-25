import os
import json
import uuid
from pathlib import Path
from typing import Optional, Protocol
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

import soundfile as sf
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from supertonic_helper import (
    load_text_to_speech,
    load_voice_style,
    Style,
    TextToSpeech,
)
from ffmpeg_dub import dub_video


class TTSResult(BaseModel):
    wav_path: str
    srt_path: str
    duration: float


class TTSModel(ABC):
    @abstractmethod
    def get_available_voices(self) -> list[str]:
        pass

    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        pass

    @abstractmethod
    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        voice_sample: Optional[Path] = None,
        speed: float = 1.05,
        silence_duration: float = 0.3,
        end_silence_duration: float = 0.5,
    ) -> TTSResult:
        pass


class SupertonicModel(TTSModel):
    VOICE_MAP = {
        "Liam": "M1",
        "Ethan": "M2",
        "Noah": "M3",
        "Lucas": "M4",
        "Oliver": "M5",
        "Ava": "F1",
        "Sophia": "F2",
        "Isabella": "F3",
        "Mia": "F4",
        "Luna": "F5",
    }

    def __init__(self, onnx_dir: str, output_dir: str):
        self.tts = load_text_to_speech(onnx_dir, use_gpu=False)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_styles = self._load_all_voices()

    def _load_all_voices(self) -> dict[str, Style]:
        styles = {}
        for name, file_prefix in self.VOICE_MAP.items():
            path = f"models/supertonic/voice_styles/{file_prefix}.json"
            styles[name] = load_voice_style([path])
        return styles

    def get_available_voices(self) -> list[str]:
        return list(self.VOICE_MAP.keys())

    def supports_voice_cloning(self) -> bool:
        return False

    def generate(
        self,
        text: str,
        voice: Optional[str] = None,
        voice_sample: Optional[Path] = None,
        speed: float = 1.05,
        silence_duration: float = 0.3,
        end_silence_duration: float = 0.5,
    ) -> TTSResult:
        if voice not in self.voice_styles:
            raise ValueError(f"Voice {voice} not found")

        style = self.voice_styles[voice]
        wav, duration, timestamps = self.tts(
            text, style, total_step=5, speed=speed,
            silence_duration=silence_duration,
            end_silence_duration=end_silence_duration,
        )

        job_id = str(uuid.uuid4())
        wav_path = self.output_dir / f"{job_id}.wav"
        srt_path = self.output_dir / f"{job_id}.srt"

        sf.write(str(wav_path), wav[0], self.tts.sample_rate)
        self._write_srt(srt_path, timestamps)

        return TTSResult(
            wav_path=str(wav_path),
            srt_path=str(srt_path),
            duration=float(duration),
        )

    @staticmethod
    def _write_srt(path: Path, timestamps: list[dict]):
        def format_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60
            return f"{h:02}:{m:02}:{s:06.3f}".replace(".", ",")

        lines = []
        for i, t in enumerate(timestamps, start=1):
            lines.append(str(i))
            lines.append(f"{format_time(t['start'])} --> {format_time(t['end'])}")
            lines.append(t["text"])
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class ModelRegistry:
    def __init__(self):
        self.models: dict[str, TTSModel] = {}

    def register(self, name: str, model: TTSModel):
        self.models[name] = model

    def get(self, name: str) -> TTSModel:
        if name not in self.models:
            raise ValueError(f"Model {name} not found")
        return self.models[name]

    def list_models(self) -> list[dict]:
        models_data = []
        with open("models.json", "r") as f:
            config = json.load(f)

        for model_config in config["models"]:
            name = model_config["name"]
            models_data.append({
                "name": name,
                "available_voices": model_config["available_voices"],
                "running": name in self.models,
                "voice_cloning": model_config["voice_cloning"],
            })
        return models_data


registry = ModelRegistry()
SAMPLES_DIR = Path("videos")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.register(
        "supertonic-66m",
        SupertonicModel("models/supertonic/onnx", str(OUTPUT_DIR))
    )
    yield


app = FastAPI(lifespan=lifespan)


class TTSRequest(BaseModel):
    text: str
    speed: float = 1.05
    silence_duration: float = 0.3
    end_silence_duration: float = 0.5
    voice: Optional[str] = None


class SubtitleConfig(BaseModel):
    font_size: int = 16
    outline: int = 2
    shadow: int = 1
    alignment: int = 2
    marginv: int = 80


class AudioConfig(BaseModel):
    background_audio_volume: float = 0.0


class VideoConfig(BaseModel):
    id: str


class GenerateRequest(BaseModel):
    tts: TTSRequest
    subtitle: Optional[SubtitleConfig] = None
    audio: Optional[AudioConfig] = None
    video: VideoConfig


class VideoSample(BaseModel):
    id: str
    name: str
    url: str
    duration: str
    tags: list[str]


class VideoSamplesResponse(BaseModel):
    page: int
    page_size: int
    total_videos: int
    total_pages: int
    videos: list[VideoSample]


@app.get("/tts/models/")
def list_tts_models():
    return {"models": registry.list_models()}


@app.get("/samples/videos")
def list_video_samples(
    page: int = 1,
    page_size: int = 10,
    tags: Optional[str] = None,
):
    samples_file = SAMPLES_DIR / "videos.json"
    if not samples_file.exists():
        raise HTTPException(status_code=404, detail="Samples not found")

    with open(samples_file, "r") as f:
        all_videos = json.load(f)["videos"]

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        all_videos = [
            v for v in all_videos
            if any(tag in v["tags"] for tag in tag_list)
        ]

    total_videos = len(all_videos)
    total_pages = (total_videos + page_size - 1) // page_size

    start = (page - 1) * page_size
    end = start + page_size
    videos = all_videos[start:end]

    return VideoSamplesResponse(
        page=page,
        page_size=page_size,
        total_videos=total_videos,
        total_pages=total_pages,
        videos=[VideoSample(**v) for v in videos],
    )


@app.post("/generate/{model_name}")
async def generate_video(model_name: str, request: GenerateRequest):
    try:
        model = registry.get(model_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found or not running")

    samples_file = SAMPLES_DIR / "videos.json"
    with open(samples_file, "r") as f:
        all_videos = json.load(f)["videos"]

    video_data = next((v for v in all_videos if v["id"] == request.video.id), None)
    if not video_data:
        raise HTTPException(status_code=404, detail=f"Video {request.video.id} not found")

    video_path = SAMPLES_DIR / video_data["name"]
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample file not found")

    tts_result = model.generate(
        text=request.tts.text,
        voice=request.tts.voice,
        speed=request.tts.speed,
        silence_duration=request.tts.silence_duration,
        end_silence_duration=request.tts.end_silence_duration,
    )

    subtitle_config = request.subtitle or SubtitleConfig()
    audio_config = request.audio or AudioConfig()

    output_path = OUTPUT_DIR / f"{uuid.uuid4()}.mp4"

    dub_video(
        video_path=str(video_path),
        voice_path=tts_result.wav_path,
        srt_path=tts_result.srt_path,
        output_path=str(output_path),
        video_audio_volume=audio_config.background_audio_volume,
        font_size=subtitle_config.font_size,
        outline=subtitle_config.outline,
        shadow=subtitle_config.shadow,
        margin_v=subtitle_config.marginv,
    )

    return {"video": f"/outputs/{output_path.name}"}


@app.get("/outputs/{filename}")
def get_output_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/")
async def serve_index():
    return FileResponse("index.html")
