# Dubstack
This project implements a pipeline that dub explainers or short stories over gameplay parkours (brainrot style content). It uses lightweight local models and runs 100% offline and is simple enough to extend. It supports voice cloning too. 
[Example output](videos\60b58583-8342-48fa-9e7c-5e74bada278c.mp4)
# Requirements
python 311
ffmpeg
# Install
1. create and activate a venv
pip install requirements
run the download_models.py file


# Use
1. Add the background videos using the add_video.py script: 
python add_videos.py /path/to/videos -tags=nature,beauty -url=https/path/to/a/storage/bucket
This copies the video into video/, generates a 3s preview and updates video/. -tags and -url are optional
the url when specified, refers to a remote bucket where the preview is going to be hosted. this is only relevant when cloud hosting the app or prefer to server the previews from a remote bucket for fast accesses. do not specify url otherwise. 

2. Server the app: 
uvicorn server:app --reload --host 0.0.0.0 --port 7189
view on any browswer:
http:localhost:7189