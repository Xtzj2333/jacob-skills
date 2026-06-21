#!/usr/bin/env python3
"""
fix_chat_cwd.py — repair Claude Code transcripts after moving them between Macs
so they resume cleanly AND background into agent view (`/bg`).

THE PROBLEM THIS SOLVES
-----------------------
Claude Code stores each chat at:
    ~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl
where <encoded-cwd> is the chat's absolute working directory with every
non-alphanumeric character replaced by '-'  (e.g. enc("/Users/x/My Proj")).

Every line of the transcript also records the working directory it ran in
("cwd": "..."). When you move a chat from an OLD Mac (user `olduser`) to a NEW
Mac, that recorded cwd still points at the old machine's path
(e.g. /Users/olduser/Claude/Proj) — a directory that does not exist here.

- `claude --resume <id>` from a terminal still works, because YOU supply a
  valid directory with `cd` first.
- BUT agent view (`claude agents`) re-hosts a backgrounded session IN THE CWD
  RECORDED INSIDE THE TRANSCRIPT. A dead cwd makes `/bg` fail with
  "Session can't start — source session ..." / "session is not responding,
  restarting it" in a loop.

Earlier failed `/bg` attempts also leave stale `bridge-session` marker lines
in the transcript, which compound the failure.

WHAT THIS SCRIPT DOES (per transcript)
--------------------------------------
1. Rewrites every cwd that starts with an OLD prefix to the matching NEW prefix.
2. Drops stale `bridge-session` lines.
3. Determines the session's HOME cwd (first cwd line). If that directory does
   not exist on disk (e.g. it was a deeper subfolder or a deleted git worktree),
   remaps every non-existent cwd up to its nearest EXISTING ancestor.
4. SAFETY GATE: only writes the file if the resulting home cwd (a) exists on
   disk AND (b) encodes to the file's own containing folder name. Otherwise the
   file is left completely untouched and reported as FLAGGED for manual review.
5. Backs up each file before editing (unless --no-backup).

Idempotent: re-running on already-fixed files is a no-op.

USAGE
-----
    python3 fix_chat_cwd.py \
        --map "/Users/olduser/Claude=>/Users/newuser/Library/Mobile Documents/com~apple~CloudDocs/Sync workspace/Claude" \
        [--map "OLD2=>NEW2" ...] \
        [--projects-dir ~/.claude/projects] \
        [--filter SUBSTRING]      # only folders whose name contains SUBSTRING \
        [--backup-dir PATH] \
        [--no-backup] \
        [--dry-run]               # report only, change nothing

Provide as many --map prefixes as you need (longest match wins).
ALWAYS run --dry-run first and read the summary before committing.
"""
import argparse, os, glob, json, re, sys, shutil

def enc(p: str) -> str:
    return re.sub(r'[^A-Za-z0-9]', '-', p)

def nearest_existing(p: str) -> str:
    while p and not os.path.isdir(p):
        p = os.path.dirname(p)
    return p

def remap(cwd: str, mappings):
    # longest OLD prefix first so nested maps resolve correctly
    for old, new in sorted(mappings, key=lambda m: -len(m[0])):
        if cwd == old or cwd.startswith(old + os.sep) or cwd.startswith(old):
            return new + cwd[len(old):]
    return cwd

def process_file(path, folder, mappings, dry):
    home = None
    records = []          # (kind, value)  kind in {"raw","d"}
    changed = False
    try:
        for line in open(path, encoding="utf-8"):
            s = line.rstrip("\n")
            if not s.strip():
                continue
            try:
                d = json.loads(s)
            except Exception:
                records.append(("raw", s)); continue
            if d.get("type") == "bridge-session":
                changed = True
                continue                      # drop stale bridge marker
            c = d.get("cwd")
            if isinstance(c, str):
                nc = remap(c, mappings)
                if nc != c:
                    d["cwd"] = nc; c = nc; changed = True
                if home is None:
                    home = c
            records.append(("d", d))
    except Exception as e:
        return ("ERROR", f"{path}: {e}")

    # If the session's home cwd is gone, remap dead cwds up to nearest ancestor.
    target = home
    if home and not os.path.isdir(home):
        target = nearest_existing(home)
        if target != home:
            changed = True
            for i, (k, v) in enumerate(records):
                if k == "d" and isinstance(v.get("cwd"), str) and not os.path.isdir(v["cwd"]):
                    v["cwd"] = target

    # SAFETY GATE
    if target and not (os.path.isdir(target) and enc(target) == folder):
        return ("FLAG", f"{os.path.basename(path)}  home_cwd={target!r}  (folder={folder})")
    if not changed:
        return ("CLEAN", None)
    if dry:
        return ("WOULD-FIX", None)

    out = [v if k == "raw" else json.dumps(v, ensure_ascii=False) for k, v in records]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, path)
    return ("FIXED", None)

def main():
    ap = argparse.ArgumentParser(description="Repair moved Claude Code transcripts for agent view.")
    ap.add_argument("--map", action="append", required=True,
                    help='OLD=>NEW path-prefix mapping (repeatable). Example: '
                         '"/Users/olduser/Claude=>/Users/me/Sync/Claude"')
    ap.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--filter", default=None, help="only project folders whose name contains this substring")
    ap.add_argument("--backup-dir", default=None, help="where to copy originals before editing")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mappings = []
    for m in args.map:
        if "=>" not in m:
            sys.exit(f"bad --map (need OLD=>NEW): {m}")
        old, new = m.split("=>", 1)
        mappings.append((old.strip(), new.strip()))

    proj = os.path.expanduser(args.projects_dir)
    folders = [d for d in glob.glob(os.path.join(proj, "*")) if os.path.isdir(d)]
    if args.filter:
        folders = [d for d in folders if args.filter in os.path.basename(d)]

    backup_dir = os.path.expanduser(args.backup_dir) if args.backup_dir else None
    if backup_dir and not args.dry_run and not args.no_backup:
        os.makedirs(backup_dir, exist_ok=True)

    tally = {}
    flags = []; errors = []
    for fol in folders:
        folder = os.path.basename(fol)
        for f in glob.glob(os.path.join(fol, "*.jsonl")):
            # back up before touching
            if backup_dir and not args.dry_run and not args.no_backup:
                dst = os.path.join(backup_dir, folder)
                os.makedirs(dst, exist_ok=True)
                shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
            status, msg = process_file(f, folder, mappings, args.dry_run)
            tally[status] = tally.get(status, 0) + 1
            if status == "FLAG": flags.append(msg)
            if status == "ERROR": errors.append(msg)

    print("=== fix_chat_cwd summary ===")
    for k in ("FIXED", "WOULD-FIX", "CLEAN", "FLAG", "ERROR"):
        if k in tally:
            print(f"  {k:10s}: {tally[k]}")
    if flags:
        print("\nFLAGGED (left untouched — home cwd missing or didn't match its folder):")
        for m in flags: print("   ", m)
    if errors:
        print("\nERRORS:")
        for m in errors: print("   ", m)
    if args.dry_run:
        print("\n(dry run — nothing was modified)")

if __name__ == "__main__":
    main()
