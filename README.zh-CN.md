<div align="center">

# 🔍 website-seo-audit（网站SEO诊断）

### 对任意网站一键做全站 SEO 体检 —— 几秒出报告，零配置。

[English](README.md) · **简体中文**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![零依赖](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#-凭什么不一样)
[![Agent Skill](https://img.shields.io/badge/agent-skill-8A2BE2.svg)](SKILL.md)
[![欢迎 PR](https://img.shields.io/badge/PRs-welcome-orange.svg)](#-参与贡献)

</div>

一个**零依赖**的 SEO 诊断工具，既能当**命令行工具**用，也能装进你的 **AI 编程 agent**
（Claude Code、Codex、opencode……）当技能用。它会爬取一个网站，检查数十项
**页面级**、**技术级**、**结构化数据** 信号，输出一份带评分的报告，每个问题都附上
具体怎么修。

不用 API key，不用注册，不用 `pip install`。只要 Python 3.8+ 和标准库。

```bash
python3 -m seo_audit https://example.com
```

---

## ✨ 效果一览

```
# 🔍 SEO Audit — https://example.com
Score: 72/100 (C)  ·  🔴 2 critical · 🟡 8 warnings · 🟢 15 notices
Crawled 23 pages · 45 internal links checked

## 🔴 Critical (2)
### Broken internal links (3×)   —— 内链 404
### Site not on HTTPS            —— 站点未启用 HTTPS

## 🟡 Warnings (8)
### Missing meta description (6×)      —— 缺 meta description
### Duplicate titles                   —— 标题重复
### Structured data missing fields     —— Article 缺 image / datePublished
...
```

👉 完整样例：[`examples/sample-report.md`](examples/sample-report.md)

---

## 🚀 快速开始

```bash
git clone https://github.com/zxhydfzr/website-seo-audit.git
cd website-seo-audit
python3 -m seo_audit https://yoursite.com
```

就这样。不用建虚拟环境、不用装任何包。

想要一个全局命令？用 [pipx](https://pipx.pypa.io/) 安装：

```bash
pipx install git+https://github.com/zxhydfzr/website-seo-audit.git
seo-audit https://yoursite.com
```

---

## 🤖 装进你的 AI agent 用

仓库自带 [`SKILL.md`](SKILL.md)，任何支持开放
[Agent Skills](https://code.claude.com/docs/en/skills) 格式的 agent 都能识别。
之后你只要说一句：**「帮我诊断 https://example.com 的 SEO」**，agent 就会自己跑工具、
把结果讲给你听。

| Agent | 安装方式 |
|---|---|
| **Claude Code** | `git clone https://github.com/zxhydfzr/website-seo-audit ~/.claude/skills/website-seo-audit` |
| **Codex** | clone 到你的项目里，自带的 [`AGENTS.md`](AGENTS.md) 会告诉它怎么跑 |
| **opencode / 其它** | clone 到 agent 能读到的目录，指给它 `SKILL.md` |

---

## 🔬 它检查什么

<table>
<tr><td valign="top" width="33%">

**页面级**
- `<title>`：有无 / 长度 / 重复
- meta description：有无 / 长度
- `<h1>` 与标题层级
- canonical 规范链接
- 移动端 viewport
- `<html lang>`
- 图片 `alt`
- 薄内容（支持中文计数）
- Open Graph 社媒标签
- HTTPS 混合内容

</td><td valign="top" width="33%">

**技术级**
- HTTPS
- `robots.txt`
- `sitemap.xml`
- 内链死链（4xx/5xx）
- 重复 title / meta
- 近孤儿页
- 重定向处理

</td><td valign="top" width="33%">

**结构化数据** ⭐
- JSON-LD 语法是否有效
- 是否带 `@type`
- Schema.org 必填字段
  （Article、Product、
  Organization、
  BreadcrumbList、FAQ、
  Recipe、Event……）
- 日期是否 ISO-8601

</td></tr>
</table>

---

## ⭐ 凭什么不一样

- **懂结构化数据。** 大多数快速 SEO 检查器查到标题、标题层级就停了。这个会校验你的
  **JSON-LD / Schema.org** 标记 —— 这正是搜索引擎和 **AI 问答引擎** 用来理解、并
  **引用**你页面的关键信号。
- **零依赖。** 只用 Python 标准库，Python 能跑的地方它就能跑 —— 笔记本、CI、容器、
  受限服务器都行。
- **为 agent 而生。** 以可移植技能的形式发布，你的 AI 助手能自己跑完整诊断、再用对话
  一步步带你修。
- **礼貌又安全。** 遵守 `robots.txt`、带真实 User-Agent、自我限速，只爬你指定的站点。

---

## ⚙️ 参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `-1`, `--single` | 关 | 只诊断给定 URL（不爬取） |
| `--max-pages N` | 50 | 最多爬取页数 |
| `--max-depth N` | 3 | 最大爬取深度 |
| `--json` | 关 | 输出机器可读的 JSON |
| `-o, --output FILE` | — | 报告写入文件 |
| `--ignore-robots` | 关 | 忽略 robots.txt 强行爬（仅用于自己的站） |
| `--no-link-check` | 关 | 跳过死链检测（更快） |
| `-q, --quiet` | 关 | 不显示爬取进度 |

发现任何**严重（critical）**问题时命令以非零码退出，方便接入 CI：

```bash
seo-audit https://yoursite.com --json -o seo.json || echo "SEO 出问题了！"
```

## 📊 评分规则

从 100 分开始扣，每档有封顶，避免大站被一堆小提示拖垮：
🔴 每个 −15 · 🟡 每个 −3 · 🟢 每个 −1。
等级：**A** ≥90 · **B** ≥80 · **C** ≥70 · **D** ≥55 · **F** 更低。

## 🗺️ 路线图

- [ ] 页面速度 / Core Web Vitals 信号
- [ ] hreflang 与多语言检查
- [ ] HTML 报告导出
- [ ] 可选的 sitemap 播种爬取（诊断 sitemap 里的每个 URL）

欢迎提想法和 PR。

## 🤝 参与贡献

非常欢迎提 issue 和 PR。代码库刻意做得小、带类型、零依赖，请保持这个风格。跑测试：

```bash
python -m unittest discover -s tests
```

## 🙌 致谢

检查项设计参考了开源审计工具
[python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer) 和
[seonaut](https://github.com/StJudeWasHere/seonaut)，以及 Google 富结果文档。
本项目在此之上补齐了一流的结构化数据校验，以及零依赖、可被 agent 安装的打包方式。

## 📄 许可协议

[MIT](LICENSE) —— 个人和商用都免费。

---

<div align="center">

**如果它帮你省了时间，点个 ⭐ 能让更多人发现它。**

献给所有不想登录一堆后台、只想要干净 SEO 的人。

</div>
