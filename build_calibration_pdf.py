#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 激光轮式里程计联合标定.md 转成 HTML + PDF（支持 MathJax 公式与 Mermaid 图）。
用法: python3 build_calibration_pdf.py
"""
import re
import subprocess
from pathlib import Path
import html as html_mod

ENGLISH_DIR = Path("/home/crf/english")
MD_FILE = ENGLISH_DIR / "2026-08-21-激光轮式里程计联合标定.md"
HTML_FILE = ENGLISH_DIR / "2026-08-21-激光轮式里程计联合标定.html"
PDF_FILE = ENGLISH_DIR / "2026-08-21-激光轮式里程计联合标定.pdf"


def esc(s):
    return html_mod.escape(str(s), quote=False)


def inline(text):
    """行内元素：**粗体**、`代码`（公式 $...$ 原样保留给 MathJax）"""
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md_to_html(lines):
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 显示公式块：$$ 独占一行的块
        if line.strip() == "$$":
            buf = []
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<p>$$" + " ".join(buf).strip() + "$$</p>")
            continue
        # mermaid 代码块
        if line.strip() == "```mermaid":
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() != "```":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<pre class="mermaid">' + esc("\n".join(buf)) + "</pre>")
            continue
        # 其他代码块
        if line.strip().startswith("```"):
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                i += 1
            i += 1
            continue
        # 表格
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1]):
            header = line
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [c.strip() for c in header.strip("|").split("|")]
            out.append('<div class="tblwrap"><table>')
            out.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr></thead>")
            out.append("<tbody>")
            for r in rows:
                cs = [c.strip() for c in r.strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cs) + "</tr>")
            out.append("</tbody></table></div>")
            continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            out.append(f'<h{level}>{inline(m.group(2))}</h{level}>')
            i += 1
            continue
        # 无序列表（含嵌套）
        if re.match(r"^\s*[-*] ", line):
            indent = len(line) - len(line.lstrip())
            depth = indent // 2 + 1
            out.append(f'<ul class="d{depth}">')
            out.append(f"<li>{inline(line.strip()[2:])}</li>")
            i += 1
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                ind2 = len(lines[i]) - len(lines[i].lstrip())
                d2 = ind2 // 2 + 1
                if d2 != depth:
                    out.append(f'<ul class="d{d2}"><li>{inline(lines[i].strip()[2:])}</li></ul>')
                else:
                    out.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("</ul>")
            continue
        # 有序列表
        if re.match(r"^\d+\.\s+", line):
            out.append("<ol>")
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                out.append(f"<li>{inline(re.sub(r'^\d+\.\s+', '', lines[i]))}</li>")
                i += 1
            out.append("</ol>")
            continue
        # 引用
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(inline(lines[i].lstrip("> ")))
                i += 1
            out.append("<blockquote>" + "<br>".join(buf) + "</blockquote>")
            continue
        # 分隔线
        if re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        # 空行
        if not line.strip():
            i += 1
            continue
        out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


CSS = """
  @page { size: A4; margin: 16mm 15mm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, 'Segoe UI', 'Noto Sans CJK SC', 'Droid Sans Fallback',
      'WenQuanYi Zen Hei', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    color: #1f2328;
    background: #ffffff;
    line-height: 1.7;
  }
  h1 {
    font-size: 22pt;
    color: #1f2328;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 0.3em;
    margin: 12px 0 14px 0;
    page-break-after: avoid;
  }
  h2 {
    font-size: 15pt;
    color: #1f2328;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 0.3em;
    margin: 24px 0 10px 0;
    page-break-after: avoid;
  }
  h3 {
    font-size: 12.5pt;
    color: #1f2328;
    margin: 18px 0 8px 0;
    page-break-after: avoid;
  }
  h4 { font-size: 11pt; color: #1f2328; margin: 14px 0 6px 0; page-break-after: avoid; }
  p { margin: 8px 0; }
  a { color: #0969da; text-decoration: none; }
  strong, b { color: #1f2328; }
  code {
    background: #f6f8fa;
    border: 1px solid rgba(27,31,36,0.15);
    border-radius: 6px;
    padding: 0.2em 0.4em;
    font-family: 'SFMono-Regular', 'DejaVu Sans Mono', Consolas, monospace;
    font-size: 8.5pt;
    color: #1f2328;
  }
  blockquote {
    border-left: 0.25em solid #d0d7de;
    padding: 4px 14px;
    margin: 10px 0;
    color: #57606a;
    font-size: 9.5pt;
  }
  .tblwrap { margin: 10px 0 14px 0; overflow: hidden; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.8pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid #d0d7de;
    padding: 5px 9px;
    text-align: left;
  }
  th {
    background: #f6f8fa;
    font-weight: 600;
  }
  tr:nth-child(even) td { background: #f6f8fa; }
  ul, ol { padding-left: 26px; margin: 8px 0; }
  li { margin: 3px 0; page-break-inside: avoid; }
  ul.d2 { padding-left: 26px; margin: 3px 0; }
  hr { border: none; border-top: 1px solid #d0d7de; margin: 18px 0; }
  .mermaid {
    text-align: center;
    margin: 14px 0;
    page-break-inside: avoid;
  }
  .mermaid svg { max-width: 100%; height: auto; }
  mjx-container[display="true"] { margin: 10px 0 !important; }
  .footer {
    margin-top: 22px;
    text-align: center;
    color: #57606a;
    font-size: 8.5pt;
    border-top: 1px solid #d0d7de;
    padding-top: 8px;
  }
"""

MATHJAX_CONFIG = """
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  },
  svg: { fontCache: 'local' }
};
</script>
"""

BODY_SCRIPT = """
<script>
async function renderAll() {
  try {
    if (window.mermaid) {
      mermaid.initialize({ startOnLoad: false, theme: 'neutral',
        securityLevel: 'loose', flowchart: { useMaxWidth: true, htmlLabels: true } });
      await mermaid.run({ querySelector: '.mermaid' });
    }
    if (window.MathJax && MathJax.typesetPromise) {
      await MathJax.typesetPromise();
    }
  } catch (e) { console.error(e); }
}
window.addEventListener('load', renderAll);
setTimeout(renderAll, 300);
</script>
"""


def main():
    text = MD_FILE.read_text(encoding="utf-8")
    body = md_to_html(text.splitlines())

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>激光-轮式里程计联合标定</title>
{MATHJAX_CONFIG}
<script src="vendor/tex-svg.js"></script>
<script src="vendor/mermaid.min.js"></script>
<style>{CSS}</style>
{BODY_SCRIPT}
</head>
<body>
{body}
<div class="footer">激光-轮式里程计联合标定 · 2026-08-21</div>
</body>
</html>
"""
    HTML_FILE.write_text(html_doc, encoding="utf-8")
    print(f"HTML: {HTML_FILE}")

    cmd = [
        "google-chrome", "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=20000",
        f"--print-to-pdf={PDF_FILE}",
        f"file://{HTML_FILE}",
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"PDF:  {PDF_FILE}")


if __name__ == "__main__":
    main()
