# personal-site

个人站：博客 + 读书笔记 + 技术笔记 + 观影 + 动态时间线 + 项目卡片。

**Hugo + [PaperMod](https://github.com/adityatelange/hugo-PaperMod) 主题**构建，GitHub Pages 托管；站内数据（GitHub 仓库信息、豆瓣观影、各平台动态）全部由脚本抓取，没有手填的数字。

站点是双语的：中文在根路径，英文在 `/en/`。

## 本地跑

```bash
hugo server -D          # http://localhost:1313，改文件秒级刷新
hugo --gc --minify      # 生产构建到 public/
```

Hugo 需要 extended 版（主题用到 SCSS 处理）。

## 数据脚本

`data/` 下的三份 JSON 由脚本生成、**随仓库提交**（没有数据时站点用旧数据照常构建）：

```bash
python3 scripts/fetch_data.py      # GitHub 仓库 → data/github.json + data/projects.json
python3 scripts/fetch_douban.py    # 豆瓣「看过」→ data/douban.json（需要豆瓣 cookie）
python3 scripts/fetch_activity.py  # 各平台动态 → data/activity.json（需要本机 RSSHub）
python3 scripts/fetch_orcid.py     # ORCID 公开记录 → data/publications.json
python3 scripts/fetch_douyin.py    # 抖音主页作品 → data/douyin.json（Playwright + cookie）
python3 scripts/make_covers.py     # 生成文章/项目封面 PNG → static/images/covers/
```

- **豆瓣**：cookie 走环境变量 `DOUBAN_COOKIE` 或 `~/douban_cookie.txt`（不进仓库）
- **动态**：读本机自建的 RSSHub（`127.0.0.1:1200`），源包括豆瓣广播、GitHub、B站；**本站仓库的 push 被排除**，否则「同步脚本提交数据 → 部署 → 新 push 事件 → 再提交」会自激
- **抖音**：不能在 RSSHub 里跑（该路由要 Puppeteer），改由 `fetch_douyin.py` 用 Playwright 打开主页、拦截页面自己发出的作品接口；cookie 放 `~/douyin_cookies.txt`（Netscape 格式，不进仓库）
- **论文**：`fetch_orcid.py` 读 ORCID 公开记录，只会有正式发表、带 DOI 的条目
- **抓取失败**只打印警告并保留旧 JSON，不会让构建失败

## 改内容

| 想改什么 | 改哪里 |
|:---|:---|
| 站点标题、菜单、tagline、首页自我介绍 | `hugo.toml` |
| 首页社交按钮（GitHub / Email / 豆瓣 / RSS） | `hugo.toml` 的 `[[languages.*.params.socialIcons]]`（与 `data/profile.json` 保持一致） |
| 关于页 | `content/zh/about.md`（英文 `content/en/about.md`） |
| 博客 / 读书 / 技术笔记 | `content/zh/{posts,reading,notebook}/`（英文对应 `content/en/`） |
| 观影 / 动态页的文案 | `content/{zh,en}/{movies,activity}/_index.md` |
| 界面文案（导航、按钮、空状态） | `i18n/zh.toml` + `i18n/en.toml`（缺 key 时回落到主题的 `i18n/zh.yaml`） |
| 自写页面（观影/动态/项目）样式 | `assets/css/custom.css` |
| 主题配色 | 覆盖 `assets/css/extended/`，**不要改 `themes/PaperMod/`** |

**双语约定**：一篇内容要同时出现在两种语言里，两边的相对路径和 `slug` 必须一致（`content/zh/posts/foo.md` ↔ `content/en/posts/foo.md`），否则语言切换器认不出译文，只能跳回对方首页。

**封面**：文章用 `cover.image`，项目读 `data/projects.json`。文章封面是 1200×1200 方图，需设 `cover.hidden: true`（方形设计图当 PaperMod 横幅会撑满整屏），隐藏后仍会用于 `og:image`；项目卡是 16:9，封面也按 16:9 生成。

## 结构

```
content/zh/           中文内容（根路径）
content/en/           英文内容（/en/ 前缀）
  ├─ posts/           博客，按日期倒序
  ├─ reading/         读书笔记，按书名排序
  ├─ notebook/        技术笔记
  ├─ movies/          观影（数据来自 data/douban.json）
  ├─ activity/        动态时间线（data/activity.json）
  ├─ projects/        项目卡片（data/projects.json）
  ├─ archives/        归档（主题布局，年 → 月分组）
  └─ search/          站内搜索（主题布局，fuse.js）
data/                 JSON 数据，模板里用 hugo.Data.xxx 读
layouts/_default/     只放主题没有的三页：movies / activity / projects
layouts/shortcodes/   正文里插数据：douban-stats / activity-stats
assets/css/custom.css 上述三页的补充样式
themes/PaperMod/      主题（vendored，非 submodule；升级＝整目录覆盖）
scripts/              抓数据、生成封面、截图预览
```

## 站内搜索

首页模板额外输出一份 `index.json`（`[outputs] home = [..., "JSON"]`），`/search/` 用它做纯前端过滤，中英文都按子串匹配。

## 部署

推到 `main` → Actions 自动构建（`fetch_data.py` → `hugo --minify --gc`）→ GitHub Pages。

首次启用：仓库 Settings → Pages → Source 选 **GitHub Actions**。

数据的新鲜度靠本机计划任务（豆瓣观影 / 动态），它们定时跑脚本、有变化才 commit + push，从而触发一次部署。

## License

MIT — 见 [LICENSE](LICENSE)。文章与图片的著作权仍归作者所有，代码与模板可自由取用。

> 主题 `themes/PaperMod/` 按它自己的 [MIT 许可](themes/PaperMod/LICENSE) 分发。
