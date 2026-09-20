await (async (mn) => {
  const r = await new Promise(res => {
    const x = new XMLHttpRequest();
    x.open('POST', '/meeting/delete');
    x.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    x.setRequestHeader('Accept', 'application/json, text/plain, */*');
    x.onloadend = () => res({ status: x.status, text: x.responseText });
    x.send(new URLSearchParams({ user_id: '', id: mn, meetingMasterEventId: '', occurrence: '', sendMail: 'false', mailBody: '' }).toString());
  });
  let j;
  try { j = JSON.parse(r.text); } catch (e) { return { ok: false, http: r.status, error: 'non-JSON reply (signed out?): ' + r.text.slice(0, 200) }; }
  return j.status ? { ok: true, deleted: mn } : { ok: false, errorCode: j.errorCode, error: j.errorMessage };
})(__MEETING_ID__);
