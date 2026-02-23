import re
import feedparser
import httpx
from bs4 import BeautifulSoup

# DOI 域名 → 期刊名映射
JOURNAL_MAP = {
    "nature.com": {
        "s41588": "Nature Genetics",
        "s41586": "Nature",
        "s41467": "Nature Communications",
    },
    "genome.org": "Genome Research",
    "mdpi.com": "Animals",
    "biomedcentral.com": "BMC Genomics",
}


def _extract_journal(entry: dict) -> str:
    """从 RSS 条目中提取期刊名。"""
    # 优先从 summary 的 Venue 字段提取
    summary = entry.get("summary", "")
    venue_match = re.search(r"Venue:\s*(.+)", summary)
    if venue_match:
        return venue_match.group(1).strip()

    # 从 DOI 链接推断
    link = entry.get("link", "")
    for domain, journals in JOURNAL_MAP.items():
        if domain in link:
            if isinstance(journals, dict):
                for code, name in journals.items():
                    if code in link:
                        return name
                return "Nature"  # fallback for nature.com
            return journals

    # 从 tags 提取
    tags = entry.get("tags", [])
    for tag in tags:
        term = tag.get("term", "")
        if term and term not in ("", "article"):
            return term

    return ""


def _format_date(entry: dict) -> str:
    """格式化发布日期为 YYYY-MM-DD。"""
    parsed = entry.get("published_parsed")
    if parsed:
        return f"{parsed.tm_year}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
    return entry.get("published", "")


def _extract_authors(entry: dict) -> str:
    """从 RSS 条目中提取作者信息。"""
    # 尝试从 authors 列表获取
    authors_list = entry.get("authors", [])
    if authors_list:
        author_names = [a.get("name", "") for a in authors_list if a.get("name")]
        if author_names:
            # 如果作者超过3个，只显示前3个加 et al.
            if len(author_names) > 3:
                return ", ".join(author_names[:3]) + " et al."
            return ", ".join(author_names)

    # 尝试从 author 字段获取
    author = entry.get("author", "")
    if author:
        return author

    return ""


def parse_feed(rss_url: str, count: int) -> list[dict]:
    """解析 RSS feed，返回文章列表。"""
    feed = feedparser.parse(rss_url)
    entries = feed.entries if count <= 0 else feed.entries[:count]
    articles = []
    for entry in entries:
        article = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": _format_date(entry),
            "journal": _extract_journal(entry),
            "authors": _extract_authors(entry),
            "summary": entry.get("summary", ""),
            "content": "",
        }
        articles.append(article)
    return articles


def fetch_article_content(url: str) -> str:
    """抓取文章正文内容。"""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [警告] 无法抓取文章: {e}")
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # 移除无关元素
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # 优先提取 <article> 标签
    article_tag = soup.find("article")
    if article_tag:
        text = article_tag.get_text(separator="\n", strip=True)
    else:
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    # 截断过长文本（约 8000 字）
    return text[:8000]


def get_articles(rss_url: str, count: int) -> list[dict]:
    """获取文章列表并抓取正文。count<=0 表示全部。"""
    articles = parse_feed(rss_url, count)
    print(f"从 RSS 获取到 {len(articles)} 篇文章")

    for i, article in enumerate(articles):
        print(f"  [{i+1}/{len(articles)}] 抓取: {article['title']}")
        content = fetch_article_content(article["link"])
        if content:
            article["content"] = content
        elif article["summary"]:
            article["content"] = article["summary"]

    return articles
