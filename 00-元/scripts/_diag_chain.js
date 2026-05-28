// 诊断2：隔离"时机 vs 机制"。等渲染稳定后手动再跑一次 hbFit()，再测溢出是否消除。
// 用法: node _diag_chain.js <html路径> <out.json>
const { spawn } = require("child_process");
const path = require("path");
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const htmlPath = path.resolve(process.argv[2]);
const fileUri = "file:///" + htmlPath.replace(/\\/g, "/");
const outPath = path.resolve(process.argv[3] || "docs/student/_diag_chain.json");
const PORT = 9334;
const udd = path.join(require("os").tmpdir(), "diag2_edge_" + Date.now());
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${udd}`, "--no-first-run", "--no-default-browser-check",
  "--window-size=703,1100", fileUri,
]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 测量函数：报告 selector 内仍超 W 的元素(top8) + 已缩放数量（用 getBoundingClientRect.width 测真实渲染宽）。
const MEASURE = `(function(){
  var wrap=document.querySelector('.hb-wrap'); var W=(186*96/25.4)-6;
  var sel=['.bp-tree','.katex','.kp-zhuanti table','table','.kp-zhuanti pre'];
  var over=[]; var scaled=0;
  document.querySelectorAll(sel.join(',')).forEach(function(el){
    if(el.offsetParent===null) return;
    if(el.style.fontSize) scaled++;
    var rw=el.getBoundingClientRect().width;
    if(rw>W+1){ over.push({tag:el.tagName,cls:(''+el.className).slice(0,28),
      rw:Math.round(rw),sw:el.scrollWidth,fs:el.style.fontSize||'-',txt:(el.textContent||'').slice(0,40)}); }
  });
  over.sort(function(a,b){return b.rw-a.rw;});
  return {Wlimit:Math.round(W), hbwrap_sw:wrap.scrollWidth, hbwrap_ow:wrap.offsetWidth,
    scaled_count:scaled, over_count:over.length, over_top:over.slice(0,8)};
})()`;

async function main() {
  let target = null;
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); const list = await r.json();
      target = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl); if (target) break; } catch (e) {}
  }
  if (!target) { console.error("无法连接 Edge CDP"); edge.kill(); process.exit(1); }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  const send = (m, p) => new Promise((res) => { const i = ++id; pending[i] = res; ws.send(JSON.stringify({ id: i, method: m, params: p })); });
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending[m.id]) { pending[m.id](m.result); delete pending[m.id]; } });
  await new Promise((res) => ws.addEventListener("open", res));
  await send("Runtime.enable", {});
  await send("Emulation.setEmulatedMedia", { media: "print" });
  await sleep(40000);  // 等 KaTeX 全部渲染 + 自带 hbFit 跑完

  const before = await send("Runtime.evaluate", { expression: "JSON.stringify(" + MEASURE + ")", returnByValue: true });
  // 手动再跑一次 hbFit()（此时渲染必已完成）
  await send("Runtime.evaluate", { expression: "typeof hbFit==='function'?(hbFit(),'ran'):'NO_hbFit'", returnByValue: true });
  await sleep(1500);
  const after = await send("Runtime.evaluate", { expression: "JSON.stringify(" + MEASURE + ")", returnByValue: true });
  const out = { before: JSON.parse(before.result.value), after: JSON.parse(after.result.value) };
  require("fs").writeFileSync(outPath, JSON.stringify(out, null, 1), "utf8");
  ws.close(); edge.kill(); process.exit(0);
}
main().catch((e) => { require("fs").writeFileSync(outPath, "ERR: " + e.stack); edge.kill(); process.exit(1); });
