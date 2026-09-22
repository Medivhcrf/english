#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成"词根语义分类总表"：按语义分组，每个派生词都带完整拆词解析。
用法: python3 build_root_semantic.py
"""
import re
import subprocess
import sys
from pathlib import Path
import html as html_mod
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/root-affix-review"))
from build_review import parse_daily_file, ENGLISH_DIR

SKILL_DIR = Path(__file__).resolve().parent

# root -> (组序号, 来源)
# 来源: lat=拉丁 grk=希腊 ger=日耳曼
ROOT_GROUPS = {
    # G1 看·听·说
    "spect": (1, "lat"), "vis / vid": (1, "lat"), "scope": (1, "grk"),
    "aud / audit": (1, "lat"), "dict": (1, "lat"), "voc / vok": (1, "lat"),
    "log / logue": (1, "grk"), "son": (1, "lat"), "phon": (1, "grk"),
    "scrib / script": (1, "lat"), "graph": (1, "grk"),
    # G2 感受·认知·心灵
    "sens / sent": (2, "lat"), "path": (2, "grk"), "anim": (2, "lat"),
    "psych": (2, "grk"), "sci": (2, "lat"), "cred": (2, "lat"),
    "fid": (2, "lat"), "soph": (2, "grk"), "vol": (2, "lat"),
    "clar": (2, "lat"), "phil": (2, "grk"), "phob": (2, "grk"),
    # G3 做·建·造·放
    "fac / fact / fect": (3, "lat"), "ag / act": (3, "lat"),
    "struct": (3, "lat"), "form": (3, "lat"), "morph": (3, "grk"),
    "pos / pon": (3, "lat"), "loc": (3, "lat"), "techn": (3, "grk"),
    "art": (3, "lat"), "labor": (3, "lat"),
    # G4 拿·抓·持·触
    "cap / capt / cept / ceive": (4, "lat"), "ten / tin / tain": (4, "lat"),
    "tact / tang / tag": (4, "lat"),
    # G5 走·跑·流动·运送
    "ceed / cess": (5, "lat"), "grad / gress": (5, "lat"), "vad / vas": (5, "lat"),
    "curr / curs": (5, "lat"), "mov / mot / mob": (5, "lat"), "flu / flux": (5, "lat"),
    "migr": (5, "lat"), "volv / volu / volt": (5, "lat"), "mut": (5, "lat"),
    "ven / vent": (5, "lat"), "fer": (5, "lat"), "port": (5, "lat"),
    "mit / miss": (5, "lat"), "ject": (5, "lat"),
    # G6 破·切·压·拉
    "rupt": (6, "lat"), "frag / fract": (6, "lat"), "cid / cis": (6, "lat"),
    "press": (6, "lat"), "tract": (6, "lat"),
    # G7 生命·自然·万物
    "bio": (7, "grk"), "vit / viv": (7, "lat"), "nat / nasc": (7, "lat"),
    "gen / gener": (7, "lat"), "mort": (7, "lat"), "spir": (7, "lat"),
    "hydr": (7, "grk"), "aqua / aqu": (7, "lat"), "mar": (7, "lat"),
    "therm": (7, "grk"), "luc / lux / lumin": (7, "lat"),
    "astr / aster": (7, "grk"), "terr / terra": (7, "lat"),
    "cosm": (7, "grk"), "cycl": (7, "grk"),
    # G8 人的身体
    "man / manu": (8, "lat"), "ped / pod": (8, "lat"), "corp / corpor": (8, "lat"),
    "anthrop": (8, "grk"),
    # G9 社会·群体·法律·秩序
    "dem": (9, "grk"), "greg": (9, "lat"), "jur / jus": (9, "lat"),
    "mand": (9, "lat"), "test": (9, "lat"),
    "bell": (9, "lat"), "neg": (9, "lat"), "not": (9, "lat"),
    "punct": (9, "lat"),
    # G10 属性·状态·抽象
    "bene / bon": (10, "lat"), "pot": (10, "lat"), "fort": (10, "lat"),
    "val / vail": (10, "lat"), "magn / maj / max": (10, "lat"),
    "micro": (10, "grk"), "mono": (10, "grk"), "un / uni": (10, "lat"),
    "nov": (10, "lat"), "ver": (10, "lat"), "equ": (10, "lat"),
    "liber": (10, "lat"), "vac / van / void": (10, "lat"),
    "dynam": (10, "grk"), "auto": (10, "grk"),
    # G11 时间·数字·度量
    "chron": (11, "grk"), "ann / enn": (11, "lat"), "numer": (11, "lat"),
    "meter / metr": (11, "grk"), "prim": (11, "lat"), "fin": (11, "lat"),
    "tele": (11, "grk"),
    # G12 关系·连接·比较
    "junct / join / joint": (12, "lat"), "sequ / secut / suit": (12, "lat"),
    "duc / duct": (12, "lat"), "reg / rect": (12, "lat"),
    "lect / leg / lig": (12, "lat"), "plic / pli / plex": (12, "lat"),
    "solv / solu / solut": (12, "lat"), "clud / clus / clos": (12, "lat"),
    "pend / pens": (12, "lat"), "sed / sess / sid": (12, "lat"),
    "sta / stat / stit": (12, "lat"), "tend / tent / tens": (12, "lat"),
    "trib": (12, "lat"), "us / uti": (12, "lat"),
}

GROUPS = [
    "看 · 听 · 说（感官与语言）",
    "感受 · 认知 · 心灵",
    "做 · 建 · 造 · 放（生产与构造）",
    "拿 · 抓 · 持 · 触",
    "走 · 跑 · 流动 · 运送（运动）",
    "破 · 切 · 压 · 拉（破坏与施力）",
    "生命 · 自然 · 万物",
    "人的身体",
    "社会 · 群体 · 法律 · 秩序",
    "属性 · 状态 · 抽象",
    "时间 · 数字 · 度量",
    "关系 · 连接 · 比较",
]

SRC_LABEL = {"lat": "拉丁", "grk": "希腊", "ger": "日耳曼"}
SRC_CLASS = {"lat": "lat", "grk": "grk", "ger": "ger"}

# 常见前缀/后缀 → (含义, 优先级)。按最长优先匹配。
PREFIXES = [
    ("inter", "在…之间"), ("circum", "环绕"), ("super", "超越/上"), ("intro", "向内"),
    ("intra", "内部"), ("trans", "横跨"), ("under", "在下"), ("over", "过度/上"),
    ("semi", "半"), ("anti", "对抗"), ("multi", "多"), ("omni", "全"),
    ("mega", "巨大"), ("micro", "微小"), ("tele", "远"), ("auto", "自己"),
    ("contra", "反对"), ("extra", "超出"), ("ante", "之前"), ("post", "之后"),
    ("fore", "预先"), ("per", "贯穿/彻底"), ("sub", "在下"), ("pre", "预先"),
    ("re", "再/回"), ("dis", "分开/否定"), ("un", "不/反"), ("non", "非"),
    ("mis", "错"), ("de", "向下/反转"), ("ex", "向外"), ("e", "向外"),
    ("in", "向内/否定"), ("im", "向内/否定"), ("il", "否定"), ("ir", "否定"),
    ("ad", "朝向"), ("con", "一起"), ("com", "一起"), ("co", "一起"),
    ("col", "一起"), ("cor", "一起"), ("pro", "向前/支持"), ("ab", "离开"),
    ("ob", "朝向/逆"), ("en", "使"), ("em", "使"), ("bi", "二"), ("a", "使/向"),
]
SUFFIXES = [
    ("ation", "名词(动作)"), ("ition", "名词(动作)"), ("ment", "名词(结果)"),
    ("ness", "名词(状态)"), ("ity", "名词(性质)"), ("tion", "名词(动作)"),
    ("ance", "名词(状态)"), ("ence", "名词(状态)"), ("able", "可…的"),
    ("ible", "可…的"), ("ous", "充满…的"), ("al", "…的"), ("ive", "倾向于…"),
    ("ful", "充满…的"), ("less", "无…的"), ("ship", "身份/关系"),
    ("hood", "阶段/群体"), ("dom", "领域"), ("age", "行为/总量"),
    ("ize", "使…化"), ("ify", "使…"), ("er", "…的人"), ("or", "…的人"),
    ("ist", "…的人"), ("ant", "…的人"), ("ent", "…的人"), ("ee", "被…的人"),
    ("ess", "女性"), ("ette", "小"), ("ly", "…地"), ("y", "…的"),
    ("ure", "名词"), ("acy", "名词"), ("cy", "名词"), ("ic", "…的"),
    ("ical", "…的"), ("ive", "…的"),
]


def decompose(word, root):
    """尝试把 word 拆出 前缀(含义)。仅返回前缀，避免误拆后缀/词根。"""
    w = word.lower()
    # 已知词根开头的词不拆前缀（如 biography 的 bio 是词根不是 bi 前缀）
    root_heads = {"bio", "tele", "auto", "micro", "mono", "cycl", "graph", "chron", "phil", "phob",
                  "psych", "soph", "scope", "meter", "dynam", "techn", "cosm", "astr", "aqua", "hydr",
                  "therm", "anthrop", "demo", "morph", "bene", "nov", "multi"}
    for head in sorted(root_heads, key=len, reverse=True):
        if w.startswith(head):
            return ""
    for pf, pf_m in PREFIXES:
        if w.startswith(pf) and len(pf) >= 2 and len(w) > len(pf) + 2:
            after = w[len(pf):]
            if len(after) < 3:
                continue
            return f"{pf}({pf_m})"
    return ""


def esc(s):
    return html_mod.escape(str(s), quote=False)


def main():
    files = sorted(ENGLISH_DIR.glob("*-词根词缀.html"))
    files = [f for f in files if "复习" not in f.name]
    cards_by_root = {}
    for f in files:
        d = parse_daily_file(f)
        for c in d["cards"]:
            if not c["affix"] and c["root"]:
                cards_by_root[c["root"]] = c

    # 组装分组
    groups_html = {i: [] for i in range(1, 13)}
    num = 0
    for root, (g, src) in ROOT_GROUPS.items():
        c = cards_by_root.get(root)
        if not c:
            print(f"!! 未找到词根: {root}")
            continue
        num += 1
        mean = esc(c["meaning"]).lstrip("=").strip()
        src_label = SRC_LABEL.get(src, "")
        src_cls = SRC_CLASS.get(src, "")
        words = ""
        for w in c["words"]:
            if not w["word"]:
                continue
            m = esc(w["meaning"]).strip()
            # 自动拆解部件：如 expect → ex-(向外)+spect+… 
            decomp = decompose(w["word"], c["root"])
            decomp_html = f' <span class="decomp">{esc(decomp)}</span>' if decomp else ""
            if m:
                words += f'<div class="w"><b>{esc(w["word"])}</b>{decomp_html} <span class="wm">{m}</span></div>'
            else:
                words += f'<div class="w"><b>{esc(w["word"])}</b>{decomp_html}</div>'
        groups_html[g].append(
            f'<div class="card"><div class="head"><span class="num">{num}</span>'
            f'<span class="root">{esc(root)}</span><span class="src {src_cls}">{src_label}</span> '
            f'<span class="mean">＝ {mean}</span></div><div class="words">{words}</div></div>'
        )

    total = num
    sections = []
    for g in range(1, 13):
        if not groups_html[g]:
            continue
        sections.append(f'<h2 class="section">{"一二三四五六七八九十"[:2]}{g}、{GROUPS[g-1]}</h2>')
        sections.append('<div class="cards">' + "".join(groups_html[g]) + "</div>")

    today = date.today()
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>词根语义分类总表 · {total} 个</title>
<style>
  @page {{ size: A4; margin: 15mm 14mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', 'WenQuanYi Zen Hei', sans-serif;
    font-size: 9.5pt;
    color: #1f2937;
    line-height: 1.55;
  }}
  .header {{
    border-bottom: 3px solid #059669;
    padding-bottom: 9px;
    margin-bottom: 8px;
  }}
  .header h1 {{ font-size: 19pt; color: #065f46; letter-spacing: 1px; }}
  .header .meta {{ color: #6b7280; font-size: 9.5pt; margin-top: 2px; }}
  .header .meta b {{ color: #059669; }}
  .legend {{ font-size: 8.5pt; margin-bottom: 8px; color: #4b5563; }}
  .legend span {{ display: inline-block; padding: 0 6px; border-radius: 3px; margin-right: 6px; }}
  .leg-lat {{ background: #dbeafe; color: #1e40af; }}
  .leg-grk {{ background: #fef3c7; color: #92400e; }}
  h2.section {{
    font-size: 12.5pt;
    color: #065f46;
    margin: 14px 0 7px 0;
    padding-left: 8px;
    border-left: 4px solid #059669;
    page-break-after: avoid;
  }}
  .card {{
    border: 1px solid #e5e7eb;
    border-left: 3px solid #2563eb;
    border-radius: 5px;
    padding: 5px 9px 6px 9px;
    margin-bottom: 5px;
    page-break-inside: avoid;
  }}
  .card .head {{ margin-bottom: 2px; }}
  .card .num {{
    display: inline-block;
    width: 14px; height: 14px;
    background: #2563eb; color: #fff;
    border-radius: 50%;
    text-align: center; line-height: 14px;
    font-size: 7.5pt; font-weight: bold;
    margin-right: 5px;
  }}
  .card .root {{ font-size: 11pt; font-weight: bold; color: #1e3a8a; font-family: 'DejaVu Sans', sans-serif; }}
  .card .src {{
    display: inline-block; font-size: 7.5pt; border-radius: 3px; padding: 0 4px; margin-left: 5px; vertical-align: 1px;
  }}
  .card .src.lat {{ background: #dbeafe; color: #1e40af; }}
  .card .src.grk {{ background: #fef3c7; color: #92400e; }}
  .card .src.ger {{ background: #dcfce7; color: #166534; }}
  .card .mean {{ color: #4b5563; font-size: 9pt; }}
  .card .words {{ font-size: 8.8pt; }}
  .card .w {{ margin: 1px 0; }}
  .card .w b {{ color: #b91c1c; }}
  .card .wm {{ color: #374151; }}
  .card .decomp {{ color: #6d28d9; font-size: 8pt; margin-left: 4px; }}
  .footer {{
    margin-top: 14px; text-align: center; color: #9ca3af; font-size: 8.5pt;
    border-top: 1px solid #e5e7eb; padding-top: 6px;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>词根语义分类总表 · {total} 个</h1>
  <div class="meta">{today.year} 年 {today.month} 月 {today.day} 日 ｜ <b>17 天所学全部词根</b> ｜ 每个词都带拆词解析</div>
</div>
<div class="legend"><span class="leg-lat">拉丁</span><span class="leg-grk">希腊</span></div>
{''.join(sections)}
<div class="footer">词根语义分类总表 · 学而时习之 · 不亦说乎 👋</div>
</body>
</html>
"""
    out = ENGLISH_DIR / "2026-08-20-词根语义分类.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"共 {total} 个词根")
    print(f"HTML: {out}")


if __name__ == "__main__":
    main()
