import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

from config import RSS_URL, ARTICLE_COUNT, OUTPUT_DIR, GITHUB_REPO
from rss_parser import get_articles
from ai_generator import process_articles
from tts_engine import run_tts
from audio_merger import merge_audio, cleanup_temp
from feed_generator import update_feed


def publish(today, output_path, articles):
    """Upload MP3 to GitHub Releases, update feed.xml, commit and push."""
    tag = f"v{today}"
    title = f"科研播客 {today}"
    filename = os.path.basename(output_path)

    # Upload to GitHub Releases
    print(f"\n📦 上传音频到 GitHub Releases ({tag})")
    result = subprocess.run(
        ["gh", "release", "create", tag, output_path,
         "--title", title, "--notes", f"科研播客 {today} 期"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if "already exists" in result.stderr:
            print(f"Release {tag} 已存在，跳过上传")
        else:
            print(f"Release 创建失败: {result.stderr}")
            return False
    else:
        print(f"Release 创建成功: https://github.com/{GITHUB_REPO}/releases/tag/{tag}")

    # Update RSS feed
    print("\n📝 更新 RSS feed")
    update_feed(today, output_path, articles)

    # Commit and push feed.xml
    print("\n📤 提交并推送 feed.xml")
    project_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(["git", "add", "feed.xml"], cwd=project_dir)
    subprocess.run(
        ["git", "commit", "-m", f"Update feed.xml for {today}"],
        cwd=project_dir, capture_output=True,
    )
    subprocess.run(["git", "push"], cwd=project_dir)
    print("推送完成")
    return True


def main():
    parser = argparse.ArgumentParser(description="Paper Podcast - RSS 科研播客生成工具")
    parser.add_argument("--rss", type=str, default=RSS_URL, help="RSS 订阅地址")
    parser.add_argument("--count", type=int, default=ARTICLE_COUNT, help="处理文章数量（0=全部）")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR, help="输出目录")
    parser.add_argument("--publish", action="store_true", help="上传到 GitHub Releases 并更新 RSS feed")
    args = parser.parse_args()

    if not args.rss:
        print("错误: 请通过 --rss 参数或 .env 中的 RSS_URL 指定 RSS 地址")
        sys.exit(1)

    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    output_path = os.path.join(args.output, f"podcast-{today}.mp3")
    script_path = os.path.join(args.output, f"script-{today}.txt")
    temp_dir = os.path.join(args.output, "temp_audio")

    # Step 1: 获取文章
    print(f"\n📡 获取 RSS 文章 ({args.rss})")
    articles = get_articles(args.rss, args.count)
    if not articles:
        print("未获取到文章，退出")
        sys.exit(1)

    # Step 2: AI 生成播客脚本
    print("\n🤖 AI 生成播客脚本")
    script = process_articles(articles)
    print(f"\n--- 播客脚本预览 ---\n{script[:500]}...\n")

    # 保存脚本到文件
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

    # Step 6: 发布（可选）
    if args.publish:
        publish(today, output_path, articles)


if __name__ == "__main__":
    main()
