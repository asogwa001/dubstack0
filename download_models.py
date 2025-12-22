from pathlib import Path
from huggingface_hub import snapshot_download

# REPO_ID = "onnx-community/Kokoro-82M-v1.0-ONNX"

# TARGET_DIR = Path(__file__).parent / "models" / "Kokoro-82M-v1.0-ONNX"
# TARGET_DIR.mkdir(parents=True, exist_ok=True)

# snapshot_download(
#     repo_id=REPO_ID,
#     local_dir=TARGET_DIR,
#     local_dir_use_symlinks=False,
#     allow_patterns=[
#         "voices/**",
#         "onnx/model.onnx",
#         "onnx/model_fp16.onnx",
#         "config.json"
#     ],
# )

REPO_ID = "Supertone/supertonic"

TARGET_DIR = Path(__file__).parent / "models" / "supertonic"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

snapshot_download(
    repo_id=REPO_ID,
    local_dir=TARGET_DIR,
    local_dir_use_symlinks=False,
    # allow_patterns=[
    #     "voices/**",
    #     "onnx/model.onnx",
    #     "onnx/model_fp16.onnx",
    #     "config.json"
    # ],
)

print("download complete")
