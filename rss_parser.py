import re
import feedparser
import httpx
from bs4 import BeautifulSoup

SECTION_HEADINGS = {
    "abstract": "Abstract",
    "summary": "Abstract",
    "introduction": "Introduction",
    "background": "Introduction",
    "methods": "Methods",
    "materials and methods": "Methods",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
}

STOP_HEADINGS = {
    "references",
    "acknowledgements",
    "acknowledgments",
    "funding",
    "author information",
    "ethics declarations",
    "supplementary information",
    "additional information",
}

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

    return extract_article_text(resp.text)


def extract_article_text(html: str, max_chars: int = 16000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 移除无关元素
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button"]):
        tag.decompose()

    article_tag = soup.find("article")
    root = article_tag or soup.find("main") or soup.find("body") or soup
    section_text = _extract_section_text(root)
    if section_text:
        return section_text[:max_chars]

    text = root.get_text(separator="\n", strip=True)
    return _clean_lines(text)[:max_chars]


def _extract_section_text(root) -> str:
    chunks = []
    active_heading = ""
    for element in root.find_all(["h1", "h2", "h3", "h4", "p"], recursive=True):
        name = element.name.lower()
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        if name.startswith("h"):
            normalized = _normalize_heading(text)
            if normalized in STOP_HEADINGS:
                active_heading = ""
                break
            active_heading = SECTION_HEADINGS.get(normalized, "")
            if active_heading:
                chunks.append(f"## {active_heading}")
            continue
        if active_heading:
            chunks.append(text)
    return _clean_lines("\n".join(chunks))


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z ]+", "", text.lower()).strip()


def _clean_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


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
