import re
from concurrent.futures import ThreadPoolExecutor

import httpx
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from paper_analysis import PaperAnalysis, parse_paper_analysis_json
from prompts import ANALYZE_ARTICLE_PROMPT, GENERATE_PODCAST_BATCH_PROMPT

# 使用 OpenAI 兼容 API 格式（支持 SiliconFlow、OpenRouter 等）
API_URL = f"{ANTHROPIC_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
    "Content-Type": "application/json",
}

# 逐篇 AI 分析的并发数
ANALYSIS_CONCURRENCY = 5


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


def analyze_article(article: dict) -> PaperAnalysis:
    prompt = ANALYZE_ARTICLE_PROMPT.format(
        title=article["title"],
        content=article["content"],
    )
    return parse_paper_analysis_json(_chat_raw(prompt, max_tokens=2048))


def summarize_article(article: dict) -> str:
    return analyze_article(article).to_summary()



def _strip_highlights_thinking(text: str) -> str:
    """过滤模型在亮点简介前输出的规划/思考段落（含孤立 </think> 标签）。
    策略：模型的实际简介始终是最后一段，直接取最后一段。
    """
    text = re.sub(r"</think>", "", text).strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        return paragraphs[-1]
    return text


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
        analysis = s["analysis"]
        text += f"### 文章 {i}\n{meta}\n\n{analysis.to_prompt_text()}\n\n"
    return text


def validate_script_coverage(script: str, expected_count) -> None:
    """校验脚本是否覆盖了每篇文章。

    summaries 传入 summaries 列表时，用文章标题关键词判断是否被讨论到（对口语脚本鲁棒，
    不依赖模型逐字写"文章 N"）；传入 int 时退回旧的"文章 N"字面标记检测（供既有测试使用）。
    missing（整篇未被提及）视为致命，保证不漏文章；weak（深度线索不足）仅警告，不阻断发布。
    """
    if isinstance(expected_count, int):
        _validate_by_markers(script, expected_count)
        return

    summaries = expected_count
    missing = []
    weak = []
    for i, summary in enumerate(summaries, 1):
        if not _script_covers_article(script, summary):
            missing.append(str(i))
        elif not _contains_depth_cues(script):
            weak.append(str(i))

    if weak:
        print(f"  [警告] 以下文章深度线索不足（不阻断发布）: {', '.join(weak)}")
    if missing:
        raise ValueError(
            "script coverage validation failed: missing articles: " + ", ".join(missing)
        )


def _validate_by_markers(script: str, expected_count: int) -> None:
    """旧版基于"文章 N"字面标记的覆盖校验（保留以兼容既有测试）。"""
    missing = []
    weak = []
    for article_number in range(1, expected_count + 1):
        segment = _script_segment_for_article(script, article_number, expected_count)
        if not segment:
            missing.append(str(article_number))
            continue
        if not _contains_depth_cues(segment):
            weak.append(str(article_number))

    if weak:
        print(f"  [警告] 以下文章深度线索不足（不阻断发布）: {', '.join(weak)}")
    if missing:
        raise ValueError(
            "script coverage validation failed: missing articles: " + ", ".join(missing)
        )


_EN_STOPWORDS = {
    "using", "these", "their", "based", "which", "with", "from", "into",
    "analysis", "analyses", "study", "studies", "reveals", "reveal", "across",
    "large", "scale", "identifies", "associated", "enables", "approach",
}


def _zh_ngrams(title_zh: str, n: int = 3) -> set[str]:
    """把中文标题的连续中文字符切成 n-gram 集合，用于口语脚本覆盖检测。"""
    ngrams: set[str] = set()
    for frag in re.findall(r"[\u4e00-\u9fff]+", title_zh):
        if len(frag) < n:
            if len(frag) >= 2:
                ngrams.add(frag)
            continue
        for i in range(len(frag) - n + 1):
            ngrams.add(frag[i:i + n])
    return ngrams


def _en_keywords(title_en: str) -> list[str]:
    """英文标题里的实义长词（去停用词）。"""
    words = []
    for word in re.findall(r"[A-Za-z]{5,}", title_en):
        if word.lower() not in _EN_STOPWORDS:
            words.append(word)
    return words


def _script_covers_article(script: str, summary: dict) -> bool:
    """脚本是否覆盖到该文章：命中>=2个中文标题 n-gram，或>=2个英文关键词。"""
    zh_ngrams = _zh_ngrams(summary.get("title_zh", "") or "")
    if zh_ngrams:
        zh_hits = sum(1 for g in zh_ngrams if g in script)
        if zh_hits >= 2:
            return True

    en_keywords = _en_keywords(summary.get("title", "") or "")
    if en_keywords:
        script_lower = script.lower()
        en_hits = sum(1 for k in en_keywords if k.lower() in script_lower)
        if en_hits >= 2:
            return True

    # 完全没有可用标题信息时保守视为已覆盖，避免误杀
    if not zh_ngrams and not en_keywords:
        return True

    return False


def _script_segment_for_article(script: str, article_number: int, expected_count: int) -> str:
    pattern = re.compile(rf"文章\s*{article_number}(?!\d)")
    match = pattern.search(script)
    if not match:
        return ""
    if article_number >= expected_count:
        return script[match.start():]
    next_match = re.search(rf"文章\s*{article_number + 1}(?!\d)", script[match.end():])
    if not next_match:
        return script[match.start():]
    return script[match.start(): match.end() + next_match.start()]


def _contains_depth_cues(segment: str) -> bool:
    cue_groups = (
        ("研究问题", "问题", "想回答", "关注"),
        ("方法", "数据", "样本", "使用", "分析"),
        ("结果", "发现", "显示", "提升", "降低", "揭示"),
        ("局限", "限制", "谨慎", "不能", "未明确说明"),
    )
    return all(any(cue in segment for cue in group) for group in cue_groups)


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

        batch_end = batch_start + len(batch)
        # 明确告知模型本批文章的全局编号范围，避免跨批独立调用时从"文章 1"重新编号
        if len(batch) == 1:
            number_note = f"本批只包含【文章 {batch_end}】（全期共 {total} 篇），必须使用编号 {batch_end}，不要从 1 重新编号。"
        else:
            number_note = (
                f"本批包含【文章 {batch_start + 1} 到 文章 {batch_end}】（全期共 {total} 篇），"
                f"必须严格使用这些全局编号，不要从 1 重新编号。"
            )
        role = f"{role} {number_note}"

        summaries_text = _build_summaries_text(batch, batch_start)
        prompt = GENERATE_PODCAST_BATCH_PROMPT.format(
            role=role,
            summaries=summaries_text,
        )
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
        "请将以下论文标题逐条翻译为中文，保持编号格式，每行一条，只输出翻译结果，不要解释。"
        "要求：按英文字面意思直译，不要根据记忆联想已知的中文论文标题来替换。\n\n"
        + numbered
    )
    result = _chat_raw(prompt, max_tokens=2048)

    # 从第一个 "1." 开头的行开始解析，跳过可能的思考/前言段落
    list_match = re.search(r"(?m)^1[.、]", result)
    if list_match:
        result = result[list_match.start():]

    translations = {}
    for line in result.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)[.、\s]+(.+)$", line)
        if m:
            idx = int(m.group(1)) - 1
            translation = m.group(2).strip()
            # 只取每个编号的第一次出现，防止模型在结尾"总结"时覆盖正确翻译
            if 0 <= idx < len(titles) and translation and titles[idx] not in translations:
                translations[titles[idx]] = translation
    return translations


def generate_episode_highlights(articles: list[dict]) -> str:
    """根据文章摘要生成本期节目亮点简介（2-3句，吸引听众）。"""
    overview = ""
    for a in articles:
        title = a.get("title_zh") or a.get("title", "")
        journal = a.get("journal", "")
        summary = a.get("summary_zh", "")
        if not title:
            continue
        line = f"- {title}"
        if journal:
            line += f"（{journal}）"
        if summary:
            line += f"：{summary[:120]}"
        overview += line + "\n"

    prompt = (
        "请根据以下科研文章列表，用2-3句话概括本期播客涵盖的主要研究方向和核心内容。"
        "语气平实，简洁客观，像播客节目的一句话介绍。"
        "不要夸张渲染，不要用「颠覆」「黑科技」等词，直接陈述研究主题即可。"
        "只输出最终段落文字，不要任何思考过程、列表或格式符号。\n\n"
        f"文章列表：\n{overview}"
    )
    return _strip_highlights_thinking(_chat_raw(prompt, max_tokens=512))


def process_articles(articles: list[dict]) -> str:
    """完整 pipeline：翻译标题 → 逐篇总结 → 生成播客脚本。"""
    # 批量翻译标题
    print("翻译文章标题...")
    title_map = translate_titles(articles)
    for article in articles:
        article["title_zh"] = title_map.get(article.get("title", ""), "")

    total = len(articles)

    def _analyze(index_article):
        index, article = index_article
        print(f"  [{index+1}/{total}] AI 总结: {article['title']}")
        try:
            return index, analyze_article(article)
        except Exception as e:
            # 单篇解析失败（模型漏字段、抓取内容不足等）不应拖垮整期，跳过该篇
            print(f"  [警告] 第 {index+1} 篇分析失败，已跳过: {e}")
            return index, None

    max_workers = max(1, min(ANALYSIS_CONCURRENCY, total))
    analyses: dict[int, PaperAnalysis | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, analysis in executor.map(_analyze, enumerate(articles)):
            analyses[index] = analysis

    summaries = []
    kept_articles = []
    for i, article in enumerate(articles):
        analysis = analyses[i]
        if analysis is None:
            continue
        article["summary_zh"] = analysis.to_summary()  # 存回 article 供亮点生成使用
        kept_articles.append(article)
        summaries.append({
            "title": article["title"],
            "title_zh": article.get("title_zh", ""),
            "published": article.get("published", ""),
            "journal": article.get("journal", ""),
            "analysis": analysis,
        })

    if not summaries:
        raise ValueError("所有文章分析均失败，无法生成播客脚本")

    skipped = total - len(summaries)
    if skipped:
        print(f"共 {total} 篇，{skipped} 篇分析失败已跳过，实际使用 {len(summaries)} 篇。")

    # 用实际保留的文章覆盖原列表，供后续亮点简介 / RSS 描述使用
    articles[:] = kept_articles

    print("生成播客对话脚本...")
    script = generate_podcast_script(summaries)
    validate_script_coverage(script, summaries)
    return script
