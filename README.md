# Paper Podcast - 科研播客

一个基于 AI 的科研论文播客生成工具，自动从 RSS 订阅源抓取最新论文，通过 AI 生成双人对话播客脚本，并合成为音频，最终发布为可订阅的播客。

在线收听: [网页播放器](https://guoyingwei6.github.io/paper-podcast) | 订阅地址: [RSS](https://guoyingwei6.github.io/paper-podcast/feed.xml)

![paper-podcast](https://socialify.git.ci/guoyingwei6/paper-podcast/image?description=1&forks=1&name=1&owner=1&pattern=Circuit+Board&stargazers=1&theme=Auto)

---

## 主要特性

- 自动从 RSS 源抓取科研论文，支持 Nature、Genome Research、BMC Genomics 等主流期刊
- 使用 AI 智能总结论文核心发现、研究方法和创新点
- 生成双人主持对话脚本（小薇 & 老张），让论文解读更生动有趣
- 通过 Edge TTS 合成高质量中文语音
- 自动生成 iTunes 兼容的 RSS Feed，支持主流播客 App 订阅
- 一键发布到 GitHub Releases，无需额外服务器

## 技术栈

- **Python** - 核心语言
- **OpenAI Chat Completions API** - 论文总结与播客脚本生成（通过兼容接口支持 DeepSeek、Qwen、GPT 等模型）
- **Edge TTS** - 微软语音合成（小晓 + 云扬双声道）
- **FFmpeg** - 音频拼接与处理
- **feedparser** - RSS 解析
- **httpx + BeautifulSoup** - 论文网页内容抓取
- **GitHub Releases** - 音频文件托管
- **GitHub Pages** - RSS Feed 托管

## 工作流程

```
RSS 订阅源 → 抓取论文 → AI 总结 → 生成对话脚本 → TTS 语音合成 → 音频拼接 → 发布
```

1. 从 RSS 源抓取论文元数据（标题、日期、期刊）并爬取全文内容
2. AI 逐篇总结论文要点（300-500 字摘要）
3. AI 生成双人主持对话脚本，逐篇讨论每篇论文
4. Edge TTS 分角色合成语音（女声小晓 + 男声云扬）
5. FFmpeg 拼接所有语音片段，插入 300ms 静音间隔
6. （可选）上传到 GitHub Releases 并更新 RSS Feed

## 快速开始

### 第一步：Fork 仓库

点击右上角 Fork，将本仓库复制到自己的 GitHub 账号下。

### 第二步：配置 Secrets

进入你 Fork 后的仓库 → **Settings → Secrets and variables → Actions → New repository secret**，添加以下四个 Secret：

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `ANTHROPIC_API_KEY` | 大模型服务的 API 密钥 | `sk-...` |
| `ANTHROPIC_BASE_URL` | 兼容 OpenAI 格式的接口地址 | `https://api.siliconflow.cn/v1` |
| `ANTHROPIC_MODEL` | 使用的模型名称 | `deepseek-ai/DeepSeek-R1` |
| `RSS_URL` | 你的论文 RSS 订阅地址 | `https://example.com/feed.xml` |

> 大模型服务需支持 OpenAI Chat Completions API（`/chat/completions` 端点），推荐使用 [SiliconFlow](https://siliconflow.cn)（提供 DeepSeek、Qwen 等模型，有免费额度）。
>
> RSS 订阅源推荐配合 [ZotWatch](https://github.com/guoyingwei6/ZotWatch) 使用，可自动将 Zotero 文献库生成 RSS Feed。

### 第三步：启用 GitHub Actions 和 Pages

1. 进入仓库 → **Actions** → 启用 Workflows
2. 进入 **Settings → Pages**，Source 选择 `Deploy from a branch`，Branch 选 `main`，目录选 `/ (root)`

### 第四步：手动触发

配置完成后，进入 **Actions → Daily Podcast → Run workflow** 手动触发第一次生成。

之后每周一北京时间 7:00 会自动运行。

## 项目结构

```
paper-podcast/
├── main.py              # 主程序入口，串联完整流水线
├── config.py            # 配置管理（环境变量）
├── rss_parser.py        # RSS 解析与论文内容抓取
├── ai_generator.py      # AI 论文总结与对话脚本生成
├── prompts.py           # AI 提示词（总结 & 对话生成）
├── tts_engine.py        # Edge TTS 语音合成
├── audio_merger.py      # FFmpeg 音频拼接
├── feed_generator.py    # iTunes 兼容 RSS Feed 生成
├── feed.xml             # 生成的播客 RSS Feed
├── cover.jpg            # 播客封面
├── requirements.txt     # Python 依赖
└── .github/workflows/   # GitHub Actions 自动化流程
```

## 致谢

本项目受 [Hacker Podcast](https://github.com/miantiao-me/hacker-podcast) 启发，感谢以下开源项目和服务：

- **[Edge TTS](https://github.com/rany2/edge-tts)** - 免费高质量的微软语音合成
- **[feedparser](https://github.com/kurtmckee/feedparser)** - RSS 解析库
- **[SiliconFlow](https://siliconflow.cn)** - 开源大模型 API 服务

## 贡献

欢迎提交 Issue 和 Pull Request!

## 免责声明

本项目生成的播客内容由 AI 自动生成，可能存在理解偏差，不代表原论文作者观点。请以原始论文为准。
