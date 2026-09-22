# 项目约定

## 改动后默认提交并推送（重要）

对本机以下两个仓库的任何改动，完成后**默认直接 `git add -A && git commit && git push origin main`**，
无需再询问用户：

| 目录 | 远程 | 说明 |
| --- | --- | --- |
| `/home/crf/english` | `git@github.com:Medivhcrf/english.git` | 英语学习站点 |
| `/home/crf/.claude/skills` | `git@github.com:Medivhcrf/skills.git` | 自定义 skill 集合 |

- 只提交**实际有改动**的仓库（`git status` 为空就跳过）。
- 提交信息简洁，说明改了什么；不要提交密钥、`.ttsenv/`、`.ttslibs/`、`__pycache__/`（已在 `.gitignore`）。
- SSH 已配置好（github.com 在 known_hosts），直接 `git push` 即可。

## 站点

- `/home/crf/english` 通过 GitHub Pages 发布：<https://medivhcrf.github.io/english/>（分支部署，push 后自动更新）。
- 索引页由 `python3 build_index.py` 生成，会按设备显示：手机 → `-手机版.html`，电脑 → 桌面版 + PDF。

## 目录结构（重要：新内容要写进对应子目录）

**目录即分类**，`build_index.py` 直接扫子目录。新增内容请放进对应目录，不要再堆到根目录：

| 目录 | 内容 | 由谁生成 |
| --- | --- | --- |
| `daily/` | 每日词根词缀 `<日期>-词根词缀.{html,pdf}` | `daily-root-affix` skill |
| `topic/` | 词根词缀专题（总表 / 总辨析 / 语义分类 / 速查表） | 手动或 `build_*_root.py` |
| `review/` | 复习练习 `<日期>-词根词缀复习.*` | `root-affix-review` skill |
| `phrasal/` | 动词词组 | `daily-phrasal-verbs` skill |
| `speech/` | 演讲/文章精读（含同名 `<标题>.audio/` 逐句音频） | `english-article-reading` skill |
| `prep/` `mwvb/` `verb/` | 介词词源 / MWVB 词汇 / 不规则动词 | 对应主题内容 |

根目录只放：`index.html`、`build_*.py` 工具脚本、`words-audio/`（跨页共享发音，**固定在此**）、配置文件。

- 页面在子目录里，引用共享发音要写 `../words-audio/xxx.mp3`；
  逐句音频 `<标题>.audio/` 与页面同级，跟页面一起放。
- `gen_word_audio.py` 会自动推导前缀（可用 `--site-root` 覆盖），无需手工改路径。


## 技能

- 技能定义在 `/home/crf/.claude/skills/<name>/SKILL.md`，opencode 会自动加载；改动后需重启 opencode 生效。
