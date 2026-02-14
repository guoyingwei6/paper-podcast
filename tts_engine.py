import asyncio
import os
import edge_tts
from config import VOICE_FEMALE, VOICE_MALE, AUDIO_SPEED


def parse_script(script: str) -> list[dict]:
    """解析播客脚本，返回对话片段列表。"""
    lines = []
    for line in script.strip().splitlines():
        line = line.strip()
        if line.startswith("女:") or line.startswith("女："):
            text = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
            lines.append({"gender": "female", "text": text})
        elif line.startswith("男:") or line.startswith("男："):
            text = line.split(":", 1)[1].strip() if ":" in line else line.split("：", 1)[1].strip()
            lines.append({"gender": "male", "text": text})
    return lines


async def synthesize_line(text: str, voice: str, rate: str, output_path: str):
    """用 Edge TTS 合成单段语音。"""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


async def synthesize_all(script: str, temp_dir: str) -> list[str]:
    """将播客脚本转为语音文件列表。"""
    os.makedirs(temp_dir, exist_ok=True)
    lines = parse_script(script)
    audio_files = []

    for i, line in enumerate(lines):
        voice = VOICE_FEMALE if line["gender"] == "female" else VOICE_MALE
        output_path = os.path.join(temp_dir, f"line_{i:04d}.mp3")
        print(f"  [{i+1}/{len(lines)}] TTS: {line['text'][:30]}...")
        await synthesize_line(line["text"], voice, AUDIO_SPEED, output_path)
        audio_files.append(output_path)

    return audio_files


def run_tts(script: str, temp_dir: str) -> list[str]:
    """同步入口，调用异步 TTS。"""
    return asyncio.run(synthesize_all(script, temp_dir))
