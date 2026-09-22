#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 /home/crf/english 下所有 HTML，生成分类索引页 index.html。
用法: python3 build_index.py
"""
import html as html_mod
import re
from datetime import date
from pathlib import Path

ENGLISH_DIR = Path("/home/crf/english")


def esc(s):
    return html_mod.escape(str(s), quote=False)


def classify(name):
    if "复习" in name:
        return "复习巩固", "review"
    if "动词词组" in name:
        return "动词词组", "phrasal"
    if "不规则动词" in name:
        return "不规则动词", "verb"
    if "介词" in name:
        return "介词本义与词源", "prep"
    if "MWVB" in name:
        return "MWVB 词汇（Merriam-Webster）", "mwvb"
    if "Speech" in name or "I-Have-a-Dream" in name:
        return "演讲精读", "speech"
    if any(k in name for k in ("词根", "词缀", "词源")):
        return "每日词根词缀", "daily"
    return "其他资料", "other"


def main():
    files = sorted(ENGLISH_DIR.glob("*.html"))
    files = [f for f in files if f.name != "index.html" and not f.name.endswith("-手机版.html")]

    groups = {"daily": [], "phrasal": [], "verb": [], "review": [], "prep": [], "mwvb": [], "speech": [], "other": []}
    for f in files:
        cat, key = classify(f.name)
        title = re.sub(r"\.html$", "", f.name)
        groups[key].append((f.name, title, cat))

    def items(key):
        html_parts = []
        for fname, title, cat in groups[key]:
            stem = fname[:-5]
            mob = f"{stem}-手机版.html"
            has_mob = (ENGLISH_DIR / mob).exists()
            pdf = fname.replace(".html", ".pdf")
            pdf_link = (f' <a href="{esc(pdf)}" class="pdf desktop-only">PDF ↗</a>'
                        if (ENGLISH_DIR / pdf).exists() else "")
            if has_mob:
                links = (f'<a class="main desktop-only" href="{esc(fname)}" target="_blank">{esc(title)}</a>'
                         f'<a class="main mobile-only" href="{esc(mob)}" target="_blank">{esc(title)}</a>')
            else:
                links = f'<a class="main" href="{esc(fname)}" target="_blank">{esc(title)}</a>'
            html_parts.append(f'<div class="file">{links}{pdf_link}</div>')
        return "".join(html_parts)

    today = date.today()
    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>古法编程技巧</title>
<style>
  @page {{ size: A4; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', sans-serif;
    background: #f5f6fa;
    color: #1f2937;
    line-height: 1.7;
    padding: 32px 20px 60px;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; }}
  .header {{
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    color: #fff;
    border-radius: 12px;
    padding: 26px 28px;
    margin-bottom: 24px;
  }}
  .header h1 {{ font-size: 24pt; letter-spacing: 1px; }}
  .header p {{ color: #dbeafe; font-size: 10pt; margin-top: 4px; }}
  .section {{
    background: #fff;
    border-radius: 12px;
    padding: 18px 22px 22px;
    margin-bottom: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }}
  .section h2 {{
    font-size: 13pt;
    padding-bottom: 8px;
    margin-bottom: 12px;
    border-bottom: 2px solid #e5e7eb;
    color: #1e3a8a;
  }}
  .section .count {{
    float: right;
    font-size: 9pt;
    color: #6b7280;
    font-weight: normal;
  }}
  .file {{
    display: flex;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px dashed #f0f1f4;
  }}
  .file:last-child {{ border-bottom: none; }}
  .file .main {{ color: #1e40af; text-decoration: none; font-size: 10.5pt; }}
  .file .main:hover {{ text-decoration: underline; color: #2563eb; }}
  .file .pdf {{
    margin-left: 12px;
    font-size: 8.5pt;
    color: #047857;
    text-decoration: none;
    border: 1px solid #a7f3d0;
    border-radius: 4px;
    padding: 0 6px;
    background: #ecfdf5;
  }}
  .file .pdf:hover {{ background: #d1fae5; }}
  .mobile-only {{ display: none; }}
  @media (max-width: 640px) {{
    body {{ padding: 18px 12px 40px; }}
    .header {{ padding: 20px 18px; }}
    .header h1 {{ font-size: 19pt; }}
    .section {{ padding: 14px 14px 16px; }}
    .section h2 {{ font-size: 12pt; }}
    .file .main {{ font-size: 10.5pt; }}
    .desktop-only {{ display: none !important; }}
    a.mobile-only {{ display: inline; }}
  }}
  .footer {{
    text-align: center;
    color: #9ca3af;
    font-size: 8.5pt;
    margin-top: 20px;
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🐚 古法编程技巧</h1>
    <p>C 语言 · 汇编 · 指针与内存 · 算法笔记 · 共 {len(files)} 篇 · 整理于 {today.year} 年 {today.month} 月 {today.day} 日</p>
  </div>

  <div class="section">
    <h2>经典算法专题 <span class="count">{len(groups['daily'])} 篇</span></h2>
    {items('daily')}
  </div>

  <div class="section">
    <h2>汇编优化笔记 <span class="count">{len(groups['phrasal'])} 篇</span></h2>
    {items('phrasal')}
  </div>

  <div class="section">
    <h2>指针与内存专题 <span class="count">{len(groups['prep'])} 篇</span></h2>
    {items('prep')}
  </div>

  <div class="section">
    <h2>数据结构专题 <span class="count">{len(groups['mwvb'])} 篇</span></h2>
    {items('mwvb')}
  </div>

  <div class="section">
    <h2>开源项目源码解读 <span class="count">{len(groups['speech'])} 篇</span></h2>
    {items('speech')}
  </div>

  <div class="section">
    <h2>编译原理笔记 <span class="count">{len(groups['verb'])} 篇</span></h2>
    {items('verb')}
  </div>

  <div class="section">
    <h2>代码复习与重构 <span class="count">{len(groups['review'])} 篇</span></h2>
    {items('review')}
  </div>

  <div class="section">
    <h2>疑难杂症排查 <span class="count">{len(groups['other'])} 篇</span></h2>
    {items('other')}
  </div>

  <div class="footer">重新生成：python3 /home/crf/english/build_index.py · 古法编程，贵在坚持 🐚</div>
</div>
</body>
</html>
"""
    out = ENGLISH_DIR / "index.html"
    out.write_text(html_out, encoding="utf-8")
    print(f"共 {len(files)} 份 HTML：词根词缀 {len(groups['daily'])} · 动词词组 {len(groups['phrasal'])} · 介词 {len(groups['prep'])} · MWVB {len(groups['mwvb'])} · 不规则动词 {len(groups['verb'])} · 复习 {len(groups['review'])} · 演讲 {len(groups['speech'])} · 其他 {len(groups['other'])}")
    print(f"输出: {out}")


if __name__ == "__main__":
    main()
