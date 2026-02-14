import anthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from prompts import SUMMARIZE_ARTICLE_PROMPT, GENERATE_PODCAST_PROMPT


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
    )


def summarize_article(article: dict) -> str:
    """用 AI 总结单篇科研文章。"""
    client = _get_client()
    prompt = SUMMARIZE_ARTICLE_PROMPT.format(
        title=article["title"],
        content=article["content"],
    )

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_podcast_script(summaries: list[dict]) -> str:
    """根据文章总结生成播客对话脚本。"""
    client = _get_client()

    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"### 文章 {i}：{s['title']}\n{s['summary']}\n\n"

    prompt = GENERATE_PODCAST_PROMPT.format(summaries=summaries_text)

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def process_articles(articles: list[dict]) -> str:
    """完整 pipeline：逐篇总结 → 生成播客脚本。"""
    summaries = []
    for i, article in enumerate(articles):
        print(f"  [{i+1}/{len(articles)}] AI 总结: {article['title']}")
        summary = summarize_article(article)
        summaries.append({"title": article["title"], "summary": summary})

    print("生成播客对话脚本...")
    script = generate_podcast_script(summaries)
    return script
