// 诊断2：定位最宽溢出元素的 ancestor 链，区分 scrollWidth(忽略zoom) vs rect.width(含zoom)。
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

async function main() {
  let target = null;
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await r.json();
      target = list.find((t) => t.type === "page" && t.webSocketDebuggerUrl);
      if (target) break;
    } catch (e) {}
  }
  if (!target) { console.error("无法连接 Edge CDP"); edge.kill(); process.exit(1); }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  const send = (m, p) => new Promise((res) => { const i = ++id; pending[i] = res; ws.send(JSON.stringify({ id: i, method: m, params: p })); });
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending[m.id]) { pending[m.id](m.result); delete pending[m.id]; } });
  await new Promise((res) => ws.addEventListener("open", res));
  await send("Runtime.enable", {});
  await send("Emulation.setEmulatedMedia", { media: "print" });
  await sleep(38000);

  const expr = `(function(){
    var wrap=document.querySelector('.hb-wrap'); var W=wrap?wrap.clientWidth:0;
    // 找 scrollWidth 最大的可见叶子(无子元素或文本节点)候选 + 整体最宽元素
    var widest=null, wmax=0;
    document.querySelectorAll('*').forEach(function(el){
      if(el.offsetParent===null) return;
      if(el.scrollWidth>wmax){wmax=el.scrollWidth; widest=el;}
    });
    function desc(el){ if(!el) return null;
      var r=el.getBoundingClientRect();
      return {tag:el.tagName, cls:(''+el.className).slice(0,40),
        sw:el.scrollWidth, ow:el.offsetWidth, rw:Math.round(r.width),
        zoom:el.style.zoom||'-', txt:(el.textContent||'').slice(0,45)};
    }
    // ancestor 链 from widest up to .hb-wrap
    var chain=[]; var cur=widest;
    while(cur && chain.length<12){ chain.push(desc(cur)); if(cur.classList&&cur.classList.contains('hb-wrap'))break; cur=cur.parentElement; }
    // 同时报告：被 zoom 的元素清单
    var zoomed=[]; document.querySelectorAll('[style*=zoom]').forEach(function(el){zoomed.push(desc(el));});
    return JSON.stringify({pageW_clientWidth:W, printW_703:Math.round(186*96/25.4),
      widest_chain:chain, zoomed:zoomed}, null, 1);
  })()`;
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  require("fs").writeFileSync(outPath, (r.result && r.result.value) || JSON.stringify(r), "utf8");
  ws.close(); edge.kill(); process.exit(0);
}
main().catch((e) => { require("fs").writeFileSync(outPath, "ERR: " + e.stack); edge.kill(); process.exit(1); });
