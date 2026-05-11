#!/usr/bin/env bash
# Regenerate .docx mirrors from their .md sources.
#
# Filenames are supplied by the caller (Claude resolves them via the
# `project-filename` skill, then passes them as positional args). The script
# does not construct names from any environment variable.
#
# Usage:  bash regen_docx.sh FILE.md [FILE.md ...]
# Example:
#   bash regen_docx.sh \
#       "Projects/boom-revisions/todos [boom].md" \
#       "Projects/boom-revisions/completed_actions_log [boom].md"

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 FILE.md [FILE.md ...]" >&2
    exit 2
fi

if ! command -v pandoc >/dev/null 2>&1; then
    echo "pandoc not found in PATH — install via 'brew install pandoc'." >&2
    exit 3
fi

for md in "$@"; do
    if [[ ! -f "$md" ]]; then
        echo "  skip: $md (missing)" >&2
        continue
    fi
    out="${md%.md}.docx"
    pandoc "$md" -o "$out"
    echo "  wrote: $out"
done
