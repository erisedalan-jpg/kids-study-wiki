// KaTeX 公式体检：对 复习/<科>/*.md 的每个 $...$ / $$...$$ 用 vendored KaTeX
// 真跑 renderToString(throwOnError)，列出确切解析失败的公式（文件/片段/报错）。
// 与浏览器一致地加载 mhchem 扩展，故 \ce{} 不会误报。
// 用法: node 00-元/scripts/katex_lint.js <科> [科2 ...]    例: node ... 数学 化学
const fs = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..");
const VENDOR = path.join(REPO, "docs", "student", "vendor", "katex");
const katex = require(path.join(VENDOR, "katex.min.js"));
global.katex = katex;
// mhchem UMD 内部 require('katex')：把它解析到 vendored 实例，使 \ce 不误报
const Module = require("module");
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (req, ...rest) {
  if (req === "katex") return path.join(VENDOR, "katex.min.js");
  return origResolve.call(this, req, ...rest);
};
try { require(path.join(VENDOR, "contrib", "mhchem.min.js")); }
catch (e) { console.error("⚠ mhchem 未加载，\\ce 会误报:", e.message); }

const BLOCK = /\$\$[\s\S]*?\$\$/g;
const INLINE = /\$[^\$\n]+?\$/g;

function mathSpans(text) {
  const spans = [];
  let masked = text.replace(BLOCK, (m) => { spans.push([m.slice(2, -2), true]); return " "; });
  masked.replace(INLINE, (m) => { spans.push([m.slice(1, -1), false]); return " "; });
  return spans;
}

function lintSubject(subject) {
  const dir = path.join(REPO, "复习", subject);
  if (!fs.existsSync(dir)) { console.error(`无目录: ${dir}`); return []; }
  const fails = [];
  for (const fn of fs.readdirSync(dir).filter((f) => f.endsWith(".md"))) {
    const text = fs.readFileSync(path.join(dir, fn), "utf8");
    for (const [formula, display] of mathSpans(text)) {
      try {
        // strict:false 匹配浏览器宽松度（中文/①② 在数学里只 warn 不标红，非失败）；
        // 仅真 ParseError（不支持命令/不配对/缺底数）才算失败。
        katex.renderToString(formula, { throwOnError: true, strict: false, displayMode: display });
      } catch (e) {
        fails.push({ subject, file: fn, formula: formula.trim().slice(0, 70), msg: e.message.split("\n")[0] });
      }
    }
  }
  return fails;
}

const subjects = process.argv.slice(2);
if (!subjects.length) { console.error("用法: node katex_lint.js <科> [...]"); process.exit(2); }
let all = [];
for (const s of subjects) all = all.concat(lintSubject(s));
console.log(`\n=== KaTeX 失败 ${all.length} 处 ===`);
const byFile = {};
for (const f of all) (byFile[`${f.subject}/${f.file}`] ||= []).push(f);
for (const key of Object.keys(byFile).sort()) {
  console.log(`\n● ${key}`);
  for (const f of byFile[key]) console.log(`   [${f.msg}]  ${f.formula}`);
}
