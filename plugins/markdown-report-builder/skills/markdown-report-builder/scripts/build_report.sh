#!/usr/bin/env bash
# Build a markdown report into matching .docx and .pdf using established templates.
# Usage:  build_report.sh path/to/report.md [path/to/report2.md ...]
#
# Conventions:
#   - .docx output uses pandoc --reference-doc, looking for reports/reference.docx
#     UP THE TREE from each source file (project-local styling).
#     If none found, falls back to pandoc's default reference.
#   - .pdf output uses the Eisvogel template at ~/.local/share/pandoc/templates/eisvogel.latex
#     (see ~/.claude/skills/markdown-report-builder/SKILL.md for setup).
#   - LaTeX is via TinyTeX at ~/Library/TinyTeX/bin/universal-darwin/ (added to PATH below).
#
# Hard rule: do NOT add hand-rolled YAML colors. Eisvogel stock defaults are the
# established aesthetic. See SKILL.md "Hard rules".

set -euo pipefail

if ! command -v xelatex >/dev/null 2>&1; then
  export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
fi

if [[ $# -eq 0 ]]; then
  echo "usage: $(basename "$0") path/to/report.md [...]" >&2
  exit 1
fi

# Walk up from a starting directory looking for reports/reference.docx
find_reference_doc() {
  local dir="$1"
  while [[ "$dir" != "/" && -n "$dir" ]]; do
    if [[ -f "$dir/reports/reference.docx" ]]; then
      echo "$dir/reports/reference.docx"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

for md in "$@"; do
  if [[ ! -f "$md" ]]; then
    echo "skip (not found): $md" >&2
    continue
  fi

  base="${md%.md}"
  src_dir="$(cd "$(dirname "$md")" && pwd)"
  ref_docx="$(find_reference_doc "$src_dir" || true)"

  echo "=== $md ==="

  # 1. .docx — with project reference doc if found
  if [[ -n "$ref_docx" ]]; then
    pandoc "$md" --from=markdown --to=docx \
      --reference-doc="$ref_docx" \
      --output="${base}.docx"
    echo "   .docx via reference: $ref_docx"
  else
    pandoc "$md" --from=markdown --to=docx --output="${base}.docx"
    echo "   .docx (no reference.docx found; using pandoc default)"
  fi
  echo "   -> ${base}.docx"

  # 2. .pdf — Eisvogel stock styling (no custom flags beyond template + toc + idiomatic highlighting)
  pandoc "$md" --from=markdown \
    --pdf-engine=xelatex \
    --template=eisvogel \
    --syntax-highlighting=idiomatic \
    --toc \
    --output="${base}.pdf"
  echo "   -> ${base}.pdf"
done

echo "done."
