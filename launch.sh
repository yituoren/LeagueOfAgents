#!/usr/bin/env bash
set -euo pipefail

# ========== League of Agents 启动脚本 ==========
# 在此填入你的 API Key
export OPENAI_API_KEY="your-api-key"

# 启动游戏
python main.py "${1:-config/default.yaml}"
