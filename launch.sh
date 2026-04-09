#!/usr/bin/env bash
set -euo pipefail

# ========== League of Agents ==========
# API keys are loaded from .env file (see .env.example)

python main.py "${1:-config/default.yaml}"
