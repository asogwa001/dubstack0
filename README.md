# Dubstack

This project implements a pipeline that dubs explainers or short stories over gameplay parkour videos (brainrot-style content). It uses lightweight local models and runs 100% offline, making it simple to extend. Voice cloning is also supported.

[Example output](videos/demo.mp4)

> ⚠️ **Development has been paused in favor of a client-only version of the project:** [DubStack](https://github.com/asogwa001/Dubstack)


## Requirements

- Python 3.11
- FFmpeg

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download required models:
```bash
python download_models.py
```

## Usage

### 1. Add Background Videos

Use the `add_videos.py` script to add background videos to your library:

```bash
python add_videos.py /path/to/videos --tags=nature,beauty --url=https://path/to/storage/bucket
```

This command:
- Copies the video into the `videos/` directory
- Generates a 3-second preview
- Updates the video metadata

**Optional flags:**
- `--tags`: Comma-separated tags for categorizing videos
- `--url`: Remote bucket URL for hosting previews (only use when cloud hosting the app or serving previews from a remote bucket for faster access)

### 2. Start the Server

Launch the application server:

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 7189
```

View the app in any browser at:
```
http://localhost:7189
```
