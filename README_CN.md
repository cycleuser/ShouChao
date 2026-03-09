# ShouChao (守巢) - 全球新闻情报平台

从全球100+主流新闻媒体（覆盖10种语言）聚合新闻，将文章转化为结构化的Markdown文档，索引到ChromaDB知识库中，并提供AI驱动的新闻简报和投资、移民、留学场景分析。

## 功能特性

- **10语言覆盖**: 中文、英文、日文、法文、俄文、德文、意大利文、西班牙文、葡萄牙文、韩文
- **100+新闻源**: 新华网、BBC、NHK、Le Monde、ТАСС、DW、ANSA、El Pais、Folha、연합뉴스等
- **多种抓取后端**: requests、curl_cffi、DrissionPage、Playwright，模拟人类浏览行为
- **RSS + 网页抓取**: RSS订阅高效发现新闻，网页抓取获取完整文章
- **Markdown存储**: 文章保存为 `{语言}/{网站名}/{年月日}/{标题}.md` 格式，包含YAML头信息
- **ChromaDB知识库**: 兼容GangDan的向量数据库，支持语义搜索
- **AI分析**: 通过Ollama提供投资、移民、留学和综合新闻分析
- **新闻简报**: 每日、每周和领域专题简报，LLM自动摘要
- **三种界面**: CLI命令行、GUI图形界面(tkinter)和Web仪表板(Flask)
- **国际化**: 完整的10语言界面支持

## 系统要求

- Python >= 3.10
- [Ollama](https://ollama.ai)（AI功能需要：分析、简报、语义搜索）

## 安装

```bash
pip install shouchao
```

或从源码安装：

```bash
git clone https://github.com/cycleuser/ShouChao.git
cd ShouChao
pip install -e .
```

### 可选依赖

```bash
pip install shouchao[all]         # 所有可选抓取器 + readability
pip install shouchao[curl]        # curl_cffi 更好的反爬虫
pip install shouchao[browser]     # DrissionPage（系统Chrome）
pip install shouchao[readability]  # 更好的内容提取
```

## 快速开始

```bash
# 列出可用新闻源
shouchao sources --language zh

# 抓取新闻
shouchao fetch --language zh --max 10

# 搜索已索引的新闻
shouchao search "人工智能监管"

# 生成每日简报（需要Ollama）
shouchao briefing --type daily --language zh

# 分析新闻对投资的影响（需要Ollama）
shouchao analyze "欧盟政策变化" --scenario investment

# 启动Web仪表板
shouchao web --port 5001

# 启动GUI
shouchao gui
```

## 使用方法

### CLI 命令

| 命令 | 说明 |
|------|------|
| `shouchao fetch` | 从新闻源抓取新闻 |
| `shouchao search "查询"` | 搜索已索引的新闻 |
| `shouchao briefing` | 生成新闻简报 |
| `shouchao analyze "查询"` | 场景化新闻分析 |
| `shouchao index` | 将文章索引到ChromaDB |
| `shouchao sources` | 列出/管理新闻源 |
| `shouchao config` | 查看/更新配置 |
| `shouchao web` | 启动Flask Web服务器 |
| `shouchao gui` | 启动tkinter GUI |

### 全局参数

| 参数 | 说明 |
|------|------|
| `-V, --version` | 显示版本号 |
| `-v, --verbose` | 详细输出 |
| `--json` | JSON格式输出 |
| `-q, --quiet` | 静默模式 |
| `--data-dir 路径` | 自定义数据目录 |

### 分析场景

```bash
shouchao analyze "新欧盟AI法案的影响" --scenario investment     # 投资分析
shouchao analyze "加拿大移民政策2026" --scenario immigration      # 移民分析
shouchao analyze "英国大学学费变化" --scenario study_abroad        # 留学分析
shouchao analyze "全球半导体趋势" --scenario general              # 综合分析
```

## Python API

```python
from shouchao import fetch_news, search_news, analyze_news, list_sources

# 列出新闻源
result = list_sources(language="zh")
print(result.data["count"])

# 抓取新闻
result = fetch_news(language="zh", max_articles=10)
print(result.data["fetched"])

# 搜索
result = search_news(query="气候变化", top_k=5)
for r in result.data["results"]:
    print(r["metadata"]["title"])

# 分析
result = analyze_news(query="市场趋势", scenario="investment")
print(result.data["content"])
```

## Agent 集成 (OpenAI Function Calling)

ShouChao 提供兼容 OpenAI 的工具定义：

```python
from shouchao.tools import TOOLS, dispatch

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,
)

result = dispatch(
    tool_call.function.name,
    tool_call.function.arguments,
)
```

## CLI 帮助

![CLI Help](images/shouchao_help.png)

## 开发

```bash
git clone https://github.com/cycleuser/ShouChao.git
cd ShouChao
pip install -e ".[dev]"
python -m pytest tests/test_unified_api.py -v
```

## 许可证

GPL-3.0-or-later
