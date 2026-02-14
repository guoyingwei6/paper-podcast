import re
import httpx
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from prompts import SUMMARIZE_ARTICLE_PROMPT, GENERATE_PODCAST_PROMPT

# 使用 OpenAI 兼容 API 格式（支持 SiliconFlow、OpenRouter 等）
API_URL = f"{ANTHROPIC_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
    "Content-Type": "application/json",
}


def _chat(prompt: str, max_tokens: int = 4096) -> str:
    """调用 OpenAI 兼容的 chat completions API。"""
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = httpx.post(API_URL, json=payload, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    # 过滤 DeepSeek-R1 的 <think>...</think> 思考过程
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # 有些蒸馏模型不输出 <think> 标签但会先输出规划文字，
    # 找到第一行 女: 或 男: 开头的内容，去掉之前的非对话内容
    lines = text.split("\n")
    start_idx = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^[\*\s]*(?:女|男|小薇|老张)[：:\s]", stripped):
            start_idx = idx
            break
    if start_idx > 0:
        text = "\n".join(lines[start_idx:])
    return text


def summarize_article(article: dict) -> str:
    """用 AI 总结单篇科研文章。"""
    prompt = SUMMARIZE_ARTICLE_PROMPT.format(
        title=article["title"],
        content=article["content"],
    )
    return _chat(prompt, max_tokens=1024)


def generate_podcast_script(summaries: list[dict]) -> str:
    """根据文章总结生成播客对话脚本。"""
    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        meta = f"标题：{s['title']}"
        if s.get("published"):
            meta += f"\n发表时间：{s['published']}"
        if s.get("journal"):
            meta += f"\n期刊：{s['journal']}"
        summaries_text += f"### 文章 {i}\n{meta}\n\n{s['summary']}\n\n"

    prompt = GENERATE_PODCAST_PROMPT.format(summaries=summaries_text)
    # 20篇文章需要更长的输出
    return _chat(prompt, max_tokens=8192)


def process_articles(articles: list[dict]) -> str:
    """完整 pipeline：逐篇总结 → 生成播客脚本。"""
    summaries = []
    for i, article in enumerate(articles):
        print(f"  [{i+1}/{len(articles)}] AI 总结: {article['title']}")
        summary = summarize_article(article)
        summaries.append({
            "title": article["title"],
            "published": article.get("published", ""),
            "journal": article.get("journal", ""),
            "summary": summary,
        })

    print("生成播客对话脚本...")
    script = generate_podcast_script(summaries)
    return script
