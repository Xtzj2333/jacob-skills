// Task verbs library — Step 2 of the v3 build.
// Provides cancel / snooze / bump-rollover / done as small, atomic functions
// that read tasks_v3.json, mutate exactly one task, write back.
//
// Pure mutators: no side effects beyond the tasks file. Logging to
// state.recent_notes is the caller's job (the check-in script in Step 3).
//
// CLI:
//   node task_verbs.js cancel t053 "filed already in March"
//   node task_verbs.js snooze t014 2026-07-15
//   node task_verbs.js snooze t014 move_to_berkeley     # landmark name
//   node task_verbs.js snooze t014 null                  # clear snooze
//   node task_verbs.js bump-rollover t049
//   node task_verbs.js done t053

const fs = require('fs');
const path = require('path');

const SKILL_DIR = path.resolve(__dirname, '..');
const TASKS_PATH = path.join(__dirname, 'tasks_v3.json');
const STATE_PATH = path.join(SKILL_DIR, 'state_v3.json');

function today() {
  return new Date().toISOString().slice(0, 10);
}

function loadTasks() { return JSON.parse(fs.readFileSync(TASKS_PATH, 'utf8')); }
function saveTasks(tasks) { fs.writeFileSync(TASKS_PATH, JSON.stringify(tasks, null, 2) + '\n'); }
function loadState() { return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8')); }

function findTask(tasks, id) {
  const idx = tasks.findIndex(t => t.id === id);
  if (idx === -1) throw new Error(`Task ${id} not found in tasks_v3.json`);
  return { task: tasks[idx], idx };
}

function cancel(taskId, reason) {
  if (!reason || typeof reason !== 'string' || reason.trim().length === 0) {
    throw new Error('cancel requires a non-empty reason string (why is it being cancelled?)');
  }
  const tasks = loadTasks();
  const { task } = findTask(tasks, taskId);
  if (task.status === 'cancelled') {
    throw new Error(`${taskId} already cancelled — existing reason: "${task.cancel_reason}"`);
  }
  task.status = 'cancelled';
  task.cancel_reason = reason.trim();
  task.last_status_change = today();
  saveTasks(tasks);
  return { id: taskId, status: 'cancelled', cancel_reason: task.cancel_reason, last_status_change: task.last_status_change };
}

function isRealDate(s) {
  // Validates that s is a real calendar date in YYYY-MM-DD form.
  // Rejects "2026-13-45" (month 13, day 45) while accepting "2026-02-29" only in leap years.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return false;
  const [, y, mm, dd] = m.map(Number);
  const d = new Date(Date.UTC(y, mm - 1, dd));
  return d.getUTCFullYear() === y && d.getUTCMonth() === mm - 1 && d.getUTCDate() === dd;
}

function snooze(taskId, until) {
  // `until` can be: a "YYYY-MM-DD" date string, a landmark name from state.landmarks,
  // or null to clear an existing snooze.
  if (until !== null && typeof until !== 'string') {
    throw new Error('snooze "until" must be a YYYY-MM-DD date, a landmark name, or null');
  }
  const tasks = loadTasks();
  const { task } = findTask(tasks, taskId);
  if (until !== null) {
    const looksLikeDate = /^\d{4}-\d{2}-\d{2}$/.test(until);
    if (looksLikeDate && !isRealDate(until)) {
      throw new Error(`"${until}" is not a real calendar date (check month/day)`);
    }
    if (!looksLikeDate) {
      const state = loadState();
      const landmarks = state.landmarks ?? {};
      if (!(until in landmarks)) {
        const known = Object.keys(landmarks);
        const hint = known.length === 0
          ? 'state.landmarks is empty — set the landmark first, or pass a YYYY-MM-DD date.'
          : `known landmarks: ${known.join(', ')}`;
        throw new Error(`landmark "${until}" not found. ${hint}`);
      }
    }
  }
  task.snooze_until = until;
  task.last_status_change = today();
  saveTasks(tasks);
  return { id: taskId, snooze_until: until, last_status_change: task.last_status_change };
}

function bumpRollover(taskId) {
  const tasks = loadTasks();
  const { task } = findTask(tasks, taskId);
  // Rollover is *the absence of a status change* — by definition we do NOT
  // touch last_status_change here. The counter records how many check-ins
  // have listed this task without progress.
  task.rollover_count = (task.rollover_count ?? 0) + 1;
  saveTasks(tasks);
  return { id: taskId, rollover_count: task.rollover_count };
}

function done(taskId) {
  const tasks = loadTasks();
  const { task } = findTask(tasks, taskId);
  if (task.status === 'done') throw new Error(`${taskId} already done`);
  task.status = 'done';
  task.last_status_change = today();
  saveTasks(tasks);
  return { id: taskId, status: 'done', last_status_change: task.last_status_change };
}

const WORK_STATUSES = ['not_started', 'blocked', 'in_progress', 'completed'];
function setStatus(taskId, workStatus) {
  // Sets the Google-Tasks-style lifecycle state. "completed" also closes the
  // task (Completed = done). Idempotent — safe if the task is already done.
  if (!WORK_STATUSES.includes(workStatus)) {
    throw new Error(`setStatus: invalid status "${workStatus}" (use ${WORK_STATUSES.join(' | ')})`);
  }
  const tasks = loadTasks();
  const { task } = findTask(tasks, taskId);
  task.work_status = workStatus;
  task.last_status_change = today();
  if (workStatus === 'completed') {
    task.status = 'done';
  } else if (task.status === 'done') {
    // Re-opening a done task by moving it off "completed".
    task.status = 'open';
  }
  saveTasks(tasks);
  return { id: taskId, work_status: workStatus, status: task.status, last_status_change: task.last_status_change };
}

module.exports = { cancel, snooze, bumpRollover, done, setStatus, today, loadTasks, loadState };

if (require.main === module) {
  const [verb, taskId, ...rest] = process.argv.slice(2);
  if (!verb || !taskId) {
    console.error('Usage: node task_verbs.js <cancel|snooze|bump-rollover|done> <task_id> [arg]');
    process.exit(2);
  }
  try {
    let result;
    switch (verb) {
      case 'cancel':
        if (rest.length === 0) throw new Error('cancel requires a reason as a trailing argument');
        result = cancel(taskId, rest.join(' '));
        break;
      case 'snooze': {
        const raw = rest[0];
        const until = (raw === 'null' || raw === undefined) ? null : raw;
        result = snooze(taskId, until);
        break;
      }
      case 'bump-rollover': result = bumpRollover(taskId); break;
      case 'done':          result = done(taskId); break;
      case 'status':        result = setStatus(taskId, rest[0]); break;
      default: throw new Error(`unknown verb: ${verb} (use cancel | snooze | bump-rollover | done | status)`);
    }
    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
}
