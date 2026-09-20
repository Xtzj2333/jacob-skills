await (async (P) => {
  if (!/\/meeting\/schedule/.test(location.pathname))
    return { ok: false, error: 'not on the schedule page (signed out? landed on ' + location.host + location.pathname + ')' };
  const XHR = XMLHttpRequest.prototype, open0 = XHR.open, send0 = XHR.send;
  const restore = () => { XHR.open = open0; XHR.send = send0; };
  let body;
  try {
    body = await new Promise((resolve, reject) => {
      XHR.open = function (m, u) { this.__u = u; return open0.apply(this, arguments); };
      XHR.send = function (b) {
        if (/\/rest\/meeting\/save/.test(this.__u)) { restore(); resolve(String(b)); return; }
        return send0.apply(this, arguments);
      };
      const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Save');
      if (!btn) return reject('no Save button yet: wait for the form to finish loading, then rerun');
      btn.click();
      setTimeout(() => reject('the form did not submit within 8 s (a field failed its own validation?)'), 8000);
    });
  } catch (e) { restore(); return { ok: false, error: String(e) }; }
  const o = JSON.parse(body);
  for (const k of ['topic', 'startDate', 'startTime', 'startTime2', 'duration', 'timezone'])
    if (!o[k] || !('value' in o[k])) return { ok: false, error: 'Zoom changed its schedule form: field ' + k + ' is gone. Nothing was created.' };
  o.topic.value = P.topic; o.startDate.value = P.date; o.startTime.value = P.time;
  o.startTime2.value = P.ampm; o.duration.value = P.minutes; o.timezone.value = P.tz;
  const r = await new Promise(res => {
    const x = new XMLHttpRequest();
    x.open('POST', '/rest/meeting/save');
    x.setRequestHeader('Content-Type', 'application/json');
    x.setRequestHeader('Accept', 'application/json, text/plain, */*');
    x.onloadend = () => res({ status: x.status, text: x.responseText });
    x.send(JSON.stringify(o));
  });
  let j;
  try { j = JSON.parse(r.text); } catch (e) { return { ok: false, http: r.status, error: 'non-JSON reply (signed out?): ' + r.text.slice(0, 200) }; }
  if (!j.status) return { ok: false, errorCode: j.errorCode, error: j.errorMessage };
  return { ok: true, meetingNumber: j.result.mn, joinLink: j.result.joinLink, manageUrl: j.result.url };
})(__PARAMS__);
