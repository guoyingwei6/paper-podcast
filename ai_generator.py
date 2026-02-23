import re
import httpx
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from prompts import SUMMARIZE_ARTICLE_PROMPT, GENERATE_PODCAST_BATCH_PROMPT

# 使用 OpenAI 兼容 API 格式（支持 SiliconFlow、OpenRouter 等）
API_URL = f"{ANTHROPIC_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
    "Content-Type": "application/json",
}


def _chat_raw(prompt: str, max_tokens: int = 4096) -> str:
    """调用 OpenAI 兼容的 chat completions API（仅过滤 think 标签）。"""
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
    return text


def _chat(prompt: str, max_tokens: int = 4096) -> str:
    """调用 API 并过滤非对话内容（用于生成播客脚本）。"""
    text = _chat_raw(prompt, max_tokens)
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
    return _chat_raw(prompt, max_tokens=1024)


_FAREWELL_RE = re.compile(
    r"(再见|下期|下次见|感谢收听|本期播客|就到这里|拜拜|今天就聊到|以上就是今天|好了今天|好，今天)"
)


def _strip_farewell(text: str) -> str:
    """删除非末尾批次里尾部出现的道别/结束语行。"""
    lines = text.split("\n")
    while lines:
        last = lines[-1].strip()
        if last and _FAREWELL_RE.search(last):
            lines.pop()
        else:
            break
    return "\n".join(lines)


def _build_summaries_text(summaries: list[dict], start_idx: int) -> str:
    """将 summaries 列表转换为提示词文本。"""
    text = ""
    for i, s in enumerate(summaries, start_idx + 1):
        title_zh = s.get("title_zh", "")
        if title_zh:
            meta = f"中文标题：{title_zh}\n英文标题：{s['title']}"
        else:
            meta = f"标题：{s['title']}"
        if s.get("published"):
            meta += f"\n发表时间：{s['published']}"
        if s.get("journal"):
            meta += f"\n期刊：{s['journal']}"
        text += f"### 文章 {i}\n{meta}\n\n{s['summary']}\n\n"
    return text


def generate_podcast_script(summaries: list[dict]) -> str:
    """分批生成播客对话脚本，每批 5 篇，确保所有文章都被覆盖。"""
    BATCH_SIZE = 5
    total = len(summaries)
    script_parts = []

    for batch_start in range(0, total, BATCH_SIZE):
        batch = summaries[batch_start:batch_start + BATCH_SIZE]
        is_first = batch_start == 0
        is_last = batch_start + len(batch) >= total

        if is_first and is_last:
            role = "这是本期播客的全部内容，需要有完整的开场白和结尾道别。"
        elif is_first:
            role = "这是本期播客的开始部分，需要有完整的开场白。结尾不要道别，因为后面还有更多文章。"
        elif is_last:
            role = "这是本期播客的最后部分，直接从文章讨论开始（不要重复开场白）。最后加一句简短的道别。"
        else:
            role = "这是本期播客的中间部分，直接从文章讨论开始（不要重复开场白）。结尾不要道别，后面还有更多文章。"

        summaries_text = _build_summaries_text(batch, batch_start)
        prompt = GENERATE_PODCAST_BATCH_PROMPT.format(
            role=role,
            summaries=summaries_text,
        )
        batch_end = batch_start + len(batch)
        print(f"  生成脚本片段（第 {batch_start + 1}-{batch_end}/{total} 篇）...")
        part = _chat(prompt, max_tokens=4096)
        if not is_last:
            part = _strip_farewell(part)
        script_parts.append(part)

    return "\n".join(script_parts)


def translate_titles(articles: list[dict]) -> dict[str, str]:
    """批量翻译文章标题为中文，返回 {英文标题: 中文标题} 字典。"""
    titles = [a.get("title", "") for a in articles if a.get("title")]
    if not titles:
        return {}
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = (
        "请将以下论文标题逐条翻译为中文，保持编号格式，每行一条，"
        "只输出翻译结果，不要解释：\n\n" + numbered
    )
    result = _chat_raw(prompt, max_tokens=2048)
    translations = {}
    for line in result.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 解析编号前缀，如 "1. " 或 "1、"，按编号映射而不是按顺序计数
        # 这样即使 AI 多输出了额外文字，翻译也不会错位
        m = re.match(r"^(\d+)[.、\s]+(.+)$", line)
        if m:
            idx = int(m.group(1)) - 1
            translation = m.group(2).strip()
            if 0 <= idx < len(titles) and translation:
                translations[titles[idx]] = translation
    return translations


def process_articles(articles: list[dict]) -> str:
    """完整 pipeline：翻译标题 → 逐篇总结 → 生成播客脚本。"""
    # 批量翻译标题
    print("翻译文章标题...")
    title_map = translate_titles(articles)
    for article in articles:
        article["title_zh"] = title_map.get(article.get("title", ""), "")

    summaries = []
    for i, article in enumerate(articles):
        print(f"  [{i+1}/{len(articles)}] AI 总结: {article['title']}")
        summary = summarize_article(article)
        summaries.append({
            "title": article["title"],
            "title_zh": article.get("title_zh", ""),
            "published": article.get("published", ""),
            "journal": article.get("journal", ""),
            "summary": summary,
        })

    print("生成播客对话脚本...")
    script = generate_podcast_script(summaries)
    return script
