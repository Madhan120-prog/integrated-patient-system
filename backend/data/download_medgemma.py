"""
One-time setup utility: downloads google/medgemma-4b-it from HuggingFace for
local GGUF conversion (see V4_PROGRESS.md — MedGemma vision adapter).

Not part of the running app — same category as resolve_images.py, a script
you run once during environment setup, not on every request.

Requires HUGGINGFACE_TOKEN in backend/.env (gated model — request access at
https://huggingface.co/google/medgemma-4b-it, then create a read-scoped
token at https://huggingface.co/settings/tokens).

Downloads to a sibling directory outside the repo — ~8.64GB of model weights
should never be committed.

Run: python3 data/download_medgemma.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

MODEL_REPO = "google/medgemma-4b-it"
DOWNLOAD_DIR = ROOT_DIR.parent.parent / "model-weights" / "medgemma-4b-it"

if __name__ == "__main__":
    token = os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("HUGGINGFACE_TOKEN not set in backend/.env — see docstring for setup steps.")

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_REPO} to {DOWNLOAD_DIR} ...")
    snapshot_download(
        repo_id=MODEL_REPO,
        local_dir=str(DOWNLOAD_DIR),
        token=token,
    )
    print("Done.")
