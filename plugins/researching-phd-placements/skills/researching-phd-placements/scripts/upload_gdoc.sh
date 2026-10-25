#!/bin/bash
# Upload a built doc HTML as a native Google Doc (headings, nested bullets, bold, italic and highlight survive
# Drive's HTML import) and print its link.
#
# usage: bash upload_gdoc.sh [--replace] <doc.html> "<rclone remote>:<folder path>" "<Doc title>"
#   e.g. bash upload_gdoc.sh gdoc.html "berkeley:Berkeley/Placement" "Yale History PhD placements"
#
# Without --replace it refuses when a Doc with that title is already in the folder. --replace overwrites that Doc's
# content under the same ID: the link doesn't change and Docs' version history keeps the old text, but anything
# typed into the Doc since your last change is lost and anchored comments are orphaned. Use it only after checking
# nobody has edited or commented (references/gdocs-publish.md). Either way the result has no table of contents and
# its headings have no IDs: repair them, un-bold the counts, insert the TOC and read the doc back.
set -euo pipefail
replace=0
if [ "${1:-}" = "--replace" ]; then replace=1; shift; fi
[ $# -eq 3 ] || { sed -n '5,6p' "$0"; exit 2; }
html="$1"; folder="$2"; title="$3"
[ -f "$html" ] || { echo "no such file: $html" >&2; exit 2; }

# every Doc ID in the folder whose name (with the html export extension) is the title, one per line
ids_for_title() {
  rclone lsjson "$folder" --drive-export-formats html 2>/dev/null \
    | python3 -c 'import json,sys; t=sys.argv[1]+".html"; print("\n".join(d["ID"] for d in json.load(sys.stdin) if d["Name"]==t))' "$title"
}

before=$(ids_for_title) || { echo "can't list $folder (wrong remote or folder? rclone auth expired?)" >&2; exit 1; }
if [ $replace -eq 0 ] && [ -n "$before" ]; then
  echo "\"$title\" already exists in $folder; not overwriting. To refresh it under the same link, check that nobody" >&2
  echo "has edited or commented on it since your last change, then rerun with --replace. Edited: edit it in place." >&2
  exit 1
fi
if [ $replace -eq 1 ]; then
  [ -n "$before" ] || { echo "nothing to replace: no \"$title\" in $folder (drop --replace to create it)" >&2; exit 1; }
  [ "$(echo "$before" | wc -l | tr -d ' ')" = 1 ] || { echo "several Docs are called \"$title\"; resolve that first" >&2; exit 1; }
fi

flags=(--drive-import-formats html --drive-export-formats html)
[ $replace -eq 1 ] && flags+=(--ignore-times)   # Docs have no size or checksum; force the transfer
if ! out=$(rclone copyto "$html" "$folder/$title.html" "${flags[@]}" 2>&1); then
  echo "$out" >&2; exit 1
fi
echo "$out" | grep -v "shared Google Drive client_id" || true   # rclone's notice that its shared client_id is being retired

after=$(ids_for_title)
if [ $replace -eq 1 ] && [ "$after" != "$before" ]; then
  echo "expected the content of $before replaced in place, but the folder now holds: $(echo $after)." >&2
  echo "rclone made a duplicate Doc instead; trash the new one and edit $before by hand." >&2
  exit 1
fi
id=$(echo "$after" | head -1)
[ -n "$id" ] || { echo "uploaded, but couldn't find the Doc's ID in $folder" >&2; exit 1; }
echo "https://docs.google.com/document/d/$id/edit"
