# personal-site

个人站：博客 + 分主题笔记 + 首页数据面板。Hugo 构建，GitHub Pages 托管。

站点是双语的：中文在根路径，英文在 `/en/`。

## 本地跑

```bash
hugo server -D          # http://localhost:1313，改文件秒级刷新
```

## 抓数据

首页的 Star 数、项目卡片来自 GitHub API：

```bash
python3 scripts/fetch_data.py           # 生成 data/github.json 和 data/projects.json
```

Actions 里每天自动跑一次，不用手工维护。

## 改内容

| 想改什么 | 改哪里 |
|:---|:---|
| 站点标题、菜单、tagline | `hugo.toml` |
| 首页名片里的链接 | `data/profile.json` |
| 关于页 | `content/about.md`（英文 `content/en/about.md`） |
| 博客文章 | `content/posts/`（英文 `content/en/posts/`） |
| 读书笔记 | `content/reading/`（英文 `content/en/reading/`） |
| 技术笔记 | `content/notebook/`（英文 `content/en/notebook/`） |
| 界面文案（导航、空状态） | `i18n/zh.toml` + `i18n/en.toml` |
| 配色 / 排版 | `assets/css/main.css` |

**双语约定**：一篇内容要出现在两种语言里，两边的**相对路径和 `slug` 必须一致**（`content/posts/foo.md` ↔ `content/en/posts/foo.md`），否则语言切换器认不出译文的对应关系，只能跳回对方首页。新增界面文案时两个 `i18n/*.toml` 都要加 key。

## 结构

```
content/             中文内容（根路径）
content/en/          英文内容（/en/ 前缀）
content/posts/       博客，按日期倒序
content/reading/     读书笔记，按书名排序
content/notebook/    技术笔记
content/projects/    项目卡片（数据来自 data/projects.json）
i18n/                界面文案
layouts/index.html   首页：名片 + 数字面板 + 最近文章
layouts/_default/    列表页、文章页、项目页
data/                JSON 数据，模板里用 site.Data.xxx 读
scripts/             抓数据脚本
```

## 部署

推到 GitHub → Actions 自动构建 → GitHub Pages。

首次启用：仓库 Settings → Pages → Source 选 **GitHub Actions**。
