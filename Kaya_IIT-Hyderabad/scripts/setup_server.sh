#!/usr/bin/env bash
# Sets up the Kaya Python environment (Python 3.11, CUDA 12.1 wheels; driver supports CUDA 12.2).
set -euo pipefail
ROOT="${KAYA_ROOT:-$HOME/kaya}"
cd "$ROOT"
[ -d .venv ] || python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import torch; print('cuda', torch.cuda.is_available(), torch.cuda.device_count())"
