#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网页/文章 → MP3：用 edge-tts 的微软神经网络语音把网页正文读成音频。

用法:
    webpage_tts.py <URL|文件|-> [-o out.mp3] [-v 音色] [-r 语速] [选项]

例:
    webpage_tts.py https://example.com/article -o a.mp3
    webpage_tts.py https://example.com/article --text-out a.txt --timing
    webpage_tts.py https://example.com/article --split          # 按段落切成多个 mp3
    webpage_tts.py https://example.com/article --sentence-split # 每句一个 mp3（站点点读结构）
    webpage_tts.py article.html -v en-GB-SoniaNeural -r -8%
    echo "hello world" | webpage_tts.py - -o hi.mp3

常用选项:
    -v/--voice   音色（默认 en-US-EmmaMultilingualNeural）
    -r/--rate    语速，如 +10% / -8%（默认 -3%）
    --split / --sentence-split / --outdir
    --timing [FILE]    输出句级时间轴 JSON
    --text-out FILE    输出提取后的纯文本
    --gap N            块间停顿秒数（默认 0.35）
    --proxy URL        走代理（也可用环境变量 EDGE_TTS_PROXY）
    --cookie STR       抓需要登录的页面
    --list-voices en   查看全部音色

特点:
- 不需要任何 Windows 设置，只用 Edge 同款在线神经语音（需联网）。
- 自动抓正文：优先 <article>/<main>，剔除脚本、导航、页脚、侧栏。
- 超长文本自动按句切块，用 WAV 中间态 concat 成整篇，块间插自然停顿。
- --timing 输出句级时间轴 JSON，可做逐句点读（配合 tts_client.js 那套思路）。
- 失败自动重试；并发度可调。

依赖: edge-tts（本机 /home/crf/len/.venv 里有），拼接 mp3 需要 ffmpeg（缺失时退化为直接拼接）。
"""
from __future__ import annotations

import argparse
import asyncio
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from html.parser import HTMLParser
from typing import Iterable

# ---------------------------------------------------------------- 常量

MAX_CHARS = 1800          # 单次请求最大字符数（edge-tts 长文本容易超时/报错）
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 Edg/124.0")
DEFAULT_VOICE = "en-US-EmmaMultilingualNeural"
DEFAULT_RATE = "-3%"      # 长文朗读稍慢一点更清楚
BITRATE = "32k"

# 英语常见缩写，避免在这里断句
ABBR = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "eg",
        "ie", "fig", "no", "vol", "ch", "sec", "gov", "ltd", "inc", "co",
        "approx", "dept", "est", "min", "max", "al", "cf", "ed", "eds", "pp"}

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head",
             "nav", "footer", "aside", "form", "iframe", "button", "select",
             "figcaption", "code", "pre"}
BLOCK_TAGS = {"p", "div", "section", "article", "main", "li", "dd", "dt",
              "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td",
              "th", "ul", "ol", "table", "header", "figure", "figcaption",
              "pre", "address", "hr", "br"}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- 抓取

def looks_like_url(s: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", s)) or \
        bool(re.match(r"^(www\.|localhost[:/]|\d+\.\d+\.\d+\.\d+)", s))


def fetch(url: str, cookie: str | None = None, timeout: int = 30) -> str:
    """抓取 URL 文本。优先用 requests，没有就退回 urllib。"""
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if cookie:
        headers["Cookie"] = cookie
    try:
        import requests  # type: ignore
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except ImportError:
        pass
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset()
    for enc in filter(None, [charset, "utf-8"]):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------- 正文提取

class Reader(HTMLParser):
    """把 HTML 变成若干段纯文本，尽量保留正文、丢掉页面框架。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paras: list[tuple[str, str]] = []   # (kind, text) kind: p/h/li
        self._depth_skip = 0
        self._stack: list[tuple[str, str]] = []  # (tag, kind)
        self._buf: list[str] = []
        self._kind: str | None = None
        self._tag: str | None = None
        self._main_seen = False
        self._article_seen = False

    # -- 内部
    def _flush(self):
        if self._kind and self._buf:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.paras.append((self._kind, text))
        self._buf = []
        self._kind = None
        self._tag = None

    def _open(self, tag: str, attrs):
        if tag in SKIP_TAGS:
            self._depth_skip += 1
            return
        if self._depth_skip:
            return
        if tag in ("article", "main"):
            self._flush()
            if tag == "article":
                self._article_seen = True
            else:
                self._main_seen = True
            return
        if tag in BLOCK_TAGS:
            self._flush()
            self._kind = "h" if tag in HEADING_TAGS else ("li" if tag == "li" else "p")
            self._tag = tag

    # -- HTMLParser 回调
    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if tag in ("br", "hr"):
            self._flush()
        else:
            self._open(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._depth_skip = max(0, self._depth_skip - 1)
            return
        if self._depth_skip:
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._depth_skip or not data:
            return
        if self._kind is None:
            if not data.strip():
                return
            self._kind, self._tag = "p", "p"
        self._buf.append(data)

    def paragraphs(self) -> list[tuple[str, str]]:
        self._flush()
        return self.paras


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def extract(html: str) -> tuple[str, list[tuple[str, str]]]:
    """返回 (标题, [(kind, text)])。"""
    title = ""
    m = TITLE_RE.search(html)
    if m:
        title = re.sub(r"\s+", " ", htmlmod.unescape(m.group(1))).strip()

    # 优先只解析 <article> / <main> 内部，减少噪音
    body = html
    for tag in ("article", "main"):
        mm = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, re.S | re.I)
        if mm and len(mm.group(1)) > 400:
            body = mm.group(1)
            break

    r = Reader()
    try:
        r.feed(body)
        r.close()
    except Exception as e:  # 畸形 HTML 不致命
        log("  [warn] HTML 解析异常，已尽力提取:", e)
    paras = r.paragraphs()

    # 短句碎片合并，超长段落拆分交给分块逻辑
    merged: list[tuple[str, str]] = []
    for kind, text in paras:
        if merged and kind == "p" and merged[-1][0] == "p" and len(merged[-1][1]) < 60:
            merged[-1] = ("p", merged[-1][1] + " " + text)
        else:
            merged.append((kind, text))
    return title, merged


# ---------------------------------------------------------------- 分块

def split_sentences(text: str) -> list[str]:
    """按句号/问号/感叹号/分号切句，简单跳过常见缩写。"""
    out, buf = [], []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        buf.append(ch)
        if ch in ".!?;。！？；":
            # 省略号、缩写、小数点不断句
            if ch == "." and i + 1 < n and text[i + 1].isdigit():
                i += 1
                continue
            if ch == "." and i + 2 < n and text[i + 1] == ".":
                i += 1
                continue
            tail = "".join(buf)
            w = re.search(r"([A-Za-z]+)\.$", tail)
            if w and w.group(1).lower() in ABBR:
                i += 1
                continue
            if i + 1 < n and text[i + 1] not in " \t\n\r\"')]":
                i += 1
                continue
            out.append("".join(buf).strip())
            buf = []
        i += 1
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return [s for s in out if s]


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """把长文本切成 <= max_chars 的块，尽量在句边界切。"""
    chunks, cur = [], ""
    for sent in split_sentences(text):
        if len(sent) > max_chars:      # 超长句硬切
            if cur:
                chunks.append(cur)
                cur = ""
            for k in range(0, len(sent), max_chars):
                chunks.append(sent[k:k + max_chars])
            continue
        if len(cur) + len(sent) + 1 > max_chars:
            chunks.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        chunks.append(cur)
    return chunks


# ---------------------------------------------------------------- 合成

async def synth(text: str, voice: str, rate: str, volume: str, pitch: str,
                retries: int = 4, proxy: str | None = None):
    """返回 (mp3 bytes, boundaries)。boundaries 为 [(text, offset_100ns, duration_100ns)]。"""
    import edge_tts
    last = None
    for attempt in range(retries):
        try:
            audio = bytearray()
            bounds: list[list] = []
            kw = {}
            if proxy:
                kw["proxy"] = proxy
            comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume,
                                        pitch=pitch, **kw)
            async for ch in comm.stream():
                if ch["type"] == "audio":
                    audio += ch["data"]
                elif ch["type"] in ("WordBoundary", "SentenceBoundary"):
                    bounds.append([ch.get("text", ""), ch["offset"], ch["duration"]])
            if not audio:
                raise RuntimeError("未收到音频数据")
            return bytes(audio), bounds
        except Exception as e:                      # noqa: BLE001
            last = e
            if attempt < retries - 1:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"合成失败: {last}")


async def synth_all(texts: list[str], voice: str, rate: str, volume: str,
                    pitch: str, concurrency: int = 3, proxy: str | None = None):
    sem = asyncio.Semaphore(concurrency)
    results: list = [None] * len(texts)

    async def worker(i: int):
        async with sem:
            results[i] = await synth(texts[i], voice, rate, volume, pitch, proxy=proxy)
            log(f"  [{i + 1}/{len(texts)}] {len(texts[i])} 字符")

    await asyncio.gather(*(worker(i) for i in range(len(texts))))
    return results


# ---------------------------------------------------------------- 音频拼接

def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def encode(src: str, dst: str, ffmpeg: str) -> None:
    """统一成 24kHz 单声道 WAV（无损，供拼接后再一次性编码 mp3）。"""
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                    "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", dst], check=True)


def duration(path: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def concat(clips: list[str], out: str, tmp: str,
           gap: float = 0.35) -> tuple[float, list[float]]:
    """把分块音频合成整篇。

    做法：每块先解码成 24kHz 单声道 WAV（顺带拿到精确时长），用 concat
    demuxer 串成一个流再编码成 mp3；块之间插 gap 秒静音当自然停顿。
    ffmpeg 缺失时退化为 mp3 直接字节拼接（不插停顿，时长可能不准）。

    返回 (总时长秒, 每块时长列表)。
    """
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        log("  [warn] 未找到 ffmpeg，退化为直接拼接（不插停顿，部分播放器时长不准）")
        with open(out, "wb") as w:
            for c in clips:
                w.write(open(c, "rb").read())
        return 0.0, [0.0] * len(clips)

    wavs = [os.path.join(tmp, f"e{i:04d}.wav") for i in range(len(clips))]
    for s, d in zip(clips, wavs):
        encode(s, d, ffmpeg)
    durs = [duration(w) for w in wavs]

    sil = None
    if gap > 0 and len(wavs) > 1:
        sil = os.path.join(tmp, "gap.wav")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=24000:cl=mono", "-t", f"{gap}",
                        "-c:a", "pcm_s16le", sil], check=True)

    listfile = os.path.join(tmp, "list.txt")
    with open(listfile, "w", encoding="utf-8") as f:
        for i, w in enumerate(wavs):
            if i and sil:
                f.write(f"file '{sil}'\n")
            f.write(f"file '{w}'\n")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", listfile,
                    "-ac", "1", "-ar", "24000", "-b:a", BITRATE, out], check=True)
    return duration(out), durs


# ---------------------------------------------------------------- 主流程

def stem_for(src: str, out: str | None) -> str:
    if out:
        return os.path.splitext(out)[0]
    if src == "-":
        return "stdin"
    if looks_like_url(src):
        from urllib.parse import urlparse
        p = urlparse(src)
        s = (p.netloc + p.path).strip("/")
    else:
        s = os.path.splitext(os.path.basename(src))[0]
    s = re.sub(r"[^\w\-.]+", "_", s).strip("_")
    return (s or "output")[:80]


async def convert(src: str, args) -> int:
    # 1. 取文本
    if src == "-":
        raw = sys.stdin.read()
        stem = stem_for(src, args.out)
        title, paras = "", [("p", p) for p in re.split(r"\n{2,}", raw) if p.strip()]
    elif looks_like_url(src):
        url = src if "://" in src else "https://" + src
        log(f"抓取 {url} ...")
        raw = fetch(url, args.cookie, args.timeout)
        stem = stem_for(src, args.out)
        title, paras = extract(raw)
    else:
        if not os.path.exists(src):
            log(f"错误: 找不到文件 {src}")
            return 2
        raw = open(src, encoding="utf-8", errors="replace").read()
        stem = stem_for(src, args.out)
        if raw.lstrip().startswith("<"):
            title, paras = extract(raw)
        else:
            title, paras = "", [("p", p) for p in re.split(r"\n{2,}", raw) if p.strip()]

    paras = [(k, t) for k, t in paras if len(t.strip()) >= 2]
    if not paras:
        log("错误: 没提取到任何正文")
        return 3
    chars = sum(len(t) for _, t in paras)
    log(f"正文 {len(paras)} 段 / {chars} 字符" + (f"（标题: {title}）" if title else ""))

    if args.text_out:
        with open(args.text_out, "w", encoding="utf-8") as f:
            if title:
                f.write(title + "\n\n")
            for k, t in paras:
                f.write(("# " if k == "h" else "") + t + "\n\n")
        log(f"纯文本已写入 {args.text_out}")

    # 逐句任务用的句子表（标题也当一句读）
    sents: list[str] = []
    if args.sentence_split:
        for kind, text in paras:
            sents.extend(split_sentences(text))
        log(f"逐句音频 {len(sents)} 句")

    # 2. 分配输出路径
    out_mp3 = args.out or (stem + ".mp3")
    outdir = args.outdir or (stem + ".audio")
    if args.split or args.sentence_split:
        os.makedirs(outdir, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(out_mp3)) or ".", exist_ok=True)

    # 3. 分段任务：--sentence-split 每句一个文件；--split 每段一个文件；否则合并整篇
    if args.sentence_split:
        groups = [(os.path.join(outdir, f"s{i + 1:03d}.mp3"), [("p", s)])
                  for i, s in enumerate(sents)]
    elif args.split:
        groups = [(os.path.join(outdir, f"{i + 1:02d}.mp3"), [("p", t)])
                  for i, (_k, t) in enumerate(paras)]
    else:
        groups = [(out_mp3, paras)]

    timing_out: dict = {"voice": args.voice, "rate": args.rate,
                        "source": src, "title": title, "files": []}

    for path, group in groups:
        if args.sentence_split:
            # 每句一个文件时，句边界就是文件边界，不再按 max_chars 合并
            texts = [t for _k, t in group]
            metas = [(k, t, 0) for k, t in group]
        else:
            texts, metas = [], []
            for kind, text in group:
                for ci, ch in enumerate(chunk_text(text)):
                    texts.append(ch)
                    metas.append((kind, text, ci))
        if not texts:
            continue
        log(f"合成 → {path}（{len(texts)} 块，音色 {args.voice}，语速 {args.rate}）")
        results = await synth_all(texts, args.voice, args.rate, args.volume,
                                  args.pitch, args.concurrency, args.proxy)

        tmp = tempfile.mkdtemp(prefix="wptts_")
        try:
            clips = []
            for i, (audio, _b) in enumerate(results):
                p = os.path.join(tmp, f"r{i:04d}.mp3")
                with open(p, "wb") as f:
                    f.write(audio)
                clips.append(p)
            total = 0.0
            durs: list[float] = []
            if len(clips) == 1 and not args.reencode:
                shutil.copyfile(clips[0], path)
                total = duration(path)
                durs = [total]
            else:
                total, durs = concat(clips, path, tmp, args.gap)

            # 4. 句级时间轴：块内 boundary 偏移 + 前面各块的实测时长
            if args.timing:
                entries = []
                base = 0.0
                for gi, (kind, text, _ci) in enumerate(metas):
                    bounds = results[gi][1]
                    for btext, off, dur in bounds:
                        entries.append({
                            "text": btext,
                            "start": round(base + off / 1e7, 3),
                            "end": round(base + (off + dur) / 1e7, 3),
                            "kind": kind,
                        })
                    base += durs[gi] if gi < len(durs) else 0.0
                timing_out["files"].append({
                    "mp3": os.path.basename(path),
                    "duration": round(total, 3),
                    "sentences": entries,
                })
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        size = os.path.getsize(path) / 1024.0
        log(f"完成 {path}（{size:.0f} KB）")

    # 5. 时间轴落盘（放最后，方便边生成边看）
    if args.timing:
        tpath = args.timing if isinstance(args.timing, str) else stem + ".timing.json"
        with open(tpath, "w", encoding="utf-8") as f:
            json.dump(timing_out, f, ensure_ascii=False, indent=1)
        log(f"时间轴已写入 {tpath}")

    return 0


def list_voices(lang: str) -> int:
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--list-voices"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        log(r.stderr.strip())
        return 1
    lines = r.stdout.splitlines()
    head = lines[:1]
    rows = [ln for ln in lines[1:] if lang.lower() in ln.lower()]
    print("\n".join(head + rows))
    return 0


def parse_args(argv: Iterable[str] | None = None):
    p = argparse.ArgumentParser(
        prog="webpage_tts.py",
        description="网页/文章 → 神经网络语音 MP3（edge-tts）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="音色示例:\n"
               "  en-US-EmmaMultilingualNeural   英式/美式皆可，清晰自然（默认）\n"
               "  en-US-AndrewMultilingualNeural 男声，温暖\n"
               "  en-US-AvaMultilingualNeural    女声，表现力强\n"
               "  en-US-BrianMultilingualNeural  男声，口语化\n"
               "  en-GB-SoniaNeural / en-GB-RyanNeural  英音\n"
               "  zh-CN-XiaoxiaoNeural / zh-CN-YunxiNeural  中文\n"
               "用 --list-voices en 查看全部。")
    p.add_argument("input", nargs="*", help="URL / HTML 文件 / 纯文本文件 / - 读标准输入")
    p.add_argument("-o", "--out", help="输出 mp3（默认按来源自动命名）")
    p.add_argument("-v", "--voice", default=DEFAULT_VOICE, help="音色（默认 %(default)s）")
    p.add_argument("-r", "--rate", default=DEFAULT_RATE, help="语速，如 +10%% / -8%%（默认 %(default)s）")
    p.add_argument("--volume", default="+0%", help="音量（默认 %(default)s）")
    p.add_argument("--pitch", default="+0Hz", help="音调，如 +2Hz / -3Hz（默认 %(default)s）")
    p.add_argument("-c", "--concurrency", type=int, default=3, help="并发请求数（默认 3）")
    p.add_argument("--max-chars", type=int, default=MAX_CHARS, help="单块最大字符数（默认 %(default)s）")
    p.add_argument("--split", action="store_true", help="按段落切成多个 mp3 而不是合成整篇")
    p.add_argument("--sentence-split", action="store_true",
                   help="逐句生成 s001.mp3, s002.mp3... 到 <名字>.audio/（站点点读结构）")
    p.add_argument("--outdir", help="--split/--sentence-split 的输出目录（默认 <名字>.audio/）")
    p.add_argument("--timing", nargs="?", const=True, default=False,
                   metavar="FILE", help="输出句级时间轴 JSON（默认 <名字>.timing.json）")
    p.add_argument("--text-out", metavar="FILE", help="同时保存提取出的纯文本")
    p.add_argument("--reencode", action="store_true", help="即使单块也重新编码统一码率")
    p.add_argument("--gap", type=float, default=0.35,
                   help="块之间的停顿秒数，0 为不插（默认 0.35）")
    p.add_argument("--cookie", help="抓取时附加的 Cookie 头（需要登录的页面）")
    p.add_argument("--proxy", help="edge-tts 用的代理，如 http://127.0.0.1:7890")
    p.add_argument("--timeout", type=int, default=30, help="抓取超时秒数（默认 30）")
    p.add_argument("--text", help="--try-voices 用的试听文本（默认一句英语长句）")
    p.add_argument("--list-voices", metavar="LANG", help="列出含该语言的音色后退出")
    p.add_argument("--try-voices", metavar="V1,V2,...", nargs="?", const="",
                   help="合成同一句试听样本（默认 6 个英语女声），方便挑音色后退出")
    return p.parse_args(list(argv) if argv is not None else None)


TRY_SENTENCE = ("Reading aloud is one of the oldest study techniques in the book. "
                "It forces you to slow down, and slowing down is where comprehension happens.")
TRY_VOICES = ["en-US-AvaMultilingualNeural", "en-US-EmmaMultilingualNeural",
              "en-US-AriaNeural", "en-US-JennyNeural",
              "en-GB-LibbyNeural", "en-GB-SoniaNeural"]


def try_voices(arg: str, args) -> int:
    """把同一句话用多个音色各合成一遍，输出到 voices/ 并生成对比页。"""
    voices = [v.strip() for v in arg.split(",") if v.strip()] if arg else TRY_VOICES
    outdir = args.outdir or "voices"
    os.makedirs(outdir, exist_ok=True)
    text = args.text or TRY_SENTENCE
    log(f"试听 {len(voices)} 个音色 → {outdir}/")
    sem = asyncio.Semaphore(args.concurrency)

    async def one(v: str):
        async with sem:
            audio, _b = await synth(text, v, args.rate, args.volume, args.pitch,
                                    proxy=args.proxy)
            p = os.path.join(outdir, f"{v}.mp3")
            with open(p, "wb") as f:
                f.write(audio)
            log(f"  {v} → {p}（{os.path.getsize(p) / 1024:.0f} KB）")

    asyncio.run(_gather([one(v) for v in voices]))

    rows = "\n".join(
        f'<div style="margin:10px 0;padding:10px;border:1px solid #e5e5e5;border-radius:8px">'
        f'<b>{i + 1}. {v}</b><br><audio controls preload="none" src="{v}.mp3" '
        f'style="width:100%"></audio></div>'
        for i, v in enumerate(voices))
    page = ("<!doctype html><meta charset=\"utf-8\"><title>音色对比</title>"
            "<style>body{font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif;"
            "max-width:760px;margin:24px auto;padding:0 16px}</style>"
            "<h1>音色对比</h1><p style='color:#666;font-size:13px'>点 ▶ 逐个听，"
            "记下名字，然后 <code>-v 名字</code> 就能用它朗读。</p>" + rows)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    log(f"对比页：{os.path.join(outdir, 'index.html')}")
    return 0


async def _gather(aws) -> None:
    await asyncio.gather(*aws)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    global MAX_CHARS
    MAX_CHARS = args.max_chars

    if args.list_voices:
        return list_voices(args.list_voices)

    if args.try_voices is not None:
        return try_voices(args.try_voices, args)

    if not args.input:
        log("错误: 没有输入。用 -h 查看用法，或传 URL/文件/-（标准输入）")
        return 2

    if len(args.input) > 1 and args.out:
        log("错误: 多个输入时不能用 -o（输出文件名会互相覆盖），请分次运行")
        return 1

    # 代理也可以从环境变量取
    if not args.proxy:
        args.proxy = os.environ.get("EDGE_TTS_PROXY") or None

    import asyncio as _asyncio
    rc = 0
    for src in args.input:
        try:
            code = _asyncio.run(convert(src, args))
        except KeyboardInterrupt:
            return 130
        except Exception as e:                      # noqa: BLE001
            log(f"错误: {src}: {e}")
            code = 1
        if code and not rc:
            rc = code
    return rc


if __name__ == "__main__":
    sys.exit(main())
