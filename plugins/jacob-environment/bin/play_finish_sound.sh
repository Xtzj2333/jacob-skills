#!/usr/bin/env bash
# Claude Code completion chime — fires as a Stop hook.
# Configurable via ~/.config/claude-chime/chime.conf (see chime.conf.template).

# SSH / headless guard — no audio session in remote contexts
[[ -n "${SSH_TTY:-}" ]] && exit 0

# Defaults
CHIME_SOUND="/System/Library/Sounds/Glass.aiff"
CHIME_VOLUME="1.0"
CHIME_MUTE="false"
CHIME_MIN_DURATION_SEC="0"

# Safe config override — never source; allowlist + printf -v only
config_file="${HOME}/.config/claude-chime/chime.conf"
if [[ -f "$config_file" ]]; then
    while IFS='=' read -r key val; do
        case "$key" in
            CHIME_SOUND|CHIME_VOLUME|CHIME_MUTE|CHIME_MIN_DURATION_SEC)
                printf -v "$key" '%s' "$val" ;;
        esac
    done < <(grep -E '^[A-Z_]+=[^[:space:]]' "$config_file")
fi

# Mute check
[[ "$CHIME_MUTE" == "true" ]] && exit 0

# Conditional trigger — CHIME_MIN_DURATION_SEC guard
# NOTE: As of May 2026, the Claude Code Stop hook payload does NOT include duration_ms
# or any timing field (confirmed: code.claude.com/docs/en/hooks). CHIME_MIN_DURATION_SEC
# is parsed and stored but cannot be evaluated against session duration. It is a
# forward-compatible stub: if Anthropic adds duration_ms to the Stop hook payload,
# wire it here with: elapsed=$(( duration_ms / 1000 ))
#                           [[ "$elapsed" -lt "$CHIME_MIN_DURATION_SEC" ]] && exit 0

# Kill any already-playing chime to prevent stacking
pkill -f 'afplay.*Sounds' 2>/dev/null || true

# Sound file guard
[[ ! -f "$CHIME_SOUND" ]] && exit 0

# Play — afplay -v: 0=silent, 1.0=normal system volume, up to 255=amplified
afplay -v "$CHIME_VOLUME" "$CHIME_SOUND" 2>/dev/null || true
