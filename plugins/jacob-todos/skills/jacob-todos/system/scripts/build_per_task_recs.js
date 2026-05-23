// build_per_task_recs.js — generates one HTML recommendation page per task
// (2026-05-16 — replaces the all-in-one create_recommendations_doc.js).
//
// Output: <root>/recs/rec_<task_id>.html — one file per active task.
// Linked from check_in.html via the "View suggested plan →" anchor that
// build_check_in.js emits next to each task. So Jacob's read flow is:
//
//   check_in.html  →  click "View suggested plan →"  →  rec_tNNN.html
//
// The rec page renders the `solution` field as RICH HTML (headers, lists,
// tables, links, bold) via the `marked` markdown parser. This is
// load-bearing — content that's just newline-separated prose is not what
// a recommendation page should look like (Jacob, 2026-05-16:
// "[recs should be] presentable and nice and rich instead of writing
// those dry words"). If a future generator wants the recommendation to
// look good, it should write the solution field as markdown.
//
// Usage:
//   node build_per_task_recs.js [output_dir]
//
//   output_dir defaults to the to-do root (`..`). Pass an alternative
//   only for piloting.

const fs = require('fs');
const path = require('path');
const { marked } = require('marked');

// Configure marked: GitHub-style line breaks + smart enough table rendering.
marked.setOptions({
  gfm: true,
  breaks: false,        // we have explicit \n\n between paragraphs already
  headerIds: false,
});

const SCRIPT_DIR = __dirname;
const ROOT = path.resolve(SCRIPT_DIR, '..');
const TASKS_PATH = path.join(SCRIPT_DIR, 'tasks_v3.json');

const outputDir = process.argv[2] ? path.resolve(process.argv[2]) : ROOT;
const recsDir = path.join(outputDir, 'recs');
fs.mkdirSync(recsDir, { recursive: true });

const tasks = JSON.parse(fs.readFileSync(TASKS_PATH, 'utf-8'))
  .filter(t => t.status !== 'done');

const today = new Date();
const todayStr = today.toLocaleDateString('en-US', {
  weekday: 'long', month: 'short', day: 'numeric', year: 'numeric',
});

// ─── helpers ───────────────────────────────────────────────────────────────
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function daysSince(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return Math.floor((today - d) / 86400000);
}
function fmtAgo(iso) {
  const ago = daysSince(iso);
  if (ago === null) return '—';
  if (ago === 0) return 'today';
  if (ago === 1) return 'yesterday';
  return `${ago} days ago`;
}

// Decide whether to render markdown or fall back to plain text.
// Heuristic: if the string contains any markdown-flavored signal
// (heading, bold, list, link, table, blockquote), pass it to marked.
// Otherwise, emit a single <p> with line breaks.
function isMarkdownish(s) {
  if (!s) return false;
  return /(^|\n)#{1,6}\s|\*\*|^\s*[-*]\s|\[[^\]]+\]\([^)]+\)|^\s*\|.+\|.+\|/m.test(s);
}
function renderSolution(solutionText) {
  if (!solutionText) return '';
  if (isMarkdownish(solutionText)) {
    return marked.parse(solutionText);
  }
  // Plain prose fallback — preserve paragraph breaks.
  const paragraphs = solutionText
    .split(/\n{2,}/)
    .map(p => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`)
    .join('');
  return paragraphs;
}

// ─── styles ────────────────────────────────────────────────────────────────
// Designed to make rendered-markdown content feel polished — proper
// heading hierarchy, readable lists, table styling, callouts for the
// status line, link styling, and a clean back-bar at top.
const css = `
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 920px; margin: 24px auto; padding: 0 24px 80px;
    color: #1a1a1a; line-height: 1.6; font-size: 15.5px;
  }
  .back-bar {
    font-size: 13.5px; margin: 0 0 18px;
    padding: 9px 14px; background: #f4f3ee; border-radius: 4px;
  }
  .back-bar a { color: #2d5f8f; text-decoration: none; font-weight: 500; }
  .back-bar a:hover { text-decoration: underline; }
  h1.task-title { font-size: 24px; margin: 6px 0 4px; font-weight: 600; line-height: 1.3; }
  h1.task-title .rank, h1.task-title .task-id {
    color: #999; font-weight: 400; font-size: 15px; margin-right: 6px;
  }
  .meta-row {
    color: #888; font-size: 13px; margin: 0 0 16px;
    padding-bottom: 12px; border-bottom: 1px solid #eee;
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  }
  .pill {
    display: inline-block; font-size: 11px; padding: 3px 9px; border-radius: 10px;
    background: #eee; color: #555; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.4px;
  }
  .pill.dl-soon { background: #fff4e0; color: #6b4d00; }
  .pill.dl-overdue { background: #fbe4e4; color: #7a1f1f; }
  .pill.cat { background: #e2eef7; color: #1a4d6e; }
  .meta-bit { color: #666; font-size: 13px; }
  .desc {
    color: #555; font-size: 14px; margin: 4px 0 18px;
    padding: 10px 14px; background: #fafaf2;
    border-left: 3px solid #d4cba5; border-radius: 0 4px 4px 0;
    white-space: pre-wrap;
  }
  .rec-header {
    color: #2d5f8f; font-weight: 600; font-size: 15px;
    margin: 18px 0 10px; padding-bottom: 6px;
    border-bottom: 1px dashed #cdd9e3;
  }
  .status-badge { color: #888; font-style: italic; font-weight: 400; font-size: 12px; margin-left: 6px; }

  /* ── rich markdown rendering ── */
  .rec-body { color: #222; }
  .rec-body h1, .rec-body h2, .rec-body h3, .rec-body h4 {
    margin: 22px 0 8px; line-height: 1.3; color: #1a1a1a;
  }
  .rec-body h1 { font-size: 21px; }
  .rec-body h2 { font-size: 18px; padding-bottom: 4px; border-bottom: 1px solid #ececec; }
  .rec-body h3 { font-size: 16px; color: #333; }
  .rec-body h4 { font-size: 14.5px; color: #444; }
  .rec-body p { margin: 8px 0; }
  .rec-body ul, .rec-body ol { margin: 8px 0 8px 4px; padding-left: 22px; }
  .rec-body li { margin: 4px 0; }
  .rec-body li > p { margin: 4px 0; }
  .rec-body strong { color: #111; }
  .rec-body em { color: #444; }
  .rec-body a { color: #2d5f8f; text-decoration: none; border-bottom: 1px solid #bfd3e3; }
  .rec-body a:hover { text-decoration: none; border-bottom-color: #2d5f8f; background: #eef4fa; }
  .rec-body code {
    background: #f4f3ee; padding: 1px 5px; border-radius: 3px;
    font-family: ui-monospace, Menlo, monospace; font-size: 13.5px;
  }
  .rec-body pre {
    background: #f4f3ee; padding: 12px 14px; border-radius: 4px;
    overflow-x: auto; font-size: 13.5px;
  }
  .rec-body pre code { background: none; padding: 0; }
  .rec-body blockquote {
    margin: 10px 0; padding: 6px 14px; color: #555;
    border-left: 3px solid #d4cba5; background: #fafaf2;
  }
  .rec-body hr { border: 0; border-top: 1px solid #e6e2d4; margin: 18px 0; }
  .rec-body table {
    border-collapse: collapse; margin: 12px 0; font-size: 14px;
    width: 100%;
  }
  .rec-body th, .rec-body td {
    border: 1px solid #e0dac4; padding: 7px 10px; text-align: left; vertical-align: top;
  }
  .rec-body th { background: #faf8ee; font-weight: 600; }
  .rec-body tr:nth-child(even) td { background: #fbfaf3; }

  .ineligible { color: #b0b0b0; font-style: italic; font-size: 13.5px; margin: 18px 0; }
  .footer { color: #888; font-style: italic; font-size: 12px; margin: 22px 0 4px; }
  .sources { margin: 20px 0 6px; font-size: 13.5px; }
  .sources-label { color: #888; font-style: italic; }
  .sources ul { margin: 4px 0 0 0; padding-left: 18px; }
  .sources a { color: #2d5f8f; }
  .questions {
    margin: 20px 0 6px; font-size: 14px;
    background: #fdf6e3; padding: 10px 14px;
    border-left: 3px solid #b8860b; border-radius: 0 4px 4px 0;
  }
  .questions-label { color: #b8860b; font-weight: 600; }
  .questions ul { margin: 4px 0 0 0; padding-left: 18px; color: #6a5d2c; }
`;

function deadlineHtml(task) {
  if (!task.deadline) return '';
  const d = new Date(task.deadline + 'T00:00:00Z');
  const t = new Date(today.toISOString().slice(0,10) + 'T00:00:00Z');
  const days = Math.round((d - t) / 86400000);
  let cls = 'pill';
  if (days < 0) cls = 'pill dl-overdue';
  else if (days <= 3) cls = 'pill dl-soon';
  const lbl = days < 0 ? `${Math.abs(days)}d overdue` : (days === 0 ? 'today' : `+${days}d`);
  return `<span class="${cls}">⏰ ${escapeHtml(task.deadline)} · ${lbl}</span>`;
}

function renderRecBody(task) {
  const eligibility = task.solution_eligibility || null;
  const status = task.solution_status || null;
  const solution = task.solution || null;
  const sources = Array.isArray(task.solution_sources) ? task.solution_sources : [];

  if (eligibility && eligibility !== 'eligible') {
    const reasonMap = {
      'pure-jacob': 'Personal preference — no rec to add',
      'blocked-on-info': 'Blocked on info from you',
      'self-evident': 'Self-evident one-step task',
      'done': 'Already complete on action',
    };
    const reason = reasonMap[eligibility] || eligibility;
    return `<div class="ineligible">— ${escapeHtml(reason)}</div>`;
  }
  if (eligibility === 'eligible' && solution) {
    const statusBadge = status === 'fresh-pending-review' ? ' · NEW — review me'
                      : status === 'stale' ? ' · stale — re-validating'
                      : status === 'dirty' ? ' · task changed — refreshing'
                      : '';
    const conf = task.solution_confidence ? ` · confidence: ${escapeHtml(task.solution_confidence)}` : '';
    const footer = `generated ${fmtAgo(task.solution_generated_at)}${conf}`;
    let sourcesBlock = '';
    if (sources.length) {
      const items = sources.map(src => {
        if (typeof src === 'string') return `<li>${escapeHtml(src)}</li>`;
        if (src && src.url) return `<li><a href="${escapeHtml(src.url)}">${escapeHtml(src.label || src.url)}</a></li>`;
        return `<li>${escapeHtml(JSON.stringify(src))}</li>`;
      }).join('');
      sourcesBlock = `<div class="sources"><span class="sources-label">Sources:</span><ul>${items}</ul></div>`;
    }
    return `
      <div class="rec-header">▸ Recommendation<span class="status-badge">${escapeHtml(statusBadge)}</span></div>
      <div class="rec-body">${renderSolution(solution)}</div>
      ${sourcesBlock}
      <div class="footer">${escapeHtml(footer)}</div>
    `;
  }
  if (eligibility === 'eligible' && !solution) {
    const label = status === 'needs_review'
      ? '— Generation flagged for review (failed validation 3×)'
      : '— Pending generation (next scheduled run)';
    return `<div class="ineligible">${escapeHtml(label)}</div>`;
  }
  return `<div class="ineligible">— Not yet classified (next scheduled run)</div>`;
}

function renderTaskPage(task) {
  const id = escapeHtml(task.id);
  const rank = task.rank != null ? `r${escapeHtml(task.rank)}` : '';
  const title = escapeHtml(task.title || '(untitled)');
  const desc = task.desc ? `<div class="desc">${escapeHtml(task.desc)}</div>` : '';
  const recBody = renderRecBody(task);
  const questions = Array.isArray(task.solution_questions) ? task.solution_questions : [];

  const metaBits = [];
  if (task.deadline) metaBits.push(deadlineHtml(task));
  if (task.category) metaBits.push(`<span class="pill cat">${escapeHtml(task.category)}</span>`);
  if (task.timeEstimate) metaBits.push(`<span class="meta-bit">~${task.timeEstimate} min</span>`);
  const metaRow = metaBits.length ? `<div class="meta-row">${metaBits.join(' ')}</div>` : '';

  let questionsBlock = '';
  if (questions.length) {
    const items = questions.map(q => `<li>${escapeHtml(q)}</li>`).join('');
    questionsBlock = `<div class="questions"><span class="questions-label">Questions for you:</span><ul>${items}</ul></div>`;
  }

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${title} — recommendation</title>
<style>${css}</style>
</head>
<body>
  <div class="back-bar">← <a href="../check_in.html">Back to check-in</a></div>
  <h1 class="task-title"><span class="rank">${rank}</span><span class="task-id">[${id}]</span> ${title}</h1>
  ${metaRow}
  ${desc}
  ${recBody}
  ${questionsBlock}
</body>
</html>`;
}

// ─── main ──────────────────────────────────────────────────────────────────
const active = tasks
  .filter(t => t.status !== 'parked' && t.status !== 'done')
  .sort((a, b) => (a.rank || 999) - (b.rank || 999));

let written = 0;
const manifest = [];
const stats = { withRec: 0, ineligible: 0, pending: 0, unclassified: 0 };

for (const task of active) {
  const html = renderTaskPage(task);
  const outPath = path.join(recsDir, `rec_${task.id}.html`);
  fs.writeFileSync(outPath, html);
  manifest.push({
    id: task.id,
    title: task.title,
    rank: task.rank,
    eligibility: task.solution_eligibility,
    status: task.solution_status,
    has_solution: !!task.solution,
    file: `recs/rec_${task.id}.html`,
  });
  written++;

  if (task.solution_eligibility === 'eligible' && task.solution) stats.withRec++;
  else if (task.solution_eligibility && task.solution_eligibility !== 'eligible') stats.ineligible++;
  else if (task.solution_eligibility === 'eligible' && !task.solution) stats.pending++;
  else stats.unclassified++;
}

fs.writeFileSync(
  path.join(outputDir, 'rec_manifest.json'),
  JSON.stringify({ generated_at: today.toISOString(), today: todayStr, tasks: manifest }, null, 2)
);

console.log(`Wrote ${written} per-task recommendation pages → ${recsDir}`);
console.log(`  with rec:    ${stats.withRec}`);
console.log(`  pending:     ${stats.pending}`);
console.log(`  ineligible:  ${stats.ineligible}`);
console.log(`  unclassified:${stats.unclassified}`);
console.log(`Manifest → ${path.join(outputDir, 'rec_manifest.json')}`);
