import argparse
import os
from datetime import date

from config import RSS_URL, ARTICLE_COUNT, OUTPUT_DIR
from rss_parser import get_articles
from ai_generator import process_articles
from tts_engine import run_tts
from audio_merger import merge_audio, cleanup_temp


def main():
    parser = argparse.ArgumentParser(description="Paper Podcast - RSS 科研播客生成工具")
    parser.add_argument("--rss", type=str, default=RSS_URL, help="RSS 订阅地址")
    parser.add_argument("--count", type=int, default=ARTICLE_COUNT, help="处理文章数量（0=全部）")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR, help="输出目录")
    args = parser.parse_args()

    if not args.rss:
        print("错误: 请通过 --rss 参数或 .env 中的 RSS_URL 指定 RSS 地址")
        return

    today = date.today().isoformat()
    output_path = os.path.join(args.output, f"podcast-{today}.mp3")
    temp_dir = os.path.join(args.output, "temp_audio")

    # Step 1: 获取文章
    print(f"\n📡 获取 RSS 文章 ({args.rss})")
    articles = get_articles(args.rss, args.count)
    if not articles:
        print("未获取到文章，退出")
        return

    # Step 2: AI 生成播客脚本
    print("\n🤖 AI 生成播客脚本")
    script = process_articles(articles)
    print(f"\n--- 播客脚本预览 ---\n{script[:500]}...\n")

    # 保存脚本到文件
    script_path = os.path.join(args.output, f"script-{today}.txt")
    os.makedirs(args.output, exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"脚本已保存: {script_path}")

    # Step 3: TTS 语音合成
    print("\n🔊 TTS 语音合成")
    audio_files = run_tts(script, temp_dir)

    # Step 4: 音频拼接
    print("\n🎵 音频拼接")
    merge_audio(audio_files, output_path)

    # Step 5: 清理
    cleanup_temp(temp_dir)

    print(f"\n✅ 完成! 播客文件: {output_path}")


if __name__ == "__main__":
    main()
