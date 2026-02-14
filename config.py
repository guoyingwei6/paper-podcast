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

# 播客元数据
PODCAST_TITLE = "Paper Podcast - 科研播客"
PODCAST_DESCRIPTION = "AI 生成的科研论文解读播客，由两位动物基因组学博士主持"
PODCAST_AUTHOR = "Paper Podcast"
GITHUB_REPO = "guoyingwei6/paper-podcast"
