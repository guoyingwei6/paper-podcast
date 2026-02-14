import feedparser
import httpx
from bs4 import BeautifulSoup


def parse_feed(rss_url: str, count: int) -> list[dict]:
    """解析 RSS feed，返回文章列表。"""
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:count]:
        article = {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
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
        # 回退到 body
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    # 截断过长文本（约 8000 字）
    return text[:8000]


def get_articles(rss_url: str, count: int) -> list[dict]:
    """获取文章列表并抓取正文。"""
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
