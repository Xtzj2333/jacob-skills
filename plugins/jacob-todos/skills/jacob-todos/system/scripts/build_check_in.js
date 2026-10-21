// build_check_in.js — generates the interactive morning check-in HTML
// from tasks_v3.json + state_v3.json. Re-run whenever tasks or state change.
//
// Usage: node build_check_in.js
// Writes: ../check_in.html

const fs = require('fs');
const path = require('path');

const SCRIPT_DIR = __dirname;
const ROOT = path.resolve(SCRIPT_DIR, '..');
const TASKS_PATH = path.join(SCRIPT_DIR, 'tasks_v3.json');
const STATE_PATH = path.join(ROOT, 'state_v3.json');
const OUTPUT_PATH = path.join(ROOT, 'check_in.html');

const tasks = JSON.parse(fs.readFileSync(TASKS_PATH, 'utf8'));
const state = JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));

const today = new Date().toISOString().slice(0, 10);
// Build timestamp namespaces localStorage so that a regenerated HTML doesn't
// inherit the previous session's answers (those have already been processed
// by pickup_actions.js and applied to tasks_v3.json).
const BUILD_TS = new Date().toISOString().replace(/[:.]/g, '-');

function daysFrom(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr + 'T00:00:00Z');
  const t = new Date(today + 'T00:00:00Z');
  return Math.round((d - t) / 86400000);
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]);
}

function deadlinePill(task) {
  if (!task.deadline) return '';
  const days = daysFrom(task.deadline);
  let cls, label;
  if (days < 0)       { cls = 'overdue'; label = `${Math.abs(days)}d overdue`; }
  else if (days === 0){ cls = 'today';   label = 'TODAY'; }
  else if (days <= 3) { cls = 'urgent';  label = `+${days}d`; }
  else if (days <= 7) { cls = 'soon';    label = `+${days}d`; }
  else                { cls = 'far';     label = `+${days}d`; }
  return `<span class="dl-pill ${cls}"><span class="dl-date">⏰ ${task.deadline}</span><span class="dl-rel">${label}</span></span>`;
}

// Google-Tasks-style work-status control. Renders an empty wrapper carrying the
// current status; the page JS turns it into a clickable colored pill + dropdown.
// Statuses: not_started | blocked | in_progress | completed (Completed = done).
const WORK_STATUSES = ['not_started', 'blocked', 'in_progress', 'completed'];
function statusControl(task) {
  const st = WORK_STATUSES.includes(task.work_status) ? task.work_status : 'not_started';
  return `<span class="status-wrap" data-status="${st}" data-orig-status="${st}"></span>`;
}

// A task's organizational tags (optional `tags[]` array — e.g. project names,
// areas, contexts). Rendered as pills and used by the tag-filter bar.
function taskTags(task) {
  return Array.isArray(task.tags) ? [...new Set(task.tags.filter(Boolean))] : [];
}

function renderTask(task) {
  const id = task.id;
  const decisionId = `task-${id}`;
  const formName = `task-${id}`;
  const hasSubtasks = task.subtasks && task.subtasks.length > 0;
  const titleClass = task.deadline && daysFrom(task.deadline) < 0 ? 'task-title is-overdue' : 'task-title';
  const todayFlag = task.commitToday ? '<span class="pill today-pill">today</span>' : '';
  const cat = task.category ? `<span class="pill cat-${task.category}">${escapeHtml(task.category)}</span>` : '';
  const tagPills = taskTags(task).map(t => `<span class="pill tag-pill">#${escapeHtml(t)}</span>`).join('');
  const time = task.timeEstimate ? `<span class="meta-bit">~${task.timeEstimate} min</span>` : '';
  const desc = task.desc ? `<p class="task-desc">${escapeHtml(task.desc).replace(/\n/g, '<br>')}</p>` : '';

  // Bug fix 2026-05-15: only render INCOMPLETE subtasks. Done ones are noise
  // in the active check-in surface — they've already been processed.
  // Preserve original index (i) so the action payload still references the
  // correct subtask position in tasks_v3.json.
  const openSubtasks = hasSubtasks ? task.subtasks.map((s, i) => ({ ...s, _idx: i })).filter(s => !s.done) : [];
  const doneSubtaskCount = hasSubtasks ? task.subtasks.length - openSubtasks.length : 0;
  let subtasksBlock = '';
  if (openSubtasks.length > 0) {
    const completedNote = doneSubtaskCount > 0
      ? `<div class="subtasks-meta">${doneSubtaskCount} of ${task.subtasks.length} already done</div>`
      : '';
    subtasksBlock = `${completedNote}<div class="subtasks" data-decision-id="${decisionId}">${
      openSubtasks.map(s =>
        `<label class="subtask-row"><input type="checkbox" data-subtask="${s._idx}"><span>${escapeHtml(s.text)}</span></label>`
      ).join('')
    }</div>`;
  } else if (hasSubtasks && doneSubtaskCount === task.subtasks.length) {
    // All subtasks already done — the task should have been auto-closed by pickup_actions.
    // Show a quiet note rather than nothing, so this case is visible.
    subtasksBlock = `<div class="subtasks-meta">All ${doneSubtaskCount} subtasks done — pending parent close.</div>`;
  }

  // 2026-05-16: replaced inline <details><pre>solution</pre></details> with
  // a hyperlink to a per-task recommendation page (rendered by
  // build_per_task_recs.js). Rationale: rec content now renders as rich
  // HTML (headers, lists, tables, links) on its own page instead of
  // dense plain text behind a collapsible. Same gating as before — link
  // only shows when task.solution exists.
  const solution = task.solution
    ? `<div class="rec-link-wrap"><a class="rec-link" href="recs/rec_${id}.html" target="_blank" rel="noopener">View suggested plan →</a></div>`
    : '';

  // No "Done" radio anymore — "Completed" in the status dropdown marks a task
  // done (and subtask-bearing tasks auto-close when all subtasks are checked).
  // Cancel & Snooze remain as one-off actions.
  const radios =
    `<label><input type="radio" name="${formName}" value="cancel"><span class="opt-text">✗ Cancel</span></label>
        <label><input type="radio" name="${formName}" value="snooze"><span class="opt-text">⏸ Snooze</span></label>`;

  return `
  <details class="task-row" data-task-id="${id}" data-tags="${escapeHtml(taskTags(task).join(' '))}">
    <summary>
      <span class="task-summary-left">
        <span class="${titleClass}">${escapeHtml(task.title)}</span>
        ${todayFlag}
        <span class="answer-chip" id="chip-${decisionId}"></span>
      </span>
      <span class="task-summary-right">
        ${statusControl(task)}
        ${deadlinePill(task)}
      </span>
    </summary>
    <div class="task-body">
      <div class="task-meta-row">
        ${time}
        ${cat}
        ${tagPills}
      </div>
      ${desc}
      ${subtasksBlock}
      ${solution}
      <fieldset class="decision-form" data-decision-id="${decisionId}">
        <div class="options">
        ${radios}
        </div>
        <textarea placeholder="Comment" data-comment="${decisionId}"></textarea>
      </fieldset>
    </div>
  </details>`;
}

// ---- bucket the tasks ----
function isSnoozedPast(task) {
  if (!task.snooze_until) return false;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(task.snooze_until)) return false;  // landmark/unresolved → leave visible
  return task.snooze_until > today;
}

const active = tasks
  .filter(t => t.status !== 'done' && t.status !== 'cancelled' && !isSnoozedPast(t))
  .sort((a, b) => (a.rank || 999) - (b.rank || 999));

const todayBucket = active.filter(t =>
  t.commitToday || (t.deadline && daysFrom(t.deadline) <= 3)
);
const otherBucket = active.filter(t => !todayBucket.includes(t));

const stats = {
  total: active.length,
  today: todayBucket.length,
  overdue: active.filter(t => t.deadline && daysFrom(t.deadline) < 0).length,
};

// Distinct organizational tags across active tasks (for the filter bar).
const allTags = [...new Set(active.flatMap(taskTags))].sort();

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Morning check-in — ${today}</title>
<style>
  :root {
    --bg: #fafaf7; --fg: #1a1a1a; --muted: #666;
    --accent: #0a5; --warn: #a60; --info: #06a; --del: #b33;
    --code-bg: #f4f3ee;
    --pin-bg: #fff8d9;  --pin-bd: #d4a017;
    --rule-bg: #fdfcf6; --rule-bd: #e0d9b8;
  }
  html, body { background: var(--bg); color: var(--fg); }
  body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; max-width: 900px; margin: 0 auto; padding: 28px 36px 100px; line-height: 1.5; font-size: 15px; }
  h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
  h1 + p.meta { color: var(--muted); margin: 0 0 18px; font-size: 13.5px; }
  h2 { font-size: 19px; margin: 28px 0 6px; padding-bottom: 4px; border-bottom: 1px solid #e6e2d4; }
  h2 + p.sub { color: var(--muted); font-size: 13.5px; margin: 4px 0 14px; }
  code { background: var(--code-bg); padding: 1px 5px; border-radius: 3px; font-size: 13px; }

  .intro {
    background: #e2eef7; border-left: 4px solid var(--info);
    border-radius: 4px; padding: 10px 15px; margin: 14px 0 22px;
    font-size: 14px;
  }

  /* ---- task row (one-frog focus) ---- */
  .task-row {
    background: #fff; border: 1px solid #e0dac4; border-radius: 5px;
    margin: 6px 0; transition: box-shadow 0.15s;
  }
  .task-row[open] { box-shadow: 0 1px 5px rgba(0,0,0,0.08); }
  .task-row > summary {
    list-style: none; cursor: pointer; padding: 11px 16px;
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  }
  .task-row > summary::-webkit-details-marker { display: none; }
  .task-row > summary::before {
    content: "▸"; color: var(--muted); font-size: 12px; flex-shrink: 0;
  }
  .task-row[open] > summary::before { content: "▾"; }
  .task-row > summary:hover { background: #f8f6ec; }
  .task-summary-left { display: flex; align-items: center; gap: 10px; flex: 1; flex-wrap: wrap; min-width: 0; }
  .task-summary-right { flex-shrink: 0; display: flex; align-items: center; gap: 10px; }
  .task-title { font-weight: 600; font-size: 15.5px; }
  .task-title.is-overdue { color: var(--del); }

  /* ---- deadline pill (salient) ---- */
  .dl-pill {
    display: inline-flex; flex-direction: column; align-items: flex-end;
    padding: 5px 12px; border-radius: 6px;
    font-family: ui-monospace, Menlo, monospace; line-height: 1.2;
    min-width: 130px; text-align: right;
  }
  .dl-pill .dl-date { font-weight: 600; font-size: 14px; }
  .dl-pill .dl-rel { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.85; margin-top: 2px; }
  .dl-pill.overdue { background: #fbe4e4; color: #7a1f1f; border: 1px solid #c79090; }
  .dl-pill.today   { background: #fff4e0; color: #6b4d00; border: 1px solid #d4a017; }
  .dl-pill.urgent  { background: #fff4e0; color: #6b4d00; border: 1px solid #e0c060; }
  .dl-pill.soon    { background: #fff8d9; color: #6b4d00; border: 1px solid #e8d878; }
  .dl-pill.far     { background: #e6f4ea; color: #1a5928; border: 1px solid #a8d4b3; }
  .dl-pill.no-dl   { background: #f4f3ee; color: var(--muted); border: 1px solid #ddd; font-family: -apple-system, sans-serif; font-size: 12px; min-width: auto; padding: 4px 10px; }

  .pill {
    display: inline-block; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.5px;
    padding: 2px 7px; border-radius: 9px; background: #eee; color: #555; font-weight: 600;
  }
  .pill.today-pill { background: #fbe4e4; color: #7a1f1f; }
  .pill.cat-research  { background: #e2eef7; color: #1a4d6e; }
  .pill.cat-personal  { background: #f4eafa; color: #4a2a6e; }
  .pill.cat-logistics { background: #fff4e0; color: #6b4d00; }
  .pill.cat-berkeley  { background: #e6f4ea; color: #1a5928; }
  .pill.cat-health    { background: #fbe4e4; color: #7a1f1f; }
  .pill.cat-leisure   { background: #e2f7f0; color: #1a5e57; }
  .pill.cat-meta      { background: #f0f0f0; color: #555; }
  .pill.tag-pill      { background: #d8efe9; color: #155e54; }

  /* ---- work-status dropdown (Google-Tasks style) ---- */
  .status-wrap { position: relative; flex: none; }
  .status-pill {
    display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600;
    padding: 5px 11px; border-radius: 14px; border: 1px solid transparent; cursor: pointer;
    font-family: inherit; white-space: nowrap; transition: filter .12s, box-shadow .12s;
  }
  .status-pill:hover { filter: brightness(.97); }
  .status-pill:focus-visible { outline: none; box-shadow: 0 0 0 2px #4a90d9; }
  .status-pill .caret2 { font-size: 9px; opacity: .65; }
  .st-not_started { background: #e8eaed; color: #3c4043; }
  .st-blocked     { background: #fad2cf; color: #b3261e; }
  .st-in_progress { background: #feefc3; color: #7a5900; }
  .st-completed   { background: #ceead6; color: #137333; }
  .status-menu {
    position: absolute; top: calc(100% + 6px); right: 0; z-index: 200; background: #fff;
    border: 1px solid #dadce0; border-radius: 10px; box-shadow: 0 6px 22px rgba(0,0,0,.16);
    padding: 8px; min-width: 196px; display: none;
  }
  .status-menu.open { display: block; }
  .status-menu .mi { display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: 7px; cursor: pointer; }
  .status-menu .mi:hover { background: #f1f3f4; }
  .status-menu .mi .check { width: 16px; flex: none; color: #1a1a1a; font-weight: 700; font-size: 14px; text-align: center; visibility: hidden; }
  .status-menu .mi.sel .check { visibility: visible; }
  .status-menu .mi .opt { font-size: 13px; font-weight: 600; padding: 4px 11px; border-radius: 13px; }

  /* ---- tag filter bar ---- */
  .tag-filter { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 10px 0 18px; }
  .tag-filter .tf-label { color: var(--muted); font-size: 13px; margin-right: 4px; }
  .tf-chip { font-size: 12px; padding: 4px 11px; border: 1px solid #cdbf86; background: #fff;
    border-radius: 14px; cursor: pointer; color: #5a4a1a; font-family: inherit; }
  .tf-chip:hover { background: #fffae0; }
  .tf-chip.active { background: var(--accent); color: #fff; border-color: var(--accent); }

  .answer-chip {
    font-size: 11px; padding: 2px 8px; border-radius: 9px;
    text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; display: none;
  }
  .answer-chip.has-answer { display: inline-block; }
  .answer-chip.choice-done   { background: #d4ebd6; color: #2a5d33; }
  .answer-chip.choice-cancel { background: #fbe4e4; color: #7a1f1f; }
  .answer-chip.choice-snooze { background: #fff4e0; color: #6b4d00; }
  .answer-chip.choice-comment-only { background: #e2eef7; color: #1a4d6e; }
  .answer-chip.choice-subtasks { background: #d4ebd6; color: #2a5d33; }

  .task-body { padding: 4px 18px 16px 36px; border-top: 1px dashed #e0dac4; }
  .task-meta-row { display: flex; gap: 10px; align-items: center; margin: 10px 0; flex-wrap: wrap; }
  .meta-bit { color: var(--muted); font-size: 13px; }
  .task-desc { background: #fafaf2; padding: 8px 12px; border-radius: 4px; font-size: 14px; margin: 8px 0; color: #444; }

  /* ---- subtasks (interactive checkboxes) ---- */
  .subtasks-meta { color: var(--muted); font-size: 12.5px; font-style: italic; margin: 8px 0 4px; }
  .subtasks { margin: 6px 0 10px; display: flex; flex-direction: column; gap: 4px; }
  .subtask-row {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 6px 10px; border: 1px solid #e8e3d0; border-radius: 3px;
    background: #fff; cursor: pointer; font-size: 14px;
    transition: background 0.12s;
  }
  .subtask-row:hover { background: #f8f6ec; }
  .subtask-row input[type="checkbox"] { margin-top: 3px; flex-shrink: 0; }
  .subtask-row:has(input:checked) { background: #e6f4ea; border-color: #a8d4b3; }
  .subtask-row:has(input:checked) span { text-decoration: line-through; color: var(--muted); }

  .solution-block { margin: 10px 0; }
  .solution-block summary { cursor: pointer; color: var(--info); font-size: 13px; padding: 4px 0; }
  .solution-block pre {
    background: var(--code-bg); padding: 12px 14px; border-radius: 4px;
    font-size: 13px; white-space: pre-wrap; max-height: 380px; overflow-y: auto;
    font-family: ui-monospace, Menlo, monospace;
  }

  /* 2026-05-16: hyperlink to per-task recommendation page (recs/rec_tNNN.html) */
  .rec-link-wrap { margin: 10px 0; }
  .rec-link {
    display: inline-block; color: var(--info); text-decoration: none;
    font-size: 13.5px; padding: 6px 12px;
    background: #eef4fa; border: 1px solid #c9dbeb; border-radius: 4px;
    font-weight: 500;
  }
  .rec-link:hover { background: #dceaf5; text-decoration: underline; }

  /* ---- form pattern (slimmed) ---- */
  .decision-form {
    border: 1px solid #d4cba5; background: #fdfcf6;
    border-radius: 6px; padding: 12px 16px; margin: 14px 0 0;
  }
  .decision-form .options { display: flex; flex-direction: column; gap: 5px; margin: 0 0 8px; }
  .decision-form .options label {
    display: flex; align-items: center; gap: 8px;
    padding: 9px 14px; border: 1px solid #ddd; border-radius: 4px;
    cursor: pointer; background: white; transition: background 0.12s, border-color 0.12s;
    font-size: 14px; user-select: none; -webkit-user-select: none;
  }
  .decision-form .options label:hover { background: #f6f3ea; }
  .decision-form .options label:active { background: #ecead8; }
  .decision-form .options label:has(input:checked) {
    background: #e6f4ea; border-color: #4a8e54;
  }
  .decision-form .options label > span.opt-text { flex: 1; pointer-events: none; }
  .decision-form .options input[type="radio"] { margin: 0; pointer-events: none; }
  .decision-form textarea {
    width: 100%; min-height: 44px; padding: 7px 9px; margin-top: 2px;
    border: 1px solid #ccc; border-radius: 4px; font-family: inherit; font-size: 13.5px;
    resize: vertical; box-sizing: border-box;
  }

  /* ---- sticky toolbar ---- */
  .form-toolbar {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #fff8d9; border-top: 2px solid #d4a017;
    padding: 12px 28px; display: flex; gap: 10px; align-items: center;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.08); z-index: 100;
  }
  .form-toolbar .progress { color: #5a3e00; font-size: 14px; margin-right: auto; font-weight: 500; }
  .form-toolbar button {
    padding: 8px 16px; font-size: 14px; border: 1px solid #d4a017;
    background: white; border-radius: 4px; cursor: pointer; font-family: inherit;
  }
  .form-toolbar button:hover { background: #fffae0; }
  .form-toolbar button[data-form-action="copy-all"] { background: #0a5; color: white; border-color: #0a5; }
  .form-toolbar button[data-form-action="copy-all"]:hover { background: #097a44; }
  .form-toolbar button[data-form-action="clear-all"] { color: var(--del); border-color: #c79090; }
</style>
</head>
<body>

<h1>Morning check-in &mdash; ${today}</h1>
<p class="meta">${stats.total} active &middot; ${stats.today} for today &middot; ${stats.overdue} overdue</p>

<div class="intro">
  Click a task. Pick an option or type a comment. Hit <strong>Download JSON</strong> when done, then say <strong>"pick up my answers"</strong> in chat.
</div>

${allTags.length ? `<div class="tag-filter" id="tag-filter">
  <span class="tf-label">Filter by tag:</span>
  <button type="button" class="tf-chip active" data-tag="__all__">All</button>
  ${allTags.map(t => `<button type="button" class="tf-chip" data-tag="${escapeHtml(t)}">#${escapeHtml(t)}</button>`).join('')}
</div>` : ''}

<h2 id="today">📌 For today &mdash; ${todayBucket.length}</h2>
<p class="sub">Committed today or due in the next 3 days.</p>
${todayBucket.map(renderTask).join('\n')}

<h2 id="other">📋 Everything else &mdash; ${otherBucket.length}</h2>
<p class="sub">By priority. Optional today.</p>
${otherBucket.map(renderTask).join('\n')}

<div class="form-toolbar">
  <span class="progress" id="progress">0 / ${active.length} answered</span>
  <button type="button" data-form-action="copy-all">Copy all responses</button>
  <button type="button" data-form-action="download-json">Download JSON</button>
  <button type="button" data-form-action="clear-all">Clear all</button>
</div>

<script>
(function() {
  // Namespaced by build timestamp so a regenerated check_in.html doesn't
  // resurrect the previous session's answers (those have already been
  // processed by pickup_actions.js).
  const BUILD_TS = '${BUILD_TS}';
  const STORAGE_KEY = 'todo_checkin_responses_v3_' + BUILD_TS;
  const STORAGE_PREFIX = 'todo_checkin_responses_v3_';

  // On load, clear stale keys from prior builds.
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.startsWith(STORAGE_PREFIX) && k !== STORAGE_KEY) {
        localStorage.removeItem(k);
      }
      // Also clean up the very old v2 key from the previous schema.
      if (k === 'todo_checkin_responses_v2') localStorage.removeItem(k);
    }
  } catch (e) { /* private mode etc. */ }

  function load() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch { return {}; } }
  function save(s) { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch (e) { console.warn(e); } }

  function collectTaskState(taskRow) {
    const decisionId = taskRow.querySelector('.decision-form').dataset.decisionId;
    const taskId = taskRow.dataset.taskId;
    const radio = taskRow.querySelector('.decision-form input[type="radio"]:checked');
    const ta = taskRow.querySelector('.decision-form textarea');
    const subtaskBoxes = taskRow.querySelectorAll('.subtasks input[type="checkbox"]');
    const subtasksChecked = [];
    subtaskBoxes.forEach((cb, i) => { if (cb.checked) subtasksChecked.push(parseInt(cb.dataset.subtask, 10)); });
    const sw = taskRow.querySelector('.status-wrap');
    const status = sw ? sw.dataset.status : null;
    const origStatus = sw ? sw.dataset.origStatus : null;
    return {
      decisionId,
      task_id: taskId,
      choice: radio?.value || null,
      comment: ta?.value?.trim() || '',
      hasSubtasks: subtaskBoxes.length > 0,
      subtasksChecked,
      status,
      statusChanged: !!(sw && status !== origStatus)
    };
  }

  function readAll() {
    const state = {};
    document.querySelectorAll('.task-row').forEach(row => {
      const s = collectTaskState(row);
      state[s.decisionId] = s;
    });
    return state;
  }

  function restoreAll() {
    const state = load();
    Object.entries(state).forEach(([id, v]) => {
      const form = document.querySelector(\`.decision-form[data-decision-id="\${id}"]\`);
      if (!form) return;
      const row = form.closest('.task-row');
      if (v.choice) { const r = form.querySelector(\`input[type="radio"][value="\${v.choice}"]\`); if (r) r.checked = true; }
      if (v.comment) { const ta = form.querySelector('textarea'); if (ta) ta.value = v.comment; }
      if (v.subtasksChecked && v.subtasksChecked.length) {
        v.subtasksChecked.forEach(i => {
          const cb = row.querySelector(\`.subtasks input[data-subtask="\${i}"]\`);
          if (cb) cb.checked = true;
        });
      }
      if (v.status) { const sw = row.querySelector('.status-wrap'); if (sw) sw.dataset.status = v.status; }
      updateChip(id);
      // auto-expand any task that has an answer
      const hasAnything = v.choice || v.comment || (v.subtasksChecked && v.subtasksChecked.length) || v.status;
      if (hasAnything) row.open = true;
    });
  }

  function updateChip(decisionId) {
    const chip = document.getElementById('chip-' + decisionId);
    const row = document.querySelector(\`.task-row [data-decision-id="\${decisionId}"]\`)?.closest('.task-row');
    if (!chip || !row) return;
    const s = collectTaskState(row);
    chip.className = 'answer-chip';
    chip.textContent = '';
    if (s.choice === 'done')        { chip.classList.add('has-answer','choice-done');   chip.textContent = '✓ done'; }
    else if (s.choice === 'cancel') { chip.classList.add('has-answer','choice-cancel'); chip.textContent = '✗ cancel'; }
    else if (s.choice === 'snooze') { chip.classList.add('has-answer','choice-snooze'); chip.textContent = '⏸ snooze'; }
    else if (s.hasSubtasks && s.subtasksChecked.length > 0) {
      chip.classList.add('has-answer','choice-subtasks');
      const total = row.querySelectorAll('.subtasks input').length;
      chip.textContent = \`\${s.subtasksChecked.length}/\${total} subtasks\`;
    }
    else if (s.comment) { chip.classList.add('has-answer','choice-comment-only'); chip.textContent = '💬 comment'; }
  }

  function updateProgress() {
    const state = readAll();
    const total = Object.keys(state).length;
    const answered = Object.values(state).filter(v =>
      v.choice || v.comment || (v.subtasksChecked && v.subtasksChecked.length) || v.statusChanged
    ).length;
    const el = document.getElementById('progress');
    if (el) el.textContent = \`\${answered} / \${total} answered\`;
  }

  function isEmptyState(s) {
    return !s.choice && !s.comment && !(s.subtasksChecked && s.subtasksChecked.length) && !s.statusChanged;
  }

  function persistRow(row) {
    const s = collectTaskState(row);
    const state = load();
    // Single organizing principle: keep only what's been answered.
    // Empty entries don't survive — same rule as Copy markdown and Download JSON.
    if (isEmptyState(s)) delete state[s.decisionId];
    else state[s.decisionId] = s;
    save(state);
    updateChip(s.decisionId);
    updateProgress();
  }

  function showToast(msg, color) {
    document.querySelectorAll('.form-toast').forEach(t => t.remove());
    const t = document.createElement('div');
    t.className = 'form-toast';
    t.textContent = msg;
    t.style.cssText = \`position:fixed; bottom:90px; right:24px; padding:10px 18px;
      background:\${color || '#0a5'}; color:white; border-radius:6px; z-index:99999;
      font-family:-apple-system, sans-serif; font-size:14px;
      box-shadow:0 4px 12px rgba(0,0,0,0.2);\`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2400);
  }

  function buildActionsPayload() {
    const state = readAll();
    const actions = [];
    Object.values(state).forEach(v => {
      const hasSubtaskActivity = v.hasSubtasks && v.subtasksChecked.length > 0;
      // Cancel / Snooze are terminal one-offs — emit only that, comment as its arg.
      if (v.choice === 'cancel') { const a = { task_id: v.task_id, verb: 'cancel' }; if (v.comment) a.reason = v.comment; actions.push(a); return; }
      if (v.choice === 'snooze') { const a = { task_id: v.task_id, verb: 'snooze' }; if (v.comment) a.until = v.comment; actions.push(a); return; }
      // Otherwise status change / subtasks / comment can co-occur — emit each.
      if (hasSubtaskActivity) actions.push({ task_id: v.task_id, verb: 'subtask_update', subtasks_checked: v.subtasksChecked });
      if (v.statusChanged)    actions.push({ task_id: v.task_id, verb: 'status', status: v.status });
      if (v.comment)          actions.push({ task_id: v.task_id, verb: 'comment', comment: v.comment });
    });
    return actions;
  }

  function copyAll() {
    const actions = buildActionsPayload();
    if (actions.length === 0) { showToast('No answers to copy yet', '#a60'); return; }
    let md = \`# Check-in answers for \${new Date().toISOString().slice(0,10)}\\n\\n\`;
    actions.forEach(a => {
      md += \`- **\${a.task_id}** — \${a.verb}\`;
      if (a.status) md += \` (status: \${a.status})\`;
      if (a.reason) md += \` (reason: \${a.reason})\`;
      if (a.until)  md += \` (until: \${a.until})\`;
      if (a.comment) md += \` — \${a.comment}\`;
      if (a.subtasks_checked) md += \` [subtasks: \${a.subtasks_checked.join(', ')}]\`;
      md += '\\n';
    });
    navigator.clipboard.writeText(md)
      .then(() => showToast(\`Copied \${actions.length} action\${actions.length === 1 ? '' : 's'}\`))
      .catch(err => showToast('Copy failed: ' + err.message, '#b33'));
  }

  function downloadJSON() {
    const actions = buildActionsPayload();
    if (actions.length === 0) { showToast('No answers to download yet', '#a60'); return; }
    const payload = {
      generated_at: new Date().toISOString(),
      checkin_date: '${today}',
      actions: actions
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = \`todo_actions_\${new Date().toISOString().slice(0,10)}.json\`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 500);
    showToast(\`Downloaded \${actions.length} action\${actions.length === 1 ? '' : 's'} to Downloads\`);
  }

  function clearAll() {
    if (!confirm('Clear all answers on this page?')) return;
    document.querySelectorAll('.decision-form input[type="radio"]').forEach(r => { r.checked = false; r._lastChecked = false; });
    document.querySelectorAll('.decision-form textarea').forEach(t => t.value = '');
    document.querySelectorAll('.status-wrap').forEach(sw => { sw.dataset.status = sw.dataset.origStatus; });
    renderStatusControls();
    // NOTE: subtask checkboxes are NOT cleared by Clear-all because their initial state
    // comes from tasks_v3.json (some may have been done previously). Click each one to toggle.
    document.querySelectorAll('.answer-chip').forEach(c => { c.className = 'answer-chip'; c.textContent = ''; });
    save({}); updateProgress();
    // Re-update chips to reflect any pre-checked subtasks
    document.querySelectorAll('.task-row').forEach(row => {
      const dec = row.querySelector('.decision-form')?.dataset.decisionId;
      if (dec) updateChip(dec);
    });
    showToast('Cleared all answers');
  }

  function wire() {
    // Whole-label click → toggle radio. Radio + inner span are pointer-events:none,
    // so this handler is the *only* click path for the radios — no double-firing.
    document.querySelectorAll('.decision-form .options label').forEach(label => {
      const radio = label.querySelector('input[type="radio"]');
      if (!radio) return;
      label.addEventListener('click', function(e) {
        e.preventDefault();
        const wasChecked = radio.checked;
        // Uncheck all siblings in the same name group
        document.querySelectorAll(\`input[type="radio"][name="\${radio.name}"]\`).forEach(r => { r.checked = false; });
        // If it WASN'T already checked, check it. If it was, leave all unchecked (toggle-off).
        radio.checked = !wasChecked;
        persistRow(label.closest('.task-row'));
      });
    });
    // Textareas
    document.querySelectorAll('.decision-form textarea').forEach(ta => {
      ta.addEventListener('input', function() { persistRow(this.closest('.task-row')); });
    });
    // Subtask checkboxes
    document.querySelectorAll('.subtasks input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', function() { persistRow(this.closest('.task-row')); });
    });
    // Toolbar
    document.querySelectorAll('[data-form-action]').forEach(btn => {
      const a = btn.dataset.formAction;
      btn.addEventListener('click', () => {
        if (a === 'copy-all') copyAll();
        else if (a === 'download-json') downloadJSON();
        else if (a === 'clear-all') clearAll();
      });
    });
  }

  // ---- work-status dropdown (Google-Tasks style) ----
  const STATUSES = [
    { key: 'not_started', label: 'Not Started' },
    { key: 'blocked',     label: 'Blocked'     },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'completed',   label: 'Completed'   }
  ];
  function statusLabel(key) { const s = STATUSES.find(x => x.key === key); return s ? s.label : 'Not Started'; }
  function closeStatusMenus(except) {
    document.querySelectorAll('.status-menu.open').forEach(m => { if (m !== except) m.classList.remove('open'); });
  }
  function renderStatusControl(wrap) {
    const key = wrap.dataset.status || 'not_started';
    wrap.innerHTML = '';
    const pill = document.createElement('button');
    pill.type = 'button';
    pill.className = 'status-pill st-' + key;
    pill.innerHTML = '<span class="lbl">' + statusLabel(key) + '</span><span class="caret2">▾</span>';
    const menu = document.createElement('div');
    menu.className = 'status-menu';
    STATUSES.forEach(s => {
      const mi = document.createElement('div');
      mi.className = 'mi' + (s.key === key ? ' sel' : '');
      mi.innerHTML = '<span class="check">✓</span><span class="opt st-' + s.key + '">' + s.label + '</span>';
      mi.addEventListener('click', function(e) {
        e.preventDefault(); e.stopPropagation();
        wrap.dataset.status = s.key;
        renderStatusControl(wrap);
        persistRow(wrap.closest('.task-row'));
        closeStatusMenus(null);
      });
      menu.appendChild(mi);
    });
    pill.addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation();
      const willOpen = !menu.classList.contains('open');
      closeStatusMenus(menu);
      menu.classList.toggle('open', willOpen);
    });
    menu.addEventListener('click', function(e) { e.stopPropagation(); });
    wrap.appendChild(pill);
    wrap.appendChild(menu);
  }
  function renderStatusControls() {
    document.querySelectorAll('.status-wrap').forEach(renderStatusControl);
  }

  function init() {
    restoreAll(); renderStatusControls(); wire(); updateProgress();
    document.addEventListener('click', () => closeStatusMenus(null));
    // Initial chip render for any pre-checked subtasks (from tasks_v3.json done states)
    document.querySelectorAll('.task-row').forEach(row => {
      const dec = row.querySelector('.decision-form')?.dataset.decisionId;
      if (dec) updateChip(dec);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
</script>

<script>
/* Tag filter: toggle task visibility by tag. Multi-select; "All" resets. */
(function() {
  const chips = Array.from(document.querySelectorAll('.tf-chip'));
  if (!chips.length) return;
  let active = new Set(['__all__']);
  function apply() {
    const all = active.has('__all__');
    document.querySelectorAll('.task-row').forEach(r => {
      const tags = (r.getAttribute('data-tags') || '').split(' ').filter(Boolean);
      r.style.display = (all || tags.some(t => active.has(t))) ? '' : 'none';
    });
  }
  chips.forEach(c => c.addEventListener('click', () => {
    const t = c.dataset.tag;
    if (t === '__all__') { active = new Set(['__all__']); }
    else {
      active.delete('__all__');
      if (active.has(t)) active.delete(t); else active.add(t);
      if (active.size === 0) active.add('__all__');
    }
    chips.forEach(x => {
      const xt = x.dataset.tag;
      x.classList.toggle('active', active.has('__all__') ? (xt === '__all__') : active.has(xt));
    });
    apply();
  }));
})();
</script>
</body>
</html>`;

fs.writeFileSync(OUTPUT_PATH, html);
console.log(`Wrote ${OUTPUT_PATH}`);
console.log(`  Active tasks: ${stats.total}`);
console.log(`  For today:    ${stats.today}`);
console.log(`  Overdue:      ${stats.overdue}`);
