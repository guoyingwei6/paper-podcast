import os
import shutil
import subprocess

try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_BIN = "ffmpeg"


def merge_audio(audio_files: list[str], output_path: str, silence_ms: int = 300):
    """将多个 MP3 文件拼接为一个，对话间插入静音（使用 ffmpeg concat）。"""
    if not audio_files:
        print("没有音频文件可拼接")
        return

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 生成静音文件
    silence_path = os.path.join(os.path.dirname(audio_files[0]), "silence.mp3")
    subprocess.run(
        [FFMPEG_BIN, "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=24000:cl=mono", "-t", str(silence_ms / 1000),
         "-c:a", "libmp3lame", "-q:a", "5", silence_path],
        capture_output=True,
    )

    # 创建 concat 文件列表
    filelist_path = os.path.join(os.path.dirname(audio_files[0]), "filelist.txt")
    with open(filelist_path, "w") as f:
        for i, filepath in enumerate(audio_files):
            if i > 0:
                f.write(f"file '{os.path.abspath(silence_path)}'\n")
            f.write(f"file '{os.path.abspath(filepath)}'\n")

    # 用 ffmpeg concat 拼接
    result = subprocess.run(
        [FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0",
         "-i", filelist_path, "-c:a", "libmp3lame", "-q:a", "5", output_path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ffmpeg 错误: {result.stderr}")
        return

    print(f"音频已保存: {output_path}")


def cleanup_temp(temp_dir: str):
    """清理临时音频文件。"""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print("临时文件已清理")
