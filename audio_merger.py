import os
import shutil
from pydub import AudioSegment


def merge_audio(audio_files: list[str], output_path: str, silence_ms: int = 300):
    """将多个 MP3 文件拼接为一个，对话间插入静音。"""
    if not audio_files:
        print("没有音频文件可拼接")
        return

    silence = AudioSegment.silent(duration=silence_ms)
    combined = AudioSegment.empty()

    for i, filepath in enumerate(audio_files):
        segment = AudioSegment.from_mp3(filepath)
        if i > 0:
            combined += silence
        combined += segment

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.export(output_path, format="mp3")
    print(f"音频已保存: {output_path}")


def cleanup_temp(temp_dir: str):
    """清理临时音频文件。"""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print("临时文件已清理")
