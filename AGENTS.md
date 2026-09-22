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

## 技能

- 技能定义在 `/home/crf/.claude/skills/<name>/SKILL.md`，opencode 会自动加载；改动后需重启 opencode 生效。
