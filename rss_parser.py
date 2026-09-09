import asyncio
import html
import re

import feedparser
import httpx
from bs4 import BeautifulSoup

from article_sources import (
    MAX_CONTENT_CHARS,
    SECTION_HEADINGS,
    STOP_HEADINGS,
    clean_lines,
    extract_doi,
    fetch_open_article_content,
    normalize_heading,
)

FETCH_CONCURRENCY = 8

# 许多出版商（MDPI、OUP、bioRxiv 等）会对默认 httpx UA 返回 403，
# 使用浏览器 UA 头可显著提升正文抓取成功率。
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
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
        venue = re.split(
            r"(?:<br\s*/?>|</p>|\n|\s+Authors?:)",
            venue_match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return _strip_markup(venue)

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


def _strip_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _format_date(entry: dict) -> str:
    """格式化发布日期为 YYYY-MM-DD。"""
    parsed = entry.get("published_parsed")
    if parsed:
        return f"{parsed.tm_year}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
    return entry.get("published", "")


_TITLE_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
# 标签移除后留下的占位符，用来区分"原文空格"和"XML 换行缩进带来的空格"
_TAG_MARK = "\x00"


def clean_title(title: str) -> str:
    """清理 RSS 标题：去掉 <i>/<sub>/<scp> 等标签，并把换行缩进压成单行。

    部分出版商（Science、Wiley、Genome Research 等）的 RSS 标题带排版标签，
    且被 XML 缩进换行切断，直接写入 feed 会在播客客户端和网页上显示成字面
    标签文本。标签两侧的换行是排版产物而非真实空格，因此下标、基因编号和
    括号需要在移除标签后重新贴合，避免出现 "CO 2"、"RASAL 2"、"( DIS3L2 )"。
    """
    if not title:
        return ""
    text = _TITLE_TAG_RE.sub(_TAG_MARK, html.unescape(title))
    text = re.sub(r"\s+", " ", text).strip()

    m = re.escape(_TAG_MARK)
    text = re.sub(r"(?<=[A-Za-z]) (?=" + m + r"\d)", "", text)            # CO <sub>2</sub>
    text = re.sub(r"(?<=[A-Za-z0-9])" + m + r" (?=\d)", _TAG_MARK, text)  # <scp>RASAL</scp> 2
    text = re.sub(r"(?<=[(\[]) (?=" + m + r")", "", text)                 # ( <i>X</i>
    text = re.sub(r"(?<=" + m + r") (?=[)\]},.;:%])", "", text)           # <i>X</i> )

    text = text.replace(_TAG_MARK, "")
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(rss_url: str, count: int) -> list[dict]:
    """解析 RSS feed，返回文章列表。"""
    feed = feedparser.parse(rss_url)
    entries = feed.entries if count <= 0 else feed.entries[:count]
    articles = []
    for entry in entries:
        article = {
            "title": clean_title(entry.get("title", "")),
            "link": entry.get("link", ""),
            "published": _format_date(entry),
            "journal": _extract_journal(entry),
            "summary": entry.get("summary", ""),
            "doi": extract_doi(entry.get("link", ""), entry.get("summary", "")),
            "content": "",
        }
        articles.append(article)
    return articles


async def _fetch_article_content(client: httpx.AsyncClient, article: dict) -> str:
    url = article["link"]
    try:
        resp = await client.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [警告] 无法抓取文章: {e}")
    else:
        content = extract_article_text(resp.text)
        if content:
            return content

    doi = extract_doi(article.get("link", ""), article.get("summary", ""))
    if not doi:
        return ""

    content, source = await fetch_open_article_content(client, doi)
    if content:
        print(f"  [信息] {source} 兜底成功: {doi}")
        return content

    return ""


def extract_article_text(html_text: str, max_chars: int = MAX_CONTENT_CHARS) -> str:
    soup = BeautifulSoup(html_text, "lxml")
    # 移除无关元素
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button"]):
        tag.decompose()

    article_tag = soup.find("article")
    root = article_tag or soup.find("main") or soup.find("body") or soup
    section_text = _extract_section_text(root)
    if section_text:
        return section_text[:max_chars]

    text = root.get_text(separator="\n", strip=True)
    return clean_lines(text)[:max_chars]


def _extract_section_text(root) -> str:
    chunks = []
    active_heading = ""
    for element in root.find_all(["h1", "h2", "h3", "h4", "p"], recursive=True):
        name = element.name.lower()
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        if name.startswith("h"):
            normalized = normalize_heading(text)
            if normalized in STOP_HEADINGS:
                active_heading = ""
                continue
            active_heading = SECTION_HEADINGS.get(normalized, "")
            if active_heading:
                chunks.append(f"## {active_heading}")
            continue
        if active_heading:
            chunks.append(text)
    return clean_lines("\n".join(chunks))


async def _fetch_all_content(articles: list[dict]) -> None:
    """并发抓取所有文章正文，回填 content 字段。"""
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)
    total = len(articles)

    async with httpx.AsyncClient(headers=BROWSER_HEADERS) as client:
        async def worker(index: int, article: dict) -> None:
            async with semaphore:
                print(f"  [{index + 1}/{total}] 抓取: {article['title']}")
                content = await _fetch_article_content(client, article)
            if content:
                article["content"] = content
            elif article["summary"]:
                article["content"] = article["summary"]

        await asyncio.gather(*(worker(i, a) for i, a in enumerate(articles)))


def get_articles(rss_url: str, count: int) -> list[dict]:
    """获取文章列表并抓取正文。count<=0 表示全部。"""
    articles = parse_feed(rss_url, count)
    print(f"从 RSS 获取到 {len(articles)} 篇文章")

    if articles:
        asyncio.run(_fetch_all_content(articles))

    return articles
