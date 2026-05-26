/* 学生 HTML 站复习状态（纯前端 localStorage；与 mock_review.py 解耦） */
(function (global) {
  "use strict";
  var KEY = "kids-review-v1";
  var STATE_INTERVALS = { wrong: 86400000, fuzzy: 259200000, ok: 604800000 };
  var _mem = {}; // node / 无 localStorage 时的降级存储
  var hasLS = (typeof localStorage !== "undefined");

  function load() {
    if (!hasLS) return JSON.parse(JSON.stringify(_mem));
    try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; }
    catch (e) { return {}; }
  }
  function save(map) {
    if (!hasLS) { _mem = JSON.parse(JSON.stringify(map)); return; }
    localStorage.setItem(KEY, JSON.stringify(map));
  }
  function mark(stem, state) {
    var m = load();
    if (!STATE_INTERVALS[state]) { delete m[stem]; }
    else { m[stem] = { s: state, t: Date.now() }; }
    save(m); return m;
  }
  function stateOf(stem) {
    var e = load()[stem];
    return e ? e.s : null;
  }
  function isDue(stem, now) {
    var e = load()[stem];
    if (!e || !STATE_INTERVALS[e.s]) return false;
    return (now - e.t) >= STATE_INTERVALS[e.s];
  }
  function mergeImport(current, incoming) {
    var out = {}, k;
    for (k in current) if (current.hasOwnProperty(k)) out[k] = current[k];
    for (k in incoming) if (incoming.hasOwnProperty(k)) {
      if (!out[k] || (incoming[k].t || 0) > (out[k].t || 0)) out[k] = incoming[k];
    }
    return out;
  }
  function exportData() { return JSON.stringify(load()); }

  var STATE_LABEL = { ok: "✅已掌握", fuzzy: "⚠️模糊", wrong: "❌错题" };
  var STATE_ORDER = ["ok", "fuzzy", "wrong"];

  function renderMarks() {
    var cur = load();
    document.querySelectorAll(".review-mark").forEach(function (box) {
      var stem = box.getAttribute("data-stem");
      box.innerHTML = "";
      STATE_ORDER.forEach(function (st) {
        var b = document.createElement("button");
        b.className = "rmark-btn rmark-" + st;
        b.textContent = STATE_LABEL[st];
        if (cur[stem] && cur[stem].s === st) b.classList.add("active");
        b.addEventListener("click", function () {
          var now = (cur[stem] && cur[stem].s === st) ? null : st; // 再点取消
          mark(stem, now); renderMarks(); renderProgress();
        });
        box.appendChild(b);
      });
    });
  }

  function renderProgress() {
    var box = document.getElementById("review-progress");
    if (!box) return;
    var cur = load();
    var lis = document.querySelectorAll(".entry-list li[data-stem]");
    var total = lis.length, done = 0;
    lis.forEach(function (li) {
      var stem = li.getAttribute("data-stem");
      var st = cur[stem] ? cur[stem].s : null;
      var dot = li.querySelector(".rdot");
      if (!dot) { dot = document.createElement("span"); dot.className = "rdot"; li.insertBefore(dot, li.firstChild); }
      dot.className = "rdot rdot-" + (st || "none");
      if (st === "ok") done++;
    });
    var pct = total ? Math.round(done / total * 100) : 0;
    box.innerHTML = '<div class="rprog-label">已掌握 ' + done + ' / ' + total + '（' + pct + '%）</div>' +
      '<div class="rprog-bar"><div class="rprog-fill" style="width:' + pct + '%"></div></div>';
  }

  function applyFilter() {
    var sEl = document.getElementById("review-search");
    var fEl = document.getElementById("review-filter");
    var q = (sEl ? sEl.value : "").trim().toLowerCase();
    var mode = fEl ? fEl.value : "all";
    var now = Date.now(), cur = load();
    document.querySelectorAll(".entry-list li[data-stem]").forEach(function (li) {
      var stem = li.getAttribute("data-stem");
      var title = li.getAttribute("data-title") || "";
      var st = cur[stem] ? cur[stem].s : null;
      var okText = (q === "" || title.indexOf(q) !== -1);
      var okMode = true;
      if (mode === "wrong") okMode = (st === "wrong");
      else if (mode === "fuzzy") okMode = (st === "fuzzy");
      else if (mode === "unmarked") okMode = (st === null);
      else if (mode === "due") okMode = isDue(stem, now);
      li.style.display = (okText && okMode) ? "" : "none";
    });
  }

  function initIO() {
    var box = document.getElementById("review-io");
    if (!box) return;
    var exp = document.createElement("button");
    exp.textContent = "导出复习记录"; exp.className = "rio-btn";
    exp.addEventListener("click", function () {
      var blob = new Blob([exportData()], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      var d = new Date(); var ymd = d.getFullYear() +
        String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
      a.download = "kids-review-" + ymd + ".json"; a.click();
      URL.revokeObjectURL(a.href);
    });
    var imp = document.createElement("input");
    imp.type = "file"; imp.accept = "application/json"; imp.className = "rio-file";
    imp.addEventListener("change", function () {
      var f = imp.files[0]; if (!f) return;
      var fr = new FileReader();
      fr.onload = function () {
        try {
          var incoming = JSON.parse(fr.result);
          save(mergeImport(load(), incoming));
          renderMarks(); renderProgress(); applyFilter();
          alert("复习记录已导入合并。");
        } catch (e) { alert("导入失败：JSON 解析错误。"); }
      };
      fr.readAsText(f);
    });
    box.appendChild(exp); box.appendChild(imp);
  }

  function init() {
    renderMarks(); renderProgress(); initIO();
    var s = document.getElementById("review-search");
    var f = document.getElementById("review-filter");
    if (s) s.addEventListener("input", applyFilter);
    if (f) f.addEventListener("change", applyFilter);
    applyFilter();
  }

  var Review = {
    STATE_INTERVALS: STATE_INTERVALS,
    load: load, save: save, mark: mark, stateOf: stateOf,
    isDue: isDue, mergeImport: mergeImport, exportData: exportData,
    renderMarks: renderMarks, renderProgress: renderProgress,
    applyFilter: applyFilter, initIO: initIO, init: init
  };
  global.Review = Review;
  if (typeof module !== "undefined" && module.exports) module.exports = Review;
  if (typeof document !== "undefined") {
    if (document.readyState !== "loading") init();
    else document.addEventListener("DOMContentLoaded", init);
  }
})(typeof window !== "undefined" ? window : this);
