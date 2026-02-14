import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

# RSS
RSS_URL = os.getenv("RSS_URL", "")
ARTICLE_COUNT = int(os.getenv("ARTICLE_COUNT", "5"))

# TTS
AUDIO_SPEED = os.getenv("AUDIO_SPEED", "+10%")
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural"
VOICE_MALE = "zh-CN-YunyangNeural"

# 输出目录
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
