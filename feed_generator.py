"""RSS feed generator for Paper Podcast (iTunes/Apple Podcasts compatible)."""

import os
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import formatdate

from config import PODCAST_TITLE, PODCAST_DESCRIPTION, PODCAST_AUTHOR, GITHUB_REPO

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
FEED_PATH = os.path.join(os.path.dirname(__file__), "feed.xml")
SITE_URL = "https://guoyingwei6.github.io/paper-podcast"


def _release_url(filename):
    tag = filename.replace("podcast-", "v").replace(".mp3", "")
    return f"https://github.com/{GITHUB_REPO}/releases/download/{tag}/{filename}"


def _get_mp3_duration(filepath):
    """Get MP3 duration using pydub."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(filepath)
        duration_sec = len(audio) // 1000
        mins, secs = divmod(duration_sec, 60)
        return f"{mins}:{secs:02d}"
    except Exception:
        return "0:00"


def _get_episode_description(articles, highlights=""):
    """Generate episode description from article list (bilingual)."""
    if not articles:
        return "科研论文解读播客"
    lines = []
    for a in articles:
        title = a.get("title", "")
        title_zh = a.get("title_zh", "")
        journal = a.get("journal", "")
        published = a.get("published", "")

        if not title:
            continue

        # 构建元信息行（期刊、日期）
        meta_parts = []
        if journal:
            meta_parts.append(journal)
        if published:
            meta_parts.append(published)

        meta_line = ", ".join(meta_parts) if meta_parts else ""

        # 组装格式：元信息 + 英文标题 + 中文翻译
        article_lines = []
        if meta_line:
            article_lines.append(meta_line)
        article_lines.append(title)
        if title_zh:
            article_lines.append(title_zh)

        # 添加到总列表，每篇文章之间空一行
        lines.append("\n".join(article_lines))

    if lines:
        article_list = "本期讨论文章：\n\n" + "\n\n".join(lines)
        if highlights:
            return f"{highlights}\n\n{article_list}"
        return article_list
    return "科研论文解读播客"


def _create_channel():
    """Create a new RSS channel element."""
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = PODCAST_TITLE
    ET.SubElement(channel, "description").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, "language").text = "zh-cn"
    ET.SubElement(channel, "link").text = SITE_URL

    ET.SubElement(channel, f"{{{ITUNES_NS}}}author").text = PODCAST_AUTHOR
    ET.SubElement(channel, f"{{{ITUNES_NS}}}summary").text = PODCAST_DESCRIPTION
    ET.SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"
    cat = ET.SubElement(channel, f"{{{ITUNES_NS}}}category")
    cat.set("text", "Science")
    ET.SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": f"{SITE_URL}/cover.jpg"})

    return rss, channel


def _add_item(channel, episode_date, mp3_path, articles, highlights=""):
    """Add an episode item to the channel."""
    filename = os.path.basename(mp3_path)
    file_size = str(os.path.getsize(mp3_path))
    audio_url = _release_url(filename)
    duration = _get_mp3_duration(mp3_path)
    description = _get_episode_description(articles, highlights)
    guid = f"podcast-{episode_date}"

    # Parse date for pubDate
    dt = datetime.strptime(episode_date, "%Y-%m-%d")
    pub_date = formatdate(dt.timestamp(), usegmt=True)

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"科研播客 - {episode_date}"
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "enclosure", {
        "url": audio_url,
        "length": file_size,
        "type": "audio/mpeg",
    })
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = duration
    ET.SubElement(item, f"{{{ITUNES_NS}}}author").text = PODCAST_AUTHOR
    ET.SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "false"


def update_feed(episode_date, mp3_path, articles, highlights=""):
    """Update or create the RSS feed with a new episode.

    Args:
        episode_date: Date string in YYYY-MM-DD format.
        mp3_path: Path to the MP3 file.
        articles: List of article dicts with 'title' key.
        highlights: Optional episode highlights text to prepend to description.
    """
    ET.register_namespace("itunes", ITUNES_NS)
    ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")

    if os.path.exists(FEED_PATH):
        tree = ET.parse(FEED_PATH)
        rss = tree.getroot()
        channel = rss.find("channel")
        # Check if episode already exists
        guid_text = f"podcast-{episode_date}"
        for item in channel.findall("item"):
            guid = item.find("guid")
            if guid is not None and guid.text == guid_text:
                print(f"Episode {episode_date} already exists in feed, skipping")
                return
    else:
        rss, channel = _create_channel()

    _add_item(channel, episode_date, mp3_path, articles, highlights)

    # Write with XML declaration
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(FEED_PATH, encoding="unicode", xml_declaration=True)

    print(f"Feed updated: {FEED_PATH}")
    return FEED_PATH
