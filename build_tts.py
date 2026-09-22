#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给英语精读页注入「点击朗读」：用 edge-tts 生成整篇真人神经网络语音，
按句/色块/重点词切好时间轴，内嵌进 HTML，离线也能点读。

用法:
    PYTHONPATH=/home/crf/english/.ttslibs python3 build_tts.py <html> [voice] [rate]

- 默认音色 en-US-GuyNeural，语速 -8%。
- 会先备份 <html> 为 <html>.orig，再原地写入。
- 幂等：重复运行会先移除旧的 tts 注入。
"""
import os, re, sys, json, base64, asyncio, subprocess, shutil, tempfile, html as htmlmod

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_JS = os.path.join(HERE, "tts_client.js")
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
BITRATE = "24k"

SUP_RE = re.compile(r'<span class="sup">.*?</span>', re.S)
PNUM_RE = re.compile(r'<span class="pnum">.*?</span>', re.S)
SENT_RE = re.compile(r'<div class="sent">(.*?)</div>', re.S)
TAG_RE = re.compile(r'<[^>]+>')
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*")


def strip_tags(s):
    return htmlmod.unescape(TAG_RE.sub("", s))


def find_ck_spans(s):
    """Return list of (inner_html) for every <span class="ck">...</span>, balanced."""
    out = []
    for m in re.finditer(r'<span\b[^>]*class="ck"[^>]*>', s):
        i = m.end()
        depth = 1
        while i < len(s) and depth > 0:
            o = s.find("<span", i)
            c = s.find("</span>", i)
            if c == -1:
                break
            if o != -1 and o < c:
                depth += 1
                i = o + 5
            else:
                depth -= 1
                i = c + 7
        inner = s[m.end(): i - 7]
        out.append(inner)
    return out


def chunk_words_keys(inner):
    """Words in a chunk + article-word index of the word right before each sup."""
    words, keys, pos = [], [], 0
    for m in SUP_RE.finditer(inner):
        seg = inner[pos:m.start()]
        seg_words = WORD_RE.findall(strip_tags(seg))
        words += seg_words
        keys.append(len(words) - 1 if seg_words else None)
        pos = m.end()
    words += WORD_RE.findall(strip_tags(inner[pos:]))
    return words, keys


def parse(html_text):
    sents = []
    for sm in SENT_RE.finditer(html_text):
        inner = sm.group(1)
        full = strip_tags(SUP_RE.sub("", PNUM_RE.sub("", inner)))
        full = re.sub(r"\s+", " ", full).strip()
        chunks, art_words = [], []
        for ck in find_ck_spans(inner):
            cw, keys = chunk_words_keys(ck)
            a = len(art_words)
            art_words += cw
            b = len(art_words)
            chunks.append({"a": a, "b": b, "keys": keys, "nwords": len(cw)})
        sents.append({"full": full, "chunks": chunks, "nart": len(art_words)})
    return sents


async def synth_one(text, voice, rate):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate)
    audio = bytearray()
    bounds = []
    async for ch in comm.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            bounds.append({"text": ch["text"], "offset": ch["offset"], "duration": ch["duration"]})
    return bytes(audio), bounds


async def synth_all(texts, voice, rate, concurrency=4):
    sem = asyncio.Semaphore(concurrency)
    results = [None] * len(texts)

    async def worker(i):
        async with sem:
            for attempt in range(4):
                try:
                    results[i] = await synth_one(texts[i], voice, rate)
                    return
                except Exception as e:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(1.5 * (attempt + 1))

    await asyncio.gather(*(worker(i) for i in range(len(texts))))
    return results


def reencode(src, dst):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", src,
                    "-ac", "1", "-ar", "24000", "-b:a", BITRATE, dst], check=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def map_idx(i, n_art, n_tts):
    if n_art <= 0 or n_tts <= 0:
        return 0
    return min(n_tts - 1, int(round(i * n_tts / n_art)))


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python3 build_tts.py <html> [voice] [rate]")
    path = os.path.abspath(sys.argv[1])
    voice = sys.argv[2] if len(sys.argv) > 2 else "en-US-GuyNeural"
    rate = sys.argv[3] if len(sys.argv) > 3 else "-8%"

    html_text = open(path, encoding="utf-8").read()
    backup = path + ".orig"
    if not os.path.exists(backup):
        shutil.copyfile(path, backup)

    sents = parse(html_text)
    texts = [s["full"] for s in sents]
    print("句子数:", len(sents), "音色:", voice, "语速:", rate, flush=True)

    results = asyncio.run(synth_all(texts, voice, rate))

    tmp = tempfile.mkdtemp(prefix="tts_")
    clips, durs = [], []
    for i, (audio, _b) in enumerate(results):
        raw = os.path.join(tmp, "r%d.mp3" % i)
        enc = os.path.join(tmp, "%04d.mp3" % i)
        open(raw, "wb").write(audio)
        reencode(raw, enc)
        clips.append(enc)
        durs.append(duration(enc))
    print("音频生成完毕，总时长 %.1f 秒" % sum(durs), flush=True)

    listfile = os.path.join(tmp, "list.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write("file '%s'\n" % c)
    full_mp3 = os.path.join(tmp, "full.mp3")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", listfile, "-c", "copy", full_mp3], check=True)
    total = sum(durs)

    out_sents = []
    start = 0.0
    for i, s in enumerate(sents):
        bounds = results[i][1]
        n_tts = len(bounds)
        n_art = s["nart"]
        chunks_out = []
        for c in s["chunks"]:
            a, b = c["a"], c["b"]
            if b > a and n_tts:
                wi0 = map_idx(a, n_art, n_tts)
                wi1 = map_idx(b - 1, n_art, n_tts)
                t0 = start + bounds[wi0]["offset"] / 1e7
                t1 = start + (bounds[wi1]["offset"] + bounds[wi1]["duration"]) / 1e7
            else:
                t0 = t1 = start
            keys = []
            for ki in c["keys"]:
                if ki is None or not n_tts or n_art == 0:
                    keys.append(None)
                    continue
                wi = map_idx(a + ki, n_art, n_tts)
                k0 = start + bounds[wi]["offset"] / 1e7
                k1 = start + (bounds[wi]["offset"] + bounds[wi]["duration"]) / 1e7
                keys.append([round(k0, 3), round(k1, 3)])
            chunks_out.append({"t0": round(t0, 3), "t1": round(t1, 3), "keys": keys})
        out_sents.append({"t0": round(start, 3), "t1": round(start + durs[i], 3),
                          "chunks": chunks_out})
        start += durs[i]

    audio_b64 = base64.b64encode(open(full_mp3, "rb").read()).decode("ascii")
    data = {"voice": voice, "rate": rate, "total": round(total, 3),
            "audio": "data:audio/mpeg;base64," + audio_b64, "sents": out_sents}

    # idempotent: drop previous injection
    html_text = re.sub(r'<script id="tts-data" type="application/json">.*?</script>', "", html_text, flags=re.S)
    html_text = re.sub(r'<script id="tts-logic">.*?</script>', "", html_text, flags=re.S)

    js = open(CLIENT_JS, encoding="utf-8").read()
    payload = ('<script id="tts-data" type="application/json">'
               + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
               + "</script>\n<script id=\"tts-logic\">\n" + js + "\n</script>\n")
    html_text = html_text.replace("</body>", payload + "</body>", 1)
    open(path, "w", encoding="utf-8").write(html_text)

    shutil.rmtree(tmp, ignore_errors=True)
    size_mb = os.path.getsize(path) / 1048576.0
    print("已写入 %s（%.1f MB）" % (path, size_mb), flush=True)


if __name__ == "__main__":
    main()
