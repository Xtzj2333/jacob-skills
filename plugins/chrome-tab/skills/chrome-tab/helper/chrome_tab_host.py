#!/usr/bin/env python3
"""chrome-tab helper: the native-messaging host.

Chrome starts this process when the chrome-tab helper extension calls
`chrome.runtime.connectNative("com.jacob_skills.chrome_tab")`, and keeps it running while
the extension holds the port. It relays between two sides:

  * Chrome, on stdin/stdout, in native-messaging framing: a 4-byte native-endian length,
    then that many bytes of UTF-8 JSON;
  * chrome-tab, on a Unix socket (default ~/.claude/chrome-tab-helper/bridge.sock). Its
    directory is 0700 and the socket 0600, so only this user account can connect. Each
    connection carries one request line of JSON, {"cmd", "args", "timeout"}, and gets back
    one reply line, {"ok": true, "result": …} or {"ok": false, "error": "…"}.

`{"cmd": "host"}` is answered here, without asking the extension. It reports this process,
the Chrome process that started it (our parent — the launcher `exec`s us, so that is
Chrome's browser process), and what the extension said when it connected. chrome-tab uses
that Chrome pid to read window names from *this* Chrome by process id: a headless copy of
Chrome that another job launched can't answer for it that way.

Stdlib only, Python 3.8+. Nothing but framed messages may ever go to stdout.
"""
import itertools
import json
import os
import socket
import struct
import sys
import threading
import time
from pathlib import Path

SOCK = Path(os.environ.get("CHROME_TAB_SOCKET")
            or (Path.home() / ".claude" / "chrome-tab-helper" / "bridge.sock"))
LOG = SOCK.parent / "host.log"
MAX_TIMEOUT = 60.0

_out_lock = threading.Lock()
_pending = {}                 # request id -> [threading.Event, reply or None]
_pending_lock = threading.Lock()
_ids = itertools.count(1)
_hello = {}
_started = time.time()
_stopping = threading.Event()
_sock_ino = None


def log(msg):
    try:
        if LOG.exists() and LOG.stat().st_size > 1_000_000:
            LOG.write_text("")
        with LOG.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  [{os.getpid()}] {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------- Chrome side


def send_to_chrome(msg):
    data = json.dumps(msg).encode("utf-8")
    with _out_lock:
        sys.stdout.buffer.write(struct.pack("@I", len(data)) + data)
        sys.stdout.buffer.flush()


def read_from_chrome():
    head = sys.stdin.buffer.read(4)
    if len(head) < 4:
        return None
    (n,) = struct.unpack("@I", head)
    body = sys.stdin.buffer.read(n)
    if len(body) < n:
        return None
    return json.loads(body.decode("utf-8"))


def chrome_reader():
    """Route the extension's replies to whoever is waiting; stop when Chrome hangs up."""
    try:
        while not _stopping.is_set():
            msg = read_from_chrome()
            if msg is None:
                break
            if isinstance(msg, dict) and msg.get("type") == "hello":
                _hello.clear()
                _hello.update({k: v for k, v in msg.items() if k != "type"})
                log(f"extension connected: {_hello}")
                continue
            rid = msg.get("id") if isinstance(msg, dict) else None
            with _pending_lock:
                slot = _pending.get(rid)
            if slot is not None:
                slot[1] = msg
                slot[0].set()
    except Exception as e:
        log(f"reader stopped: {e!r}")
    stop("Chrome closed the port")


def ask_extension(cmd, args, timeout):
    rid = next(_ids)
    slot = [threading.Event(), None]
    with _pending_lock:
        _pending[rid] = slot
    try:
        send_to_chrome({"id": rid, "cmd": cmd, "args": args})
        if not slot[0].wait(timeout):
            return {"ok": False, "error": f"the extension did not answer within {timeout:g} s"}
        reply = slot[1]
        return {k: reply[k] for k in ("ok", "result", "error") if k in reply}
    finally:
        with _pending_lock:
            _pending.pop(rid, None)


# -------------------------------------------------------------- socket side


def handle(conn):
    with conn:
        conn.settimeout(5)
        buf = b""
        try:
            while not buf.endswith(b"\n") and len(buf) < 1_000_000:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
            req = json.loads(buf.decode("utf-8") or "{}")
            cmd = req.get("cmd")
            if cmd == "host":
                reply = {"ok": True, "result": {
                    "pid": os.getpid(), "chrome_pid": os.getppid(), "extension": dict(_hello),
                    "socket": str(SOCK), "started": _started}}
            elif not cmd:
                reply = {"ok": False, "error": "no cmd"}
            else:
                timeout = min(float(req.get("timeout") or 10.0), MAX_TIMEOUT)
                reply = ask_extension(cmd, req.get("args") or {}, timeout)
        except Exception as e:
            reply = {"ok": False, "error": f"host: {e!r}"}
        try:
            conn.settimeout(10)
            conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))
        except Exception:
            pass


def socket_alive():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(str(SOCK))
        return True
    except OSError:
        return False
    finally:
        s.close()


def bind_socket():
    """Bind SOCK, or return None while another live host serves it.

    A second host exists when the extension is loaded in two Chrome profiles. The first
    one keeps the socket; this one waits and takes over when that one goes away. A socket
    file nobody answers on is left over from a host that died, and is replaced.
    """
    global _sock_ino
    SOCK.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(SOCK.parent, 0o700)
    if SOCK.exists() or SOCK.is_symlink():
        if socket_alive():
            return None
        log(f"replacing stale {SOCK}")
        SOCK.unlink()
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old = os.umask(0o177)
    try:
        srv.bind(str(SOCK))
    finally:
        os.umask(old)
    os.chmod(SOCK, 0o600)
    _sock_ino = SOCK.stat().st_ino
    srv.listen(16)
    srv.settimeout(0.5)
    return srv


def stop(why):
    if _stopping.is_set():
        return
    _stopping.set()
    log(f"stopping: {why}")
    try:
        if _sock_ino is not None and SOCK.exists() and SOCK.stat().st_ino == _sock_ino:
            SOCK.unlink()                     # only our own socket, never a successor's
    except Exception:
        pass
    os._exit(0)


def ours():
    try:
        return _sock_ino is not None and SOCK.stat().st_ino == _sock_ino
    except OSError:
        return False


def main():
    global _sock_ino
    log(f"started by pid {os.getppid()} with {sys.argv[1:]}")
    threading.Thread(target=chrome_reader, daemon=True).start()
    srv = None
    waiting = False
    while not _stopping.is_set():
        if srv is None:
            srv = bind_socket()
            if srv is None:
                if not waiting:
                    log("another host serves the socket; waiting")
                    waiting = True
                time.sleep(1)
                continue
            waiting = False
            log(f"serving {SOCK}")
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            if not ours():                      # removed or replaced under us
                srv.close()
                srv, _sock_ino = None, None
            continue
        except OSError as e:
            log(f"accept failed: {e!r}")
            time.sleep(0.2)
            continue
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
