(function () {
  "use strict";
  var dataEl = document.getElementById("tts-data");
  if (!dataEl) return;
  var DATA;
  try { DATA = JSON.parse(dataEl.textContent); } catch (e) { return; }
  if (!DATA || !DATA.audio) return;

  var audio = new Audio();
  audio.preload = "metadata";
  audio.src = DATA.audio;

  var style = document.createElement("style");
  style.textContent =
    ".ck{cursor:pointer}" +
    ".ck.tts-on{outline:2.5px solid #b91c1c;outline-offset:1px;border-radius:3px;background-image:linear-gradient(rgba(185,28,28,.10),rgba(185,28,28,.10))}" +
    ".tts-btn{display:inline-block;border:0;background:#b91c1c;color:#fff;border-radius:50%;width:15px;height:15px;line-height:15px;font-size:9px;margin-right:5px;cursor:pointer;vertical-align:1.5px;padding:0;font-family:sans-serif}" +
    ".tts-btn.playing{background:#1e3a8a}" +
    "#tts-bar{position:fixed;right:12px;bottom:12px;z-index:9999;display:flex;gap:7px;font-family:sans-serif}" +
    "#tts-bar button{border:0;background:rgba(30,58,138,.93);color:#fff;border-radius:22px;padding:9px 15px;font-size:13px;cursor:pointer;box-shadow:0 3px 12px rgba(0,0,0,.28)}" +
    "#tts-bar button.stop{background:rgba(127,29,29,.93);display:none}" +
    "#tts-bar button.stop.show{display:inline-block}" +
    "@media print{.tts-btn,#tts-bar,.ck.tts-on{display:none!important}}";
  document.head.appendChild(style);

  var sentEls = document.querySelectorAll(".speech .sent");
  var chunkByEl = new Map();
  var allChunks = [];
  var maxSent = Math.min(sentEls.length, DATA.sents.length);
  for (var si = 0; si < maxSent; si++) {
    var sd = DATA.sents[si];
    var ckEls = sentEls[si].querySelectorAll(".ck");
    var n = Math.min(ckEls.length, sd.chunks.length);
    for (var ci = 0; ci < n; ci++) {
      var rec = { t0: sd.chunks[ci].t0, t1: sd.chunks[ci].t1, keys: sd.chunks[ci].keys, el: ckEls[ci] };
      chunkByEl.set(ckEls[ci], rec);
      allChunks.push(rec);
    }
  }

  var token = 0, playing = false, stopAt = 0, pending = null, lastOn = null;
  var playAllBtn = null, stopBtn = null;

  function setBar(on) {
    if (stopBtn) stopBtn.classList.toggle("show", on);
    if (playAllBtn) playAllBtn.textContent = on ? "\u275A\u275A \u6682\u505C" : "\u25B6 \u5168\u6587\u6717\u8BFB";
  }
  function clearHighlight() {
    if (lastOn) { lastOn.classList.remove("tts-on"); lastOn = null; }
  }
  function highlight(t) {
    var found = null;
    for (var i = 0; i < allChunks.length; i++) {
      var c = allChunks[i];
      if (t >= c.t0 - 0.05 && t < c.t1) { found = c.el; break; }
    }
    if (found !== lastOn) {
      if (lastOn) lastOn.classList.remove("tts-on");
      if (found) found.classList.add("tts-on");
      lastOn = found;
    }
  }
  function stop() {
    token++;
    playing = false;
    pending = null;
    try { audio.pause(); } catch (e) {}
    clearHighlight();
    setBar(false);
  }
  function doPending() {
    if (!pending) return;
    var t0 = pending.t0;
    pending = null;
    try { audio.currentTime = t0; } catch (e) {}
    var p = audio.play();
    if (p && p.catch) p.catch(function () {});
  }
  audio.addEventListener("loadedmetadata", doPending);
  audio.addEventListener("timeupdate", function () {
    if (!playing) return;
    if (audio.currentTime >= stopAt - 0.03) { stop(); return; }
    highlight(audio.currentTime);
  });
  audio.addEventListener("ended", function () { if (playing) stop(); });

  function playRange(t0, t1) {
    token++;
    playing = true;
    stopAt = t1;
    setBar(true);
    if (audio.readyState >= 1) {
      try { audio.currentTime = t0; } catch (e) {}
      var p = audio.play();
      if (p && p.catch) p.catch(function () {});
    } else {
      pending = { t0: t0 };
      audio.load();
    }
  }

  for (var k = 0; k < maxSent; k++) {
    (function (idx) {
      var el = sentEls[idx];
      var btn = document.createElement("button");
      btn.className = "tts-btn";
      btn.type = "button";
      btn.textContent = "\u25B6";
      btn.title = "\u6717\u8BFB\u6574\u53E5";
      var pnum = el.querySelector(".pnum");
      if (pnum) el.insertBefore(btn, pnum); else el.insertBefore(btn, el.firstChild);
      btn.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        var sd = DATA.sents[idx];
        playRange(sd.t0, sd.t1);
      });
    })(k);
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    var ck = null;
    while (t && t !== document.body) {
      if (t.classList && t.classList.contains("ck")) { ck = t; break; }
      t = t.parentNode;
    }
    if (!ck) return;
    var rec = chunkByEl.get(ck);
    if (!rec) return;
    var sup = e.target.closest ? e.target.closest(".sup") : null;
    if (sup && rec.keys) {
      var sups = ck.querySelectorAll(".sup");
      var idx = Array.prototype.indexOf.call(sups, sup);
      var kt = rec.keys[idx];
      if (kt) { playRange(kt[0], kt[1]); return; }
    }
    playRange(rec.t0, rec.t1);
  });

  var bar = document.createElement("div");
  bar.id = "tts-bar";
  playAllBtn = document.createElement("button");
  playAllBtn.type = "button";
  playAllBtn.textContent = "\u25B6 \u5168\u6587\u6717\u8BFB";
  stopBtn = document.createElement("button");
  stopBtn.type = "button";
  stopBtn.className = "stop";
  stopBtn.textContent = "\u25A0 \u505C\u6B62";
  bar.appendChild(playAllBtn);
  bar.appendChild(stopBtn);
  document.body.appendChild(bar);

  playAllBtn.addEventListener("click", function () {
    if (playing) { stop(); return; }
    playRange(0, DATA.total);
  });
  stopBtn.addEventListener("click", stop);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") stop();
  });
})();
