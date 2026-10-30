# personal-site

个人站：博客 + 分主题笔记 + 首页数据面板。Hugo 构建，GitHub Pages 托管。

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
| 关于页 | `content/about.md` |
| 博客文章 | `content/posts/` |
| 读书笔记 | `content/reading/` |
| 技术笔记 | `content/notebook/` |
| 配色 / 排版 | `assets/css/main.css` |

## 结构

```
content/posts/       博客，按日期倒序
content/reading/     读书笔记，按书名排序
content/notebook/    技术笔记
content/projects/    项目卡片（数据来自 data/projects.json）
layouts/index.html   首页：名片 + 数字面板 + 最近文章
layouts/_default/    列表页、文章页、项目页
data/                JSON 数据，模板里用 site.Data.xxx 读
scripts/             抓数据脚本
```

## 部署

推到 GitHub → Actions 自动构建 → GitHub Pages。

首次启用：仓库 Settings → Pages → Source 选 **GitHub Actions**。
