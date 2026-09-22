#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 词根词缀总表.md 转成排版精美的 HTML + PDF。
用法: python3 build_summary_pdf.py [--out 输出pdf路径]
"""
import re
import subprocess
import sys
from pathlib import Path
import html as html_mod

ENGLISH_DIR = Path("/home/crf/english")
MD_FILE = ENGLISH_DIR / "词根词缀总表.md"


def esc(s):
    return html_mod.escape(str(s), quote=False)


def inline(text):
    """处理行内元素：**粗体**、`代码`"""
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md_to_html(lines):
    """把 md 总表转成 HTML 片段。"""
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 表格
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1]):
            header = line
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [c.strip() for c in header.strip("|").split("|")]
            out.append("<table>")
            out.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr></thead>")
            out.append("<tbody>")
            for r in rows:
                cs = [c.strip() for c in r.strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cs) + "</tr>")
            out.append("</tbody></table>")
            continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = min(len(m.group(1)), 3)
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        # 无序列表（含嵌套）
        if line.startswith("- "):
            out.append("<ul>")
            out.append(f"<li>{inline(line[2:])}</li>")
            while i + 1 < len(lines) and lines[i + 1].startswith("- "):
                i += 1
                out.append(f"<li>{inline(lines[i][2:])}</li>")
            out.append("</ul>")
            i += 1
            continue
        # 引用
        if line.startswith(">"):
            out.append(f'<blockquote>{inline(line.lstrip("> "))}</blockquote>')
            i += 1
            continue
        # 空行
        if not line.strip():
            i += 1
            continue
        out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


def main():
    out_pdf = None
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == "--out" and args:
            out_pdf = Path(args.pop(0))

    text = MD_FILE.read_text(encoding="utf-8")
    body = md_to_html(text.splitlines())

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>词根词缀总表</title>
<style>
  @page {{ size: A4; margin: 16mm 14mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', 'WenQuanYi Zen Hei', sans-serif;
    font-size: 9.5pt;
    color: #1f2937;
    line-height: 1.6;
  }}
  h1 {{
    font-size: 20pt;
    color: #065f46;
    border-bottom: 3px solid #059669;
    padding-bottom: 8px;
    margin-bottom: 6px;
  }}
  blockquote {{
    background: #ecfdf5;
    border-left: 4px solid #059669;
    border-radius: 4px;
    padding: 6px 10px;
    margin: 6px 0 10px 0;
    color: #065f46;
    font-size: 9pt;
  }}
  h2 {{
    font-size: 13pt;
    color: #065f46;
    margin: 14px 0 6px 0;
    padding-left: 8px;
    border-left: 4px solid #059669;
  }}
  h3 {{
    font-size: 11pt;
    color: #b91c1c;
    margin: 12px 0 5px 0;
    background: #fef2f2;
    border-left: 4px solid #dc2626;
    padding: 4px 10px;
    border-radius: 4px;
    page-break-after: avoid;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin: 6px 0 10px 0;
    page-break-inside: avoid;
  }}
  th {{
    background: #059669;
    color: #fff;
    border: 1px solid #059669;
    padding: 3px 6px;
    text-align: left;
  }}
  td {{
    border: 1px solid #e5e7eb;
    padding: 2px 6px;
  }}
  td:first-child {{ white-space: nowrap; }}
  tr:nth-child(even) td {{ background: #f0fdf4; }}
  td b {{ color: #065f46; }}
  code {{
    background: #f1f5f9;
    border-radius: 3px;
    padding: 0 3px;
    font-family: 'DejaVu Sans Mono', monospace;
    font-size: 8.5pt;
    color: #be123c;
  }}
  ul {{ padding-left: 20px; margin: 2px 0; }}
  li {{ margin: 1px 0; page-break-inside: avoid; }}
  li b {{ color: #dc2626; }}
  p {{ margin: 4px 0; }}
  .footer {{
    margin-top: 16px;
    text-align: center;
    color: #9ca3af;
    font-size: 8pt;
    border-top: 1px solid #e5e7eb;
    padding-top: 6px;
  }}
</style>
</head>
<body>
{body}
<div class="footer">词根词缀总表 · 学而时习之 · 不亦说乎 👋</div>
</body>
</html>
"""
    html_path = ENGLISH_DIR / "词根词缀总表.html"
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"HTML: {html_path}")

    if not out_pdf:
        out_pdf = ENGLISH_DIR / "词根词缀总表.pdf"
    cmd = [
        "google-chrome", "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={out_pdf}",
        f"file://{html_path}",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"PDF:  {out_pdf}")


if __name__ == "__main__":
    main()
