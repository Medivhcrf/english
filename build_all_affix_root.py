#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成"英语词根词缀总表"：按语义类型分组，★频率标记，标记已学。
用法: python3 build_all_affix_root.py
"""
import importlib.util
import subprocess
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude/skills/root-affix-review"))
from build_review import parse_daily_file

ENGLISH_DIR = Path("/home/crf/english")

_spec = importlib.util.spec_from_file_location("affix_data", Path(__file__).parent / "affix_data.py")
_affix_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_affix_data)
PREFIXES = _affix_data.PREFIXES
SUFFIXES = _affix_data.SUFFIXES
ROOTS = _affix_data.ROOTS

SRC_CLASS = {"拉丁": "lat", "希腊": "grk", "日耳曼": "ger", "拉丁/希腊": "grk", "法语": "fre"}


def esc(s):
    import html as h
    return h.escape(str(s), quote=False)


def learned_set():
    learned = set()
    for f in sorted(ENGLISH_DIR.glob("*-词根词缀.html")):
        if "复习" in f.name:
            continue
        d = parse_daily_file(f)
        for c in d["cards"]:
            learned.add(c["root"])
    return learned


def star(n):
    return "★" * n + "☆" * (3 - n)


# ===== 语义类型分类 =====

PREFIX_GROUPS = [
    "① 否定 · 反向", "② 方向 · 位置", "③ 数量 · 程度", "④ 时间 · 顺序",
    "⑤ 关系 · 比较", "⑥ 态度 · 评价", "⑦ 使动 · 强化",
]

PREFIX_KEYWORDS = [
    (["un-", "in-", "il-", "im-", "ir-", "dis-", "non-", "mis-", "de-", "a-", "an-", "dys-", "mal-", "male-", "neg-", "for-"], 0),
    (["ex-", "e-", "ef-", "sub-", "super-", "sur-", "trans-", "inter-", "pro-", "per-", "over-", "under-",
      "fore-", "out-", "intro-", "intra-", "extra-", "extro-", "circum-", "ab-", "abs-", "ad-", "ac-",
      "af-", "ag-", "al-", "ap-", "ar-", "as-", "at-", "ob-", "retro-", "para-", "epi-", "infra-",
      "endo-", "exo-", "cis-", "apo-", "cata-", "meta-", "juxta-", "with-", "down-", "up-", "by-",
      "mid-", "through-", "amphi-", "amb-", "ambi-"], 1),
    (["uni-", "mono-", "bi-", "bin-", "tri-", "quad-", "penta-", "hex-", "sext-", "sept-", "hept-",
      "oct-", "nov-", "dec-", "deci-", "cent-", "kilo-", "milli-", "semi-", "demi-", "hemi-", "multi-",
      "poly-", "omni-", "pan-", "micro-", "macro-", "mega-", "quasi-", "paleo-", "proto-"], 2),
    (["pre-", "post-", "fore-", "ante-", "retro-", "neo-", "meta-", "arch-", "mid-", "pro-"], 3),
    (["com-", "con-", "co-", "col-", "cor-", "syn-", "sym-", "syl-", "sys-", "inter-", "equi-", "iso-",
      "homo-", "hetero-", "contra-", "counter-", "ambi-", "quasi-", "cis-"], 4),
    (["anti-", "contra-", "counter-", "pro-", "eu-", "bene-", "mal-", "male-", "dys-", "dis-", "mis-",
      "anti-"], 5),
    (["en-", "em-", "be-", "hyper-", "ultra-", "extra-", "arch-", "vice-", "a-", "an-"], 6),
]

SUFFIX_GROUPS = [
    "① 名词后缀(抽象)", "② 名词后缀(人)", "③ 形容词后缀", "④ 动词后缀", "⑤ 副词后缀", "⑥ 学科·仪器后缀",
]

SUFFIX_KEYWORDS = [
    (["-tion", "-sion", "-ion", "-ment", "-ness", "-ity", "-ty", "-ance", "-ence", "-ancy", "-ency",
      "-ation", "-ition", "-age", "-dom", "-hood", "-ship", "-ism", "-al", "-ial", "-ary", "-ery",
      "-ory", "-tude", "-itude", "-acy", "-cy", "-ure", "-ture", "-ice", "-gram", "-sphere", "-ics",
      "-tics"], 0),
    (["-er", "-or", "-ar", "-ist", "-ant", "-ent", "-ee", "-ess", "-ian", "-an", "-eer", "-ier",
      "-ette"], 1),
    (["-ful", "-less", "-able", "-ible", "-ous", "-ious", "-uous", "-ive", "-ative", "-itive", "-ic",
      "-ical", "-ish", "-y", "-ly", "-like", "-al", "-ar", "-an", "-ian", "-ary", "-ate", "-en",
      "-ern", "-esque", "-fold", "-id", "-ile", "-il", "-ine", "-most", "-some", "-tive", "-ual",
      "-proof"], 2),
    (["-ize", "-ise", "-ify", "-fy", "-ate", "-en", "-ish", "-er"], 3),
    (["-ly", "-ward", "-wise", "-ways", "-way"], 4),
    (["-ology", "-logy", "-graphy", "-meter", "-metry", "-scope", "-phone", "-cide", "-phobia",
      "-phile"], 5),
]

ROOT_GROUP_ORDER = [
    # 每项 (组号, [关键词])
    (0, ["cap", "ten", "tact", "sum", "prehend", "rap", "em", "hab", "heir", "cept"]),
    (1, ["spect", "vis", "dict", "voc", "scrib", "graph", "log", "phon", "son", "aud", "scope",
    "lingu", "liter", "libr", "verb", "nomin", "onym", "loqu", "phas", "phem"]),
    (2, ["sens", "path", "psych", "sci", "cred", "fid", "soph", "anim", "vol", "clar", "cogn",
    "gnos", "mem", "ment", "neur", "psyche", "emot", "pat", "pass"]),
    (3, ["fac", "ag", "struct", "form", "morph", "pos", "loc", "techn", "art", "labor", "oper",
    "erg", "plasm", "fab", "doct", "educ"]),
    (4, ["ceed", "grad", "vad", "curr", "mov", "flu", "migr", "volv", "mut", "ven", "fer", "port",
    "mit", "ject", "ambul", "it", "nav", "veh", "ped", "plaud", "surg"]),
    (5, ["rupt", "frag", "cid", "press", "tract", "clin", "tort", "sect", "flect", "punct",
    "strict", "string", "cut", "fend", "lac", "puls", "trud", "vinc"]),
    (6, ["bio", "vit", "nat", "gen", "mort", "spir", "hydr", "aqua", "mar", "therm", "luc", "astr",
    "terr", "cosm", "cycl", "stell", "flor", "sol", "lun", "geo", "aer", "ign", "pyro",
    "flamm", "avi", "ornith", "pisc", "ichthy", "equ", "hipp", "can", "botan", "phyt",
    "arbor", "dendr", "foli", "lign", "herb", "carn", "omni", "lumin", "radi", "veni"]),
    (7, ["man", "ped", "corp", "anthrop", "card", "dent", "ocul", "capit", "crani", "faci",
    "derm", "oste", "arthr", "musc", "ven", "sanguin", "hem", "hepat", "nephr", "cardi",
    "gastr", "enter", "pneum", "rhin", "ophthalm", "ot", "labi", "ungu", "pod"]),
    (8, ["dem", "greg", "jur", "leg", "mand", "test", "bell", "milit", "neg", "not", "crim",
    "urb", "polit", "civ", "popul", "pac", "serv", "domin", "reg", "regal", "imper",
    "arist", "tyrann"]),
    (9, ["bene", "mal", "pot", "fort", "val", "magn", "micro", "mono", "un", "nov", "ver",
    "equ", "liber", "vac", "dynam", "auto", "fin", "prim", "clar", "vacu", "dens", "dur",
    "lev", "medi", "min", "par", "plen", "sol", "simil", "vari", "brevi", "long", "alt",
    "proxim", "celer", "grav", "lumin", "radi", "san", "salv", "cura", "medic", "pharmac",
    "tox", "carcin", "germ", "bon"]),
    (10, ["chron", "ann", "numer", "meter", "tele", "temp", "hor", "diur", "noct", "aev",
    "veter", "juven", "sen", "cent", "part", "tot", "unit", "bin", "tern", "quart",
    "decim", "centen", "millen"]),
    (11, ["junct", "sequ", "duc", "lect", "plic", "solv", "clud", "pend", "sed", "sta", "tend",
    "trib", "us", "here", "vert", "vers", "rot", "gyr", "circ", "glob", "orb", "coron",
    "termin", "limit", "extrem", "centr", "line", "rect", "curv", "ambl", "flect"]),
]

def classify(items, keywords, default):
    groups = {}
    for item in items:
        name = item[0]
        g = None
        for kws, gid in keywords:
            if any(name.startswith(k) for k in kws):
                g = gid
                break
        if g is None:
            g = default
        groups.setdefault(g, []).append(item)
    return groups


def render_group(items, learned):
    rows = []
    for item in items:
        if len(item) == 6:
            name, src, mean, words, note, lvl = item
        else:
            name, src, mean, words, lvl = item
            note = ""
        mark = '<span class="learned">已学</span>' if name in learned else ""
        src_c = SRC_CLASS.get(src, "lat")
        rows.append(
            f'<tr><td class="af">{esc(name)}{mark}</td>'
            f'<td class="src"><span class="s {src_c}">{esc(src)}</span></td>'
            f'<td>{esc(mean)}</td>'
            f'<td class="w"><b>{esc(words)}</b></td>'
            f'<td class="note2">{esc(note)}</td>'
            f'<td class="st">{star(lvl)}</td></tr>'
        )
    return "".join(rows)


def build_sections(items, groups, keywords, learned, default):
    classified = classify(items, keywords, default)
    parts = []
    for gid, gname in enumerate(groups):
        if gid not in classified:
            continue
        parts.append(f'<h3 class="sub">{gname}</h3>')
        parts.append('<table><tr><th>名称</th><th>来源</th><th>含义</th><th>代表词</th><th>辨析</th><th>频率</th></tr>')
        parts.append(render_group(classified[gid], learned))
        parts.append('</table>')
    return "".join(parts)


def main():
        learned = learned_set()
        pre_sections = build_sections(PREFIXES, PREFIX_GROUPS, PREFIX_KEYWORDS, learned, 0)
        suf_sections = build_sections(SUFFIXES, SUFFIX_GROUPS, SUFFIX_KEYWORDS, learned, 0)

        def root_group_id(name):
            for gid, kws in ROOT_GROUP_ORDER:
                if any(name.startswith(k) for k in kws):
                    return gid
            return None

        grouped_roots = {}
        for item in ROOTS:
            name = item[0].split("/")[0].strip()
            gid = root_group_id(name)
            grouped_roots.setdefault(gid, []).append(item)

        root_parts = []
        for gid in range(12):
            if gid not in grouped_roots:
                continue
            root_parts.append(f'<h3 class="sub">{"①②③④⑤⑥⑦⑧⑨⑩⑪⑫"[gid]} {["拿·抓·持·触","看·听·说","感受·认知·心灵","做·建·造·放","走·跑·流动·运送","破·切·压·拉","生命·自然·万物","人的身体","社会·群体·法律","属性·状态·抽象","时间·数字·度量","关系·连接·比较"][gid]}</h3>')
            root_parts.append('<table><tr><th>词根</th><th>来源</th><th>含义</th><th>代表词</th><th>频率</th></tr>')
            root_parts.append(render_group(grouped_roots[gid], learned))
            root_parts.append('</table>')


        today = date.today()
        doc = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <title>英语词根词缀总表</title>
    <style>
      @page {{ size: A4; margin: 14mm 13mm; }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', 'WenQuanYi Zen Hei', sans-serif;
        font-size: 9pt;
        color: #1f2937;
        line-height: 1.55;
      }}
      .header {{
        border-bottom: 3px solid #059669;
        padding-bottom: 9px;
        margin-bottom: 8px;
      }}
      .header h1 {{ font-size: 19pt; color: #065f46; }}
      .header .meta {{ color: #6b7280; font-size: 9.5pt; }}
      .header .meta b {{ color: #059669; }}
      .legend {{ font-size: 8.5pt; margin: 4px 0 10px 0; color: #4b5563; }}
      .legend span {{ display: inline-block; padding: 0 6px; border-radius: 3px; margin-right: 6px; }}
      .leg-lat {{ background: #dbeafe; color: #1e40af; }}
      .leg-grk {{ background: #fef3c7; color: #92400e; }}
      .leg-ger {{ background: #dcfce7; color: #166534; }}
      .learned {{
        display: inline-block; font-size: 7.5pt; background: #fef2f2; color: #b91c1c;
        border-radius: 3px; padding: 0 4px; margin-left: 5px; vertical-align: 1px;
      }}
      h2.section {{
        font-size: 12.5pt; color: #065f46; margin: 13px 0 6px 0;
        padding-left: 8px; border-left: 4px solid #059669; page-break-after: avoid;
      }}
      h3.sub {{
        font-size: 10.5pt; color: #b45309; margin: 10px 0 4px 0; page-break-after: avoid;
      }}
      table {{
        width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-bottom: 10px;
        page-break-inside: auto;
      }}
      th {{
        background: #059669; color: #fff; border: 1px solid #059669; padding: 3px 6px; text-align: left;
      }}
      td {{ border: 1px solid #e5e7eb; padding: 2px 6px; vertical-align: top; }}
      tr:nth-child(even) td {{ background: #f0fdf4; }}
      td.af {{ white-space: nowrap; font-weight: bold; color: #b91c1c; }}
      td .s {{ display: inline-block; font-size: 7.5pt; border-radius: 3px; padding: 0 4px; }}
      .s.lat {{ background: #dbeafe; color: #1e40af; }}
      .s.grk {{ background: #fef3c7; color: #92400e; }}
      .s.ger {{ background: #dcfce7; color: #166534; }}
      td.w b {{ color: #065f46; }}
      td.note2 {{ color: #6b7280; font-size: 8pt; }}
      td.st {{ color: #f59e0b; white-space: nowrap; font-size: 8pt; }}
      .footer {{
        margin-top: 14px; text-align: center; color: #9ca3af; font-size: 8.5pt;
        border-top: 1px solid #e5e7eb; padding-top: 6px;
      }}
    </style>
    </head>
    <body>
    <div class="header">
      <h1>英语词根词缀总表</h1>
      <div class="meta">{today.year} 年 {today.month} 月 {today.day} 日 ｜ <b>按类型归类 · 常用★标记</b> ｜ 前缀 {len(PREFIXES)} · 后缀 {len(SUFFIXES)} · 词根 {len(ROOTS)}</div>
    </div>
    <div class="legend">
      <span class="leg-lat">拉丁</span><span class="leg-grk">希腊</span><span class="leg-ger">日耳曼</span>
      ｜ 频率：<b style="color:#f59e0b">★ 越高越常用</b> ｜ <span style="background:#fef2f2;color:#b91c1c;border-radius:3px;padding:0 6px;">已学</span> = 每日词根词缀中学过
    </div>

    <h2 class="section">一、前缀（{len(PREFIXES)} 个 · 按类型）</h2>
    {pre_sections}

    <h2 class="section">二、后缀（{len(SUFFIXES)} 个 · 按功能）</h2>
    {suf_sections}

    <h2 class="section">三、词根（{len(ROOTS)} 个 · 按语义）</h2>
    {''.join(root_parts)}

    <div class="footer">英语词根词缀总表 · 按类型归类 · 学而时习之 👋</div>
    </body>
    </html>
    """
        out = ENGLISH_DIR / "2026-08-20-词根词缀总表.html"
        out.write_text(doc, encoding="utf-8")
        print(f"前缀 {len(PREFIXES)} · 后缀 {len(SUFFIXES)} · 词根 {len(ROOTS)}")
        print(f"HTML: {out}")


if __name__ == "__main__":
    main()


    def classify(items, keywords, default):
        """返回 {组序号: [items]}，组内保持原顺序（数据已按★排）。"""
        groups = {}
        for item in items:
            name = item[0]
            g = None
            for kws, gid in keywords:
                if any(name.startswith(k) for k in kws):
                    g = gid
                    break
            if g is None:
                g = default
            groups.setdefault(g, []).append(item)
        return groups


    def render_group(items, learned):
        rows = []
        for item in items:
            if len(item) == 6:
                name, src, mean, words, note, lvl = item
            else:
                name, src, mean, words, lvl = item
                note = ""
            mark = '<span class="learned">已学</span>' if name in learned else ""
            src_c = SRC_CLASS.get(src, "lat")
            rows.append(
                f'<tr><td class="af">{esc(name)}{mark}</td>'
                f'<td class="src"><span class="s {src_c}">{esc(src)}</span></td>'
                f'<td>{esc(mean)}</td>'
                f'<td class="w"><b>{esc(words)}</b></td>'
                f'<td class="note2">{esc(note)}</td>'
                f'<td class="st">{star(lvl)}</td></tr>'
            )
        return "".join(rows)


    def build_sections(items, groups, keywords, learned, default):
        classified = classify(items, keywords, default)
        parts = []
        for gid, gname in enumerate(groups):
            if gid not in classified:
                continue
            parts.append(f'<h3 class="sub">{gname}</h3>')
            parts.append('<table><tr><th>名称</th><th>来源</th><th>含义</th><th>代表词</th><th>辨析</th><th>频率</th></tr>')
            parts.append(render_group(classified[gid], learned))
            parts.append('</table>')
        return "".join(parts)


    def main():
        learned = learned_set()

        pre_sections = build_sections(PREFIXES, PREFIX_GROUPS, PREFIX_KEYWORDS, learned, 0)
        suf_sections = build_sections(SUFFIXES, SUFFIX_GROUPS, SUFFIX_KEYWORDS, learned, 0)

        def root_group_id(name):
            for gid, kws in ROOT_GROUP_ORDER:
                if any(name.startswith(k) for k in kws):
                    return gid
            return None

        grouped_roots = {}
        for item in ROOTS:
            name = item[0].split("/")[0].strip()
            gid = root_group_id(name)
            grouped_roots.setdefault(gid, []).append(item)

        root_parts = []
        for gid in range(12):
            if gid not in grouped_roots:
                continue
            root_parts.append(f'<h3 class="sub">{"①②③④⑤⑥⑦⑧⑨⑩⑪⑫"[gid]} {["拿·抓·持·触","看·听·说","感受·认知·心灵","做·建·造·放","走·跑·流动·运送","破·切·压·拉","生命·自然·万物","人的身体","社会·群体·法律","属性·状态·抽象","时间·数字·度量","关系·连接·比较"][gid]}</h3>')
            root_parts.append('<table><tr><th>词根</th><th>来源</th><th>含义</th><th>代表词</th><th>频率</th></tr>')
            root_parts.append(render_group(grouped_roots[gid], learned))
            root_parts.append('</table>')


        today = date.today()
        doc = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <title>英语词根词缀总表</title>
    <style>
      @page {{ size: A4; margin: 14mm 13mm; }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        font-family: 'Noto Sans CJK SC', 'Droid Sans Fallback', 'WenQuanYi Zen Hei', sans-serif;
        font-size: 9pt;
        color: #1f2937;
        line-height: 1.55;
      }}
      .header {{
        border-bottom: 3px solid #059669;
        padding-bottom: 9px;
        margin-bottom: 8px;
      }}
      .header h1 {{ font-size: 19pt; color: #065f46; }}
      .header .meta {{ color: #6b7280; font-size: 9.5pt; }}
      .header .meta b {{ color: #059669; }}
      .legend {{ font-size: 8.5pt; margin: 4px 0 10px 0; color: #4b5563; }}
      .legend span {{ display: inline-block; padding: 0 6px; border-radius: 3px; margin-right: 6px; }}
      .leg-lat {{ background: #dbeafe; color: #1e40af; }}
      .leg-grk {{ background: #fef3c7; color: #92400e; }}
      .leg-ger {{ background: #dcfce7; color: #166534; }}
      .learned {{
        display: inline-block; font-size: 7.5pt; background: #fef2f2; color: #b91c1c;
        border-radius: 3px; padding: 0 4px; margin-left: 5px; vertical-align: 1px;
      }}
      h2.section {{
        font-size: 12.5pt; color: #065f46; margin: 13px 0 6px 0;
        padding-left: 8px; border-left: 4px solid #059669; page-break-after: avoid;
      }}
      h3.sub {{
        font-size: 10.5pt; color: #b45309; margin: 10px 0 4px 0; page-break-after: avoid;
      }}
      table {{
        width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-bottom: 10px;
        page-break-inside: auto;
      }}
      th {{
        background: #059669; color: #fff; border: 1px solid #059669; padding: 3px 6px; text-align: left;
      }}
      td {{ border: 1px solid #e5e7eb; padding: 2px 6px; vertical-align: top; }}
      tr:nth-child(even) td {{ background: #f0fdf4; }}
      td.af {{ white-space: nowrap; font-weight: bold; color: #b91c1c; }}
      td .s {{ display: inline-block; font-size: 7.5pt; border-radius: 3px; padding: 0 4px; }}
      .s.lat {{ background: #dbeafe; color: #1e40af; }}
      .s.grk {{ background: #fef3c7; color: #92400e; }}
      .s.ger {{ background: #dcfce7; color: #166534; }}
      td.w b {{ color: #065f46; }}
      td.note2 {{ color: #6b7280; font-size: 8pt; }}
      td.st {{ color: #f59e0b; white-space: nowrap; font-size: 8pt; }}
      .footer {{
        margin-top: 14px; text-align: center; color: #9ca3af; font-size: 8.5pt;
        border-top: 1px solid #e5e7eb; padding-top: 6px;
      }}
    </style>
    </head>
    <body>
    <div class="header">
      <h1>英语词根词缀总表</h1>
      <div class="meta">{today.year} 年 {today.month} 月 {today.day} 日 ｜ <b>按类型归类 · 常用★标记</b> ｜ 前缀 {len(PREFIXES)} · 后缀 {len(SUFFIXES)} · 词根 {len(ROOTS)}</div>
    </div>
    <div class="legend">
      <span class="leg-lat">拉丁</span><span class="leg-grk">希腊</span><span class="leg-ger">日耳曼</span>
      ｜ 频率：<b style="color:#f59e0b">★ 越高越常用</b> ｜ <span style="background:#fef2f2;color:#b91c1c;border-radius:3px;padding:0 6px;">已学</span> = 每日词根词缀中学过
    </div>

    <h2 class="section">一、前缀（{len(PREFIXES)} 个 · 按类型）</h2>
    {pre_sections}

    <h2 class="section">二、后缀（{len(SUFFIXES)} 个 · 按功能）</h2>
    {suf_sections}

    <h2 class="section">三、词根（{len(ROOTS)} 个 · 按语义）</h2>
    {''.join(root_parts)}

    <div class="footer">英语词根词缀总表 · 按类型归类 · 学而时习之 👋</div>
    </body>
    </html>
    """
        out = ENGLISH_DIR / "2026-08-20-词根词缀总表.html"
        out.write_text(doc, encoding="utf-8")
        print(f"前缀 {len(PREFIXES)} · 后缀 {len(SUFFIXES)} · 词根 {len(ROOTS)}")
        print(f"HTML: {out}")


if __name__ == "__main__":
    main()
