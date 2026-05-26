const assert = require("assert");
const Review = require("./review.js");

// 间隔表
assert.strictEqual(Review.STATE_INTERVALS.wrong, 86400000, "wrong=1d");
assert.strictEqual(Review.STATE_INTERVALS.fuzzy, 259200000, "fuzzy=3d");
assert.strictEqual(Review.STATE_INTERVALS.ok, 604800000, "ok=7d");

// mark + stateOf（node 下走内存降级）
Review.save({});
Review.mark("016-加法", "wrong");
assert.strictEqual(Review.stateOf("016-加法"), "wrong");
assert.strictEqual(Review.stateOf("999-不存在"), null);

// isDue：刚标记的 wrong 未到期；倒退 2 天则到期
const now = Date.now();
const m = Review.load();
assert.strictEqual(Review.isDue("016-加法", now), false, "刚标记不该到期");
m["016-加法"].t = now - 2 * 86400000;
Review.save(m);
assert.strictEqual(Review.isDue("016-加法", now), true, "2天前的wrong应到期");
assert.strictEqual(Review.isDue("999-不存在", now), false, "未标记不进队列");

// mergeImport：按 t 取较新
const cur = { a: { s: "ok", t: 100 }, b: { s: "wrong", t: 100 } };
const inc = { a: { s: "wrong", t: 200 }, c: { s: "ok", t: 50 } };
const merged = Review.mergeImport(cur, inc);
assert.strictEqual(merged.a.s, "wrong", "a 取较新 t=200");
assert.strictEqual(merged.b.s, "wrong", "b 仅 current 有");
assert.strictEqual(merged.c.s, "ok", "c 仅 incoming 有");

console.log("review.test.js: ALL PASS");
