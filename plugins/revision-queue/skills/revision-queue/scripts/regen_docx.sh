#!/usr/bin/env bash
# Regenerate .docx mirrors from their .md sources.
#
# Files are named after the user via $USER_NAME (default "user"):
#   Default 2-file project: <USER>_todos.md + completed_actions_log.md
#   Optional 3rd file (async pattern): <USER>_actions.md  — silently skipped if absent.
#
# Usage:  bash regen_docx.sh PROJECT_DIR
# Or:     ./regen_docx.sh PROJECT_DIR

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 PROJECT_DIR" >&2
    exit 2
fi

USER_NAME="${USER_NAME:-user}"
PROJ="$1"
cd "$PROJ"

ACTIONS_FILE="${USER_NAME}_actions.md"
FILES=("${USER_NAME}_todos.md" "${ACTIONS_FILE}" "completed_actions_log.md")

if ! command -v pandoc >/dev/null 2>&1; then
    echo "pandoc not found in PATH — install via 'brew install pandoc'." >&2
    exit 3
fi

for md in "${FILES[@]}"; do
    if [[ ! -f "$md" ]]; then
        # <USER>_actions.md is optional (3-file async pattern only); silent skip.
        if [[ "$md" != "${ACTIONS_FILE}" ]]; then
            echo "  skip: $md (missing)" >&2
        fi
        continue
    fi
    out="${md%.md}.docx"
    pandoc "$md" -o "$out"
    echo "  wrote: $out"
done
