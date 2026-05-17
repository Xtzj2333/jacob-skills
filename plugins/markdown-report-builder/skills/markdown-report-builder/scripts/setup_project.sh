#!/usr/bin/env bash
# One-time setup of report-rendering infrastructure in a project.
# Run from the project root.
#
# Creates:
#   reports/reference.docx  — pandoc's default Word reference doc (Jacob customizes in Word)
#   reports/build.sh        — thin wrapper that calls the skill's build_report.sh

set -euo pipefail

SKILL_DIR="$HOME/.claude/skills/markdown-report-builder"
PROJECT_ROOT="$(pwd)"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo "skill directory not found: $SKILL_DIR" >&2
  exit 1
fi

mkdir -p reports

# Generate the default reference.docx if it doesn't already exist
if [[ ! -f reports/reference.docx ]]; then
  pandoc -o reports/reference.docx --print-default-data-file reference.docx
  echo "created: reports/reference.docx (pandoc default styling — customize in Word)"
else
  echo "skipped: reports/reference.docx already exists (kept your customizations)"
fi

# Write the project-local wrapper that just calls the skill script
cat > reports/build.sh <<EOF
#!/usr/bin/env bash
# Thin wrapper. Real logic lives in:
#   ~/.claude/skills/markdown-report-builder/scripts/build_report.sh
# Update via: ~/.claude/skills/markdown-report-builder/scripts/setup_project.sh
exec "\$HOME/.claude/skills/markdown-report-builder/scripts/build_report.sh" "\$@"
EOF
chmod +x reports/build.sh
echo "created: reports/build.sh (thin wrapper around the skill)"

cat <<'NEXT'

== Next steps (Jacob's hand) ==

1. Customize Word styling (~5–10 min):
   open reports/reference.docx
   - Modify Title, Heading 1/2/3, Body Text, Block Quote, Source Code styles
   - For Table: ribbon → Table Design → Modify Table Style
   - DO NOT rename any style; pandoc finds them by name only
   - Save and close

2. (Optional) Install IBM Plex fonts for the Carbon-design aesthetic:
   - Download IBM-Plex-Sans/Serif/Mono from https://github.com/IBM/plex/releases
   - Open .ttf files in Font Book → Install
   - Then add to per-report YAML:
       mainfont: "IBM Plex Serif"
       sansfont: "IBM Plex Sans"
       monofont: "IBM Plex Mono"

3. Test build:
   ./reports/build.sh path/to/some_report.md
   # produces some_report.docx and some_report.pdf

NEXT
