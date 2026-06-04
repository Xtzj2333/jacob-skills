#!/usr/bin/env node
// bridge.js — optional one-click "Submit" channel for decision-forms-html pages.
//
// Without this, the page's "Copy all responses" / "Download JSON" buttons require
// the user to paste/hand the answers back. With it, a "Submit" button (wired in
// form-pattern.js) POSTs the answers straight to this local server, which writes
// them to a file and — with --exit-on-submit — shuts down. When the agent
// launched the server as a background task, that exit is the agent's signal to
// read the file and act. No copy-paste, no "pick up my answers".
//
// Protocol (agent-facing):
//   1. node bridge.js --serve <report.html> --out <answers.json> --exit-on-submit &
//   2. open "http://localhost:8765/"            # served same-origin → no CORS
//   3. wait for the background task to exit, then read <answers.json>
//
// The page is served FROM this server so its fetch('/__bridge/submit') is
// same-origin. CORS headers are still sent so a bare file:// page works too.
//
// Zero dependencies (Node's built-in http/fs only).

const http = require('http');
const fs = require('fs');
const path = require('path');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  const next = process.argv[i + 1];
  return (next && !next.startsWith('--')) ? next : true;
}
const SERVE = arg('serve');
const OUT = arg('out');
const REQ_PORT = parseInt(arg('port', '8765'), 10);
const EXIT_ON_SUBMIT = !!arg('exit-on-submit', false);

if (!SERVE || !OUT) {
  console.error('usage: node bridge.js --serve <html> --out <json> [--port N] [--exit-on-submit]');
  process.exit(2);
}

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
function send(res, code, body, headers) {
  res.writeHead(code, Object.assign({}, CORS, headers || {}));
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  if (req.method === 'OPTIONS') return send(res, 204, '');
  if (url === '/__bridge/ping') return send(res, 200, 'ok', { 'Content-Type': 'text/plain' });

  if (url === '/__bridge/submit' && req.method === 'POST') {
    let body = '';
    req.on('data', c => { body += c; if (body.length > 5e6) req.destroy(); });
    req.on('end', () => {
      let parsed;
      try { parsed = JSON.parse(body || '{}'); }
      catch (e) { return send(res, 400, JSON.stringify({ ok: false, error: 'bad JSON' }), { 'Content-Type': 'application/json' }); }
      try {
        fs.mkdirSync(path.dirname(OUT), { recursive: true });
        fs.writeFileSync(OUT, JSON.stringify(parsed, null, 2));
        console.log('BRIDGE_SUBMIT received -> ' + OUT);
      } catch (e) {
        return send(res, 500, JSON.stringify({ ok: false, error: e.message }), { 'Content-Type': 'application/json' });
      }
      send(res, 200, JSON.stringify({ ok: true }), { 'Content-Type': 'application/json' });
      if (EXIT_ON_SUBMIT) {
        res.on('finish', () => server.close(() => process.exit(0)));
        setTimeout(() => process.exit(0), 1500);
      }
    });
    return;
  }

  // Everything else serves the report HTML (so refresh / deep links still work).
  fs.readFile(SERVE, (err, buf) => {
    if (err) return send(res, 404, 'not found', { 'Content-Type': 'text/plain' });
    send(res, 200, buf, { 'Content-Type': 'text/html; charset=utf-8' });
  });
});

let port = REQ_PORT;
(function listen() {
  server.once('error', (e) => {
    if (e.code === 'EADDRINUSE' && port < REQ_PORT + 20) { port++; return listen(); }
    console.error('listen failed:', e.message); process.exit(1);
  });
  server.listen(port, '127.0.0.1', () => {
    console.log('BRIDGE_URL=http://localhost:' + port + '/');
    console.log('serving: ' + SERVE);
    console.log('out:     ' + OUT + (EXIT_ON_SUBMIT ? '  (will exit on submit)' : ''));
  });
})();

process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));
