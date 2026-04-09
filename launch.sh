#!/usr/bin/env bash
set -euo pipefail

# API key for backup
export OPENAI_API_KEY="AIzaSyCGy_LFjtEe5iJXmdJV9_hh-nlnGGRDWZ8"

# Launch the game
python main.py "${1:-config/default.yaml}"
