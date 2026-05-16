// Reference implementation for the decision-forms-html skill.
// Drop once at the end of <body>. Adapt aesthetics freely; behavior must match.
//
// Contract (see decision-forms-html/SKILL.md for full rationale):
// - Radios are clickable-to-uncheck (mousedown + click handlers track _lastChecked)
// - localStorage persists selections + free-text across reloads
// - Sticky toolbar exposes copy-all (Markdown), download-json, clear-all
// - Per-question Clear button as discoverable fallback
// - Absorbed-content cleanup: when relocating user text out of a fieldset,
//   wipe that decision-id from storage gated by a render-version key
// - Do NOT swap to Alpine.js — Alpine.$persist has a load-order trap where
//   x-model silently fails to bind if alpine-persist.js hasn't loaded yet
//
// Markup pattern (per fieldset):
//   <fieldset class="decision-form" data-decision-id="some-decision">
//     <legend>Question?</legend>
//     <p class="question-prompt">Restatement with my recommendation.</p>
//     <div class="options">
//       <label><input type="radio" name="some-decision" value="a"> A</label>
//       <label><input type="radio" name="some-decision" value="b"> B</label>
//     </div>
//     <button type="button" class="clear-q" data-clears="some-decision">Clear this question</button>
//     <textarea placeholder="Comments..." data-comment="some-decision"></textarea>
//   </fieldset>
//
// Toolbar:
//   <div class="form-toolbar">
//     <button type="button" data-form-action="copy-all">Copy all responses</button>
//     <button type="button" data-form-action="download-json">Download JSON</button>
//     <button type="button" data-form-action="clear-all">Clear all</button>
//   </div>

(function() {
  const STORAGE_KEY = 'html_form_responses_v1';  // namespace per report if needed

  // --- Optional: absorbed-content cleanup ---
  // When this render relocates user-supplied text out of a form fieldset
  // (into a callout, demoted-q block, etc.), list those decision-ids here
  // and bump CURRENT_RENDER. Cleanup runs once per render-version, then dormant.
  const RENDER_VERSION_KEY = STORAGE_KEY + '_render_version';
  const CURRENT_RENDER = null;       // e.g. '2026-05-12-v2-absorb-q3' — set when absorbing
  const ABSORBED_IDS = [];           // e.g. ['decision-id-1', 'decision-id-2']
  if (CURRENT_RENDER && localStorage.getItem(RENDER_VERSION_KEY) !== CURRENT_RENDER) {
    try {
      const state = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      ABSORBED_IDS.forEach(id => delete state[id]);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      localStorage.setItem(RENDER_VERSION_KEY, CURRENT_RENDER);
    } catch (e) { console.warn('absorb-cleanup failed:', e); }
  }

  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
  }
  function save(state) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (e) { console.warn('localStorage save failed:', e); }
  }
  function readForm() {
    const state = {};
    document.querySelectorAll('.decision-form').forEach(form => {
      const id = form.dataset.decisionId;
      const radio = form.querySelector('input[type="radio"]:checked');
      const ta = form.querySelector('textarea');
      state[id] = {
        question: form.querySelector('legend')?.textContent?.trim() || id,
        choice: radio?.value || null,
        choiceLabel: radio ? (radio.closest('label')?.textContent?.trim() || radio.value) : null,
        comment: ta?.value?.trim() || ''
      };
    });
    return state;
  }
  function restoreForm() {
    const state = load();
    Object.entries(state).forEach(([id, v]) => {
      const form = document.querySelector(`.decision-form[data-decision-id="${id}"]`);
      if (!form) return;
      if (v.choice) {
        const r = form.querySelector(`input[type="radio"][value="${v.choice}"]`);
        if (r) r.checked = true;
      }
      if (v.comment) {
        const ta = form.querySelector('textarea');
        if (ta) ta.value = v.comment;
      }
    });
  }
  function persist() { save(readForm()); }

  function showToast(msg, color) {
    document.querySelectorAll('.form-toast').forEach(t => t.remove());
    const t = document.createElement('div');
    t.className = 'form-toast';
    t.textContent = msg;
    t.style.cssText = `position:fixed; bottom:80px; right:24px; padding:10px 18px;
      background:${color || '#0a5'}; color:white; border-radius:6px; z-index:99999;
      font-family:-apple-system, sans-serif; font-size:14px;
      box-shadow:0 4px 12px rgba(0,0,0,0.2);`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }
  function copyAll() {
    const state = readForm();
    let md = '# My responses\n\n';
    let answered = 0;
    Object.entries(state).forEach(([id, v]) => {
      if (!v.choice && !v.comment) return;
      answered++;
      md += `## ${v.question}\n`;
      if (v.choiceLabel) md += `- **Choice:** ${v.choiceLabel}\n`;
      if (v.comment) md += `- **Comment:** ${v.comment}\n`;
      md += '\n';
    });
    if (answered === 0) { showToast('No answers to copy yet', '#a60'); return; }
    navigator.clipboard.writeText(md)
      .then(() => showToast(`Copied ${answered} response${answered === 1 ? '' : 's'}`))
      .catch(err => showToast('Copy failed: ' + err.message, '#b33'));
  }
  function downloadJSON() {
    const payload = { generated_at: new Date().toISOString(), responses: readForm() };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `responses_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 500);
    showToast('Downloaded JSON');
  }
  function clearAll() {
    if (!confirm('Clear all responses on this page?')) return;
    document.querySelectorAll('.decision-form input[type="radio"]').forEach(r => { r.checked = false; r._lastChecked = false; });
    document.querySelectorAll('.decision-form textarea').forEach(t => t.value = '');
    save({});
    showToast('Cleared all responses');
  }
  function clearQuestion(id) {
    const form = document.querySelector(`.decision-form[data-decision-id="${id}"]`);
    if (!form) return;
    form.querySelectorAll('input[type="radio"]').forEach(r => { r.checked = false; r._lastChecked = false; });
    const ta = form.querySelector('textarea');
    if (ta) ta.value = '';
    persist();
  }

  function wire() {
    // Radios: click-to-uncheck + persist on change
    document.querySelectorAll('.decision-form input[type="radio"]').forEach(radio => {
      radio.addEventListener('mousedown', function() { this._lastChecked = this.checked; });
      radio.addEventListener('click', function() {
        if (this._lastChecked && this.checked) {
          this.checked = false;
          persist();
        }
        document.querySelectorAll(`input[type="radio"][name="${this.name}"]`)
          .forEach(r => r._lastChecked = r.checked);
      });
      radio.addEventListener('change', persist);
    });
    // Textareas
    document.querySelectorAll('.decision-form textarea').forEach(ta => {
      ta.addEventListener('input', persist);
    });
    // Toolbar buttons
    document.querySelectorAll('[data-form-action]').forEach(btn => {
      const a = btn.dataset.formAction;
      btn.addEventListener('click', () => {
        if (a === 'copy-all') copyAll();
        else if (a === 'download-json') downloadJSON();
        else if (a === 'clear-all') clearAll();
      });
    });
    // Per-question Clear buttons
    document.querySelectorAll('.clear-q').forEach(btn => {
      btn.addEventListener('click', () => clearQuestion(btn.dataset.clears));
    });
  }
  function init() {
    restoreForm();
    wire();
    document.querySelectorAll('.decision-form input[type="radio"]:checked')
      .forEach(r => r._lastChecked = true);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
