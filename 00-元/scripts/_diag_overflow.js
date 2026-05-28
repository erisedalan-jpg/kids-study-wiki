// 诊断：用 Edge headless + CDP 加载手册 HTML，报告超出页宽的元素（class/宽度/是否已zoom）。
// 用法: node _diag_overflow.js <html路径>
const { spawn } = require("child_process");
const path = require("path");
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const htmlPath = path.resolve(process.argv[2]);
const fileUri = "file:///" + htmlPath.replace(/\\/g, "/");
const PORT = 9333;
const udd = path.join(require("os").tmpdir(), "diag_edge_" + Date.now());

// 窗口设为 A4 内容宽（210mm-24mm margin ≈ 703px@96dpi），模拟打印布局宽度
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
  let id = 0;
  const pending = {};
  const send = (method, params) => new Promise((res) => { const i = ++id; pending[i] = res; ws.send(JSON.stringify({ id: i, method, params })); });
  ws.addEventListener("message", (ev) => { const m = JSON.parse(ev.data); if (m.id && pending[m.id]) { pending[m.id](m.result); delete pending[m.id]; } });
  await new Promise((res) => ws.addEventListener("open", res));

  await send("Runtime.enable", {});
  await send("Emulation.setEmulatedMedia", { media: "print" });
  await sleep(35000); // 等 KaTeX 渲染（5800+公式）+ fit() 跑完（大文档）

  const expr = `(function(){
    var wrap=document.querySelector('.hb-wrap'); var W=wrap?wrap.clientWidth:document.body.clientWidth;
    var res=[];
    document.querySelectorAll('.katex,.bp-tree,.kp-zhuanti table,.kp-zhuanti pre,p,div,span,code').forEach(function(el){
      if(el.offsetParent===null) return;
      var sw=el.scrollWidth;
      if(sw>W+3){ res.push({tag:el.tagName,cls:(''+el.className).slice(0,45),sw:sw,zoom:el.style.zoom||'-'}); }
    });
    res.sort(function(a,b){return b.sw-a.sw;});
    var seen={}; var uniq=[];
    res.forEach(function(r){var k=r.tag+r.cls; if(!seen[k]){seen[k]=1;uniq.push(r);}});
    return JSON.stringify({pageW:W, katexN:document.querySelectorAll('.katex').length, zoomed:document.querySelectorAll('[style*=zoom]').length, top:uniq.slice(0,18)},null,1);
  })()`;
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
  require("fs").writeFileSync(path.resolve(process.argv[3] || "docs/student/_diag.json"),
    (r.result && r.result.value) || JSON.stringify(r), "utf8");
  ws.close(); edge.kill();
  process.exit(0);
}
main().catch((e) => { require("fs").writeFileSync("docs/student/_diag.json", "ERR: " + e.stack); edge.kill(); process.exit(1); });
