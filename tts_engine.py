import asyncio
import os
import re
import edge_tts
from config import VOICE_FEMALE, VOICE_MALE, AUDIO_SPEED

# TTS 并发合成数
TTS_CONCURRENCY = 6

# 匹配各种格式：女: / 女：/ **女:** / **小薇**: / 小薇: 等
FEMALE_PATTERN = re.compile(r"^[\*\s]*(?:女|小薇)[：:\s]*[\*]*\s*")
MALE_PATTERN = re.compile(r"^[\*\s]*(?:男|老张)[：:\s]*[\*]*\s*")


def parse_script(script: str) -> list[dict]:
    """解析播客脚本，返回对话片段列表。"""
    lines = []
    for line in script.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if FEMALE_PATTERN.match(line):
            text = FEMALE_PATTERN.sub("", line).strip()
            if text:
                lines.append({"gender": "female", "text": text})
        elif MALE_PATTERN.match(line):
            text = MALE_PATTERN.sub("", line).strip()
            if text:
                lines.append({"gender": "male", "text": text})
    return lines


async def synthesize_line(text: str, voice: str, rate: str, output_path: str, max_retries: int = 3):
    """用 Edge TTS 合成单段语音，带重试逻辑。"""
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(output_path)
            return
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  TTS 失败 (尝试 {attempt+1}/{max_retries}): {e}, {wait}s 后重试...")
                await asyncio.sleep(wait)
            else:
                raise


async def synthesize_all(script: str, temp_dir: str) -> list[str]:
    """将播客脚本转为语音文件列表（并发合成，保持顺序）。"""
    os.makedirs(temp_dir, exist_ok=True)
    lines = parse_script(script)
    total = len(lines)
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    async def worker(i: int, line: dict) -> str:
        voice = VOICE_FEMALE if line["gender"] == "female" else VOICE_MALE
        output_path = os.path.join(temp_dir, f"line_{i:04d}.mp3")
        async with semaphore:
            print(f"  [{i+1}/{total}] TTS: {line['text'][:30]}...")
            await synthesize_line(line["text"], voice, AUDIO_SPEED, output_path)
        return output_path

    return await asyncio.gather(*(worker(i, line) for i, line in enumerate(lines)))


def run_tts(script: str, temp_dir: str) -> list[str]:
    """同步入口，调用异步 TTS。"""
    return asyncio.run(synthesize_all(script, temp_dir))
