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

  var Review = {
    STATE_INTERVALS: STATE_INTERVALS,
    load: load, save: save, mark: mark, stateOf: stateOf,
    isDue: isDue, mergeImport: mergeImport, exportData: exportData
  };
  global.Review = Review;
  if (typeof module !== "undefined" && module.exports) module.exports = Review;
})(typeof window !== "undefined" ? window : this);
