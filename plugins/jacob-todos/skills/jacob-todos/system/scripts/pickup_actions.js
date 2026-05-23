// pickup_actions.js — reads the newest todo_actions_*.json from ~/Downloads,
// applies each action against tasks_v3.json, then moves the source file
// into scripts/processed_actions/ so ~/Downloads doesn't pile up.
//
// Usage:
//   node pickup_actions.js               # finds newest todo_actions_*.json in ~/Downloads
//   node pickup_actions.js path/to.json  # explicit file
//
// Actions schema (per item in payload.actions):
//   { task_id, verb: 'done'|'cancel'|'snooze'|'comment'|'subtask_update',
//     reason?, until?, comment?, subtasks_checked?: [indices] }
//
// "until" for snooze can be: YYYY-MM-DD, a landmark in state_v3.json,
// or a small set of natural phrases (tomorrow / next monday / +N days / etc.).
// Anything else is recorded under needs_review and the snooze is skipped.

const fs = require('fs');
const path = require('path');
const os = require('os');

const verbs = require('./task_verbs');

const SCRIPT_DIR = __dirname;
const SKILL_DIR = path.resolve(SCRIPT_DIR, '..');
const TASKS_PATH = path.join(SCRIPT_DIR, 'tasks_v3.json');
const STATE_PATH = path.join(SKILL_DIR, 'state_v3.json');
const PROCESSED_DIR = path.join(SCRIPT_DIR, 'processed_actions');
const DOWNLOADS_DIR = path.join(os.homedir(), 'Downloads');

const WEEKDAYS = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday'];

function todayISO() { return new Date().toISOString().slice(0,10); }
function tsSuffix() {
  const d = new Date();
  return d.toISOString().replace(/[:T]/g,'-').slice(0,19);
}

function findNewestActionsFile() {
  if (!fs.existsSync(DOWNLOADS_DIR)) {
    throw new Error(`Downloads dir not found: ${DOWNLOADS_DIR}`);
  }
  const files = fs.readdirSync(DOWNLOADS_DIR)
    .filter(f => /^todo_actions_.*\.json$/.test(f))
    .map(f => ({ name: f, full: path.join(DOWNLOADS_DIR, f), mtime: fs.statSync(path.join(DOWNLOADS_DIR, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  if (files.length === 0) {
    throw new Error(`No todo_actions_*.json files in ${DOWNLOADS_DIR}`);
  }
  return files[0].full;
}

function parseUntil(rawUntil) {
  // Returns { kind: 'date', value: 'YYYY-MM-DD' } | { kind: 'landmark', value }
  //       | { kind: 'unresolved', original }
  if (!rawUntil || typeof rawUntil !== 'string') return { kind: 'unresolved', original: rawUntil };
  const s = rawUntil.trim().toLowerCase();

  // YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return { kind: 'date', value: s };

  // landmark passthrough — let task_verbs.snooze validate
  const state = verbs.loadState();
  if (state.landmarks && s in state.landmarks) return { kind: 'landmark', value: s };

  const today = new Date();
  today.setUTCHours(0,0,0,0);
  const addDays = n => {
    const d = new Date(today); d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0,10);
  };

  // "tomorrow"
  if (s === 'tomorrow') return { kind: 'date', value: addDays(1) };
  // "next week"
  if (s === 'next week') return { kind: 'date', value: addDays(7) };
  // "+N days" / "in N days" / "in N day"
  let m = s.match(/^(?:\+|in\s+)(\d{1,3})\s*days?$/);
  if (m) return { kind: 'date', value: addDays(parseInt(m[1], 10)) };
  // "next monday" / "next tuesday" / ... — "come back next tuesday" also matches via the
  // contains check below as a fallback
  m = s.match(/(?:^|\b)(?:next\s+)?(sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b/);
  if (m) {
    const target = WEEKDAYS.indexOf(m[1]);
    const todayIdx = today.getUTCDay();
    let delta = target - todayIdx;
    if (delta <= 0 || /next\s+/.test(s)) delta += 7;     // "next <day>" or same-day → next week
    if (delta === 0) delta = 7;
    return { kind: 'date', value: addDays(delta) };
  }

  return { kind: 'unresolved', original: rawUntil };
}

function ensureDir(p) { if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true }); }

function applyComment(taskId, commentText) {
  const tasks = JSON.parse(fs.readFileSync(TASKS_PATH, 'utf8'));
  const idx = tasks.findIndex(t => t.id === taskId);
  if (idx === -1) throw new Error(`Task ${taskId} not found`);
  const task = tasks[idx];
  task.user_comments = task.user_comments || [];
  task.user_comments.push({ date: todayISO(), text: commentText });
  fs.writeFileSync(TASKS_PATH, JSON.stringify(tasks, null, 2) + '\n');
}

function applySubtaskUpdate(taskId, checkedIndices) {
  // `checkedIndices` is a DELTA — the indices of newly-completed subtasks.
  // The check-in form only renders INCOMPLETE subtasks (see build_check_in.js
  // line ~64: `filter(s => !s.done)`), so a submitted list of [0] means
  // "subtask 0 is now done", not "ONLY subtask 0 should be done".
  // Overwriting with the submitted set would un-check anything that was
  // already done before this round. Union-only is correct given the form
  // design. (Origin: 2026-05-22 — caught t009 housing+visa and t054 indices
  // 0+1 would have been incorrectly un-checked.)
  // If a future workflow needs to un-check subtasks, add a separate verb;
  // don't change the union semantics here.
  const tasks = JSON.parse(fs.readFileSync(TASKS_PATH, 'utf8'));
  const idx = tasks.findIndex(t => t.id === taskId);
  if (idx === -1) throw new Error(`Task ${taskId} not found`);
  const task = tasks[idx];
  if (!Array.isArray(task.subtasks)) throw new Error(`Task ${taskId} has no subtasks`);
  const newlyChecked = new Set(checkedIndices);
  const previouslyDone = task.subtasks.map(s => !!s.done);
  task.subtasks.forEach((sub, i) => {
    if (newlyChecked.has(i)) sub.done = true;
    // already-done subtasks stay done
  });
  fs.writeFileSync(TASKS_PATH, JSON.stringify(tasks, null, 2) + '\n');
  const allDone = task.subtasks.every(s => s.done);
  const newlyDoneCount = task.subtasks.filter((s, i) => s.done && !previouslyDone[i]).length;
  return {
    allDone,
    total: task.subtasks.length,
    done: task.subtasks.filter(s => s.done).length,
    newly_done: newlyDoneCount,
  };
}

function appendStateNote(summary) {
  const state = JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
  state.recent_notes = state.recent_notes || [];
  state.recent_notes.unshift({ date: todayISO(), summary });
  state.recent_notes = state.recent_notes.slice(0, 20);
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + '\n');
}

function main() {
  const arg = process.argv[2];
  const src = arg ? path.resolve(arg) : findNewestActionsFile();
  if (!fs.existsSync(src)) throw new Error(`Source not found: ${src}`);

  const payload = JSON.parse(fs.readFileSync(src, 'utf8'));
  if (!Array.isArray(payload.actions)) throw new Error(`Bad payload — expected { actions: [...] }`);

  const results = { applied: [], skipped: [], needs_review: [] };

  for (const action of payload.actions) {
    const { task_id, verb } = action;
    try {
      if (verb === 'done') {
        verbs.done(task_id);
        results.applied.push({ task_id, verb: 'done' });
      } else if (verb === 'cancel') {
        const reason = action.reason || action.comment || '(no reason given)';
        verbs.cancel(task_id, reason);
        results.applied.push({ task_id, verb: 'cancel', reason });
      } else if (verb === 'snooze') {
        const parsed = parseUntil(action.until || '');
        if (parsed.kind === 'unresolved') {
          results.needs_review.push({ task_id, verb: 'snooze', reason: `could not parse until="${action.until}"` });
        } else {
          verbs.snooze(task_id, parsed.value);
          results.applied.push({ task_id, verb: 'snooze', until: parsed.value, resolved_from: action.until });
        }
      } else if (verb === 'comment') {
        applyComment(task_id, action.comment || '');
        results.applied.push({ task_id, verb: 'comment', text: action.comment });
      } else if (verb === 'subtask_update') {
        const r = applySubtaskUpdate(task_id, action.subtasks_checked || []);
        results.applied.push({ task_id, verb: 'subtask_update', ...r });
        if (r.allDone) {
          try { verbs.done(task_id); results.applied.push({ task_id, verb: 'auto_done_via_subtasks' }); }
          catch (e) { /* may already be done */ }
        }
      } else {
        results.skipped.push({ task_id, verb, reason: `unknown verb: ${verb}` });
      }
    } catch (e) {
      results.needs_review.push({ task_id, verb, reason: e.message });
    }
  }

  // Append a recent_notes summary
  const summary = [
    `Check-in pickup ${todayISO()}: ${results.applied.length} applied`,
    results.needs_review.length ? `${results.needs_review.length} need review` : null,
    results.skipped.length ? `${results.skipped.length} skipped` : null,
  ].filter(Boolean).join(' · ');
  appendStateNote(summary + ' — source: ' + path.basename(src));

  // Move source out of Downloads
  ensureDir(PROCESSED_DIR);
  const moved = path.join(PROCESSED_DIR, `${path.basename(src, '.json')}__processed_${tsSuffix()}.json`);
  fs.renameSync(src, moved);

  // Print report
  console.log('Source:', src);
  console.log('Moved to:', moved);
  console.log('Applied:', results.applied.length);
  results.applied.forEach(r => console.log('  ✓', JSON.stringify(r)));
  if (results.needs_review.length) {
    console.log('Needs review:', results.needs_review.length);
    results.needs_review.forEach(r => console.log('  ?', JSON.stringify(r)));
  }
  if (results.skipped.length) {
    console.log('Skipped:', results.skipped.length);
    results.skipped.forEach(r => console.log('  -', JSON.stringify(r)));
  }
}

if (require.main === module) {
  try { main(); }
  catch (e) { console.error('ERROR:', e.message); process.exit(1); }
}

module.exports = { parseUntil, findNewestActionsFile };
