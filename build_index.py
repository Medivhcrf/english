#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 /home/crf/english 下所有 HTML，生成分类索引页 index.html。

用法: python3 build_index.py

设计要点
--------
- 站点是「英语学习站」，标题与分类均为英语学习内容。
  （此前本文件是从「古法编程技巧」项目整套复制来的，模板标题/分类硬编码为
   编程话题，而 classify() 返回的却是英语分类，两者从未对齐，导致索引页
   出现「经典算法专题」里装着词根词缀这类完全错配的情况。）
- 桌面显示「桌面版 + PDF」，手机只显示「手机版」（`-手机版.html` 不单独成条目）。
- 混入的非英语内容（编程/机器人笔记）由 EXCLUDE 兜住，不进索引。
- 同分类内按日期倒序（新的在前）。
"""
import html as html_mod
import re
from pathlib import Path

ENGLISH_DIR = Path("/home/crf/english")

SITE_TITLE = "英语学习站"
SITE_EMOJI = "📚"
SITE_DESC = "词根词缀 · 动词词组 · 文章精读 · 语法专题"

# 不属于英语学习站的文件（别的项目混进来的），不进索引
EXCLUDE = {
    "index.html",
    "s.html",          # VS Code Markdown 预览导出物，且引用 file:////root/... 死路径
}
EXCLUDE_KEYWORDS = ("激光", "里程计", "标定", "calibration")

# 分类顺序即索引里区块的先后；key 与 classify() 返回值对应
CATEGORIES = [
    ("speech", "演讲精读"),
    ("daily", "每日词根词缀"),
    ("topic", "词根词缀专题"),
    ("review", "复习巩固"),
    ("phrasal", "动词词组"),
    ("prep", "介词本义与词源"),
    ("mwvb", "MWVB 词汇"),
    ("verb", "不规则动词"),
    ("other", "其他资料"),
]


def esc(s):
    return html_mod.escape(str(s), quote=False)


def classify(name):
    """按文件名判分类。顺序有意为之：先具体后宽泛。"""
    if "复习" in name:
        return "review"
    if "动词词组" in name:
        return "phrasal"
    if "不规则动词" in name:
        return "verb"
    if "介词" in name:
        return "prep"
    if "MWVB" in name:
        return "mwvb"
    if "Speech" in name or "I-Have-a-Dream" in name:
        return "speech"
    # 汇总/辨析/速查类专题，与「每日」系列区分开
    if any(k in name for k in ("总表", "总辨析", "语义分类", "词根辨析", "速查表")):
        return "topic"
    if any(k in name for k in ("词根", "词缀", "词源")):
        return "daily"
    return "other"


def date_key(name):
    """取文件名开头的 YYYY-MM-DD 用于倒序；无日期者排最后。"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""


def collect():
    """按子目录收集内容。

    站点已按分类分子目录（daily/ speech/ review/ …），**目录即分类**。
    根目录下残留的 html 仍按文件名兜底分类，避免新增文件漏收。
    """
    groups = {k: [] for k, _ in CATEGORIES}
    for key, _ in CATEGORIES:
        d = ENGLISH_DIR / key
        if not d.is_dir():
            continue
        for f in d.glob("*.html"):
            if f.name.endswith("-手机版.html"):
                continue
            groups[key].append((key, f.name))
    # 根目录残留（未归档的）按文件名分类
    for f in ENGLISH_DIR.glob("*.html"):
        n = f.name
        if n in EXCLUDE or n.endswith("-手机版.html"):
            continue
        if any(k in n for k in EXCLUDE_KEYWORDS):
            continue
        groups[classify(n)].append(("", n))
    for k in groups:   # 同分类内新的在前
        groups[k].sort(key=lambda t: (date_key(t[1]), t[1]), reverse=True)
    return groups


def render_items(files):
    out = []
    for sub, fname in files:
        stem = fname[:-5]
        stem_path = (ENGLISH_DIR / sub / stem) if sub else (ENGLISH_DIR / stem)
        href = f"{sub}/{fname}" if sub else fname
        title = esc(stem)
        if stem_path.with_name(stem + "-手机版.html").exists():
            mhref = f"{sub}/{stem}-手机版.html" if sub else f"{stem}-手机版.html"
            links = (f'<a class="main desktop-only" href="{esc(href)}">{title}</a>'
                     f'<a class="main mobile-only" href="{esc(mhref)}">{title}</a>')
        else:
            links = f'<a class="main" href="{esc(href)}">{title}</a>'
        pdf_link = ""
        if stem_path.with_name(stem + ".pdf").exists():
            phref = f"{sub}/{stem}.pdf" if sub else f"{stem}.pdf"
            pdf_link = f'<a class="pdf desktop-only" href="{esc(phref)}">PDF</a>'
        out.append(f'    <div class="file">{links}{pdf_link}</div>')
    return "\n".join(out)


def render_sections(groups):
    out = []
    for key, name in CATEGORIES:
        files = groups[key]
        if not files:
            continue
        out.append('  <section class="section">\n'
                   f'    <h2>{esc(name)}<span class="count">{len(files)} 篇</span></h2>\n'
                   f'{render_items(files)}\n'
                   '  </section>')
    return "\n\n".join(out)


TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', sans-serif;
    background: #f5f6fa; color: #1f2937; line-height: 1.7;
    padding: 32px 20px 60px;
  }}
  .wrap {{ max-width: 820px; margin: 0 auto; }}
  .header {{
    background: linear-gradient(135deg, #7f1d1d, #b91c1c);
    color: #fff; border-radius: 12px; padding: 24px 26px; margin-bottom: 22px;
  }}
  .header h1 {{ font-size: 21pt; letter-spacing: 1px; }}
  .header p {{ color: #fecaca; font-size: 10pt; margin-top: 6px; }}
  .section {{
    background: #fff; border-radius: 12px; padding: 16px 20px 20px;
    margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }}
  .section h2 {{
    font-size: 12.5pt; padding-bottom: 8px; margin-bottom: 8px;
    border-bottom: 2px solid #f1f5f9; color: #7f1d1d;
    display: flex; justify-content: space-between; align-items: baseline;
  }}
  .section .count {{ font-size: 9pt; color: #94a3b8; font-weight: normal; }}
  .file {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 5px 0; border-bottom: 1px dashed #f1f5f9;
  }}
  .file:last-child {{ border-bottom: none; }}
  .file .main {{
    color: #1e40af; text-decoration: none; font-size: 10.5pt;
    font-family: 'DejaVu Sans', 'Noto Sans CJK SC', sans-serif;
  }}
  .file .main:hover {{ text-decoration: underline; }}
  .file .pdf {{
    flex: none; font-size: 8.5pt; color: #047857; text-decoration: none;
    border: 1px solid #a7f3d0; border-radius: 4px; padding: 0 6px; background: #ecfdf5;
  }}
  .file .pdf:hover {{ background: #d1fae5; }}
  .mobile-only {{ display: none; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 8.5pt; margin-top: 18px; }}
  .footer code {{ background: #eef2f7; padding: 1px 5px; border-radius: 4px; }}
  @media (max-width: 640px) {{
    body {{ padding: 16px 12px 40px; }}
    .header {{ padding: 18px 16px; }}
    .header h1 {{ font-size: 17pt; }}
    .section {{ padding: 13px 13px 15px; }}
    .section h2 {{ font-size: 11.5pt; }}
    .desktop-only {{ display: none !important; }}
    a.mobile-only {{ display: inline; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <h1>{emoji} {title}</h1>
    <p>{desc} · 共 {total} 篇 · 更新于 {updated}</p>
  </header>

{sections}

  <div class="footer">重新生成：<code>python3 build_index.py</code> · 每天一点，贵在坚持</div>
</div>
</body>
</html>
'''


def main():
    groups = collect()
    total = sum(len(v) for v in groups.values())
    # 「更新于」取全站最新日期，而不是只看每日系列
    newest = max((date_key(f[1]) for v in groups.values() for f in v), default="")
    html = TEMPLATE.format(
        title=SITE_TITLE, emoji=SITE_EMOJI, desc=SITE_DESC,
        total=total, updated=(newest or "—"),
        sections=render_sections(groups),
    )
    out = ENGLISH_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print("wrote %s  %d 篇" % (out, total))
    for key, name in CATEGORIES:
        if groups[key]:
            print("  %-14s %d 篇" % (name, len(groups[key])))


if __name__ == "__main__":
    main()
