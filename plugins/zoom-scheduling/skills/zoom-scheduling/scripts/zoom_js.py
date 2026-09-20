#!/usr/bin/env python3
"""Build the JavaScript that creates or deletes a meeting on a Zoom web portal.

The output is pasted, unchanged, into Claude-in-Chrome's javascript_tool on a page
of the user's Zoom domain (e.g. yourschool.zoom.us). It runs inside their own
signed-in session, so it needs no API app, token, or cookie export -- which is the
point: many universities approve no third-party Zoom apps at all.

  zoom_js.py create --topic "Robin & Sam" --start "2026-09-19 15:15" [--minutes 60] [--tz America/Los_Angeles]
      -> JS for https://<zoom domain>/meeting/schedule. Returns
         {ok, meetingNumber, joinLink, manageUrl} or {ok:false, error}.
  zoom_js.py delete --id 97599158049
      -> JS for any page of that domain. Returns {ok, deleted} or {ok:false, error}.
      Zoom keeps deleted meetings under "Recently Deleted" for 7 days.
  zoom_js.py expect --start "2026-09-19 15:15"
      -> the time line the meeting's manage page must show, e.g. "Sep 19, 2026 03:15 PM".

Why create.js clicks Save instead of building the request from scratch: the
schedule form posts ~10 KB of account defaults (passcode, "require authentication",
audio, region...) and the server rejects a minimal body ("You need to select at least
one of Meeting Passcode, Waiting Room, Authentication"). So the snippet lets the form
build its own request, holds it back, changes six fields, and sends that. Everything
else stays exactly what the user would get from the form by hand. Zoom's CSRF guard
patches XMLHttpRequest on the page, so the request goes out signed.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_start(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    sys.exit(f"--start must look like 2026-09-19 15:15 (24-hour, local to --tz); got {s!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--topic", required=True)
    c.add_argument("--start", required=True, help="YYYY-MM-DD HH:MM, 24-hour, in --tz")
    c.add_argument("--minutes", type=int, default=60)
    c.add_argument("--tz", default="America/Los_Angeles", help="IANA zone; never leave it to the profile (it says Jakarta)")
    d = sub.add_parser("delete")
    d.add_argument("--id", required=True, help="meeting number, digits only")
    e = sub.add_parser("expect")
    e.add_argument("--start", required=True)
    a = ap.parse_args()

    if a.cmd == "create":
        dt = parse_start(a.start)
        if not 1 <= a.minutes <= 24 * 60:
            sys.exit("--minutes out of range")
        params = {
            "topic": a.topic,
            "date": dt.strftime("%m/%d/%Y"),
            "time": dt.strftime("%I:%M"),      # 12-hour, zero-padded, as the form sends it
            "ampm": dt.strftime("%p"),
            "minutes": a.minutes,
            "tz": a.tz,
        }
        js = (HERE / "create.js").read_text()
        print(js.replace("__PARAMS__", json.dumps(params, ensure_ascii=False)))
    elif a.cmd == "delete":
        mid = "".join(ch for ch in a.id if ch.isdigit())
        if len(mid) < 9:
            sys.exit(f"--id must be the meeting number; got {a.id!r}")
        print((HERE / "delete.js").read_text().replace("__MEETING_ID__", json.dumps(mid)))
    else:
        print(parse_start(a.start).strftime("%b %d, %Y %I:%M %p"))


if __name__ == "__main__":
    main()
