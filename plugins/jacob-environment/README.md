# jacob-environment

Jacob's portable Claude Code environment as a single plugin: notification chimes, completion sound, and shared MCP server set.

Versions, namespaces, and reverses cleanly via `/plugin disable jacob-environment@jacob-skills` or `/plugin uninstall`.

---

## What this plugin ships

| Component | What it does |
|---|---|
| `Notification` hook | Glass chime + macOS notification when Claude Code is waiting for your input |
| `PermissionRequest` hook | Hero chime + macOS notification when Claude Code asks for a yes/no permission |
| `Stop` hook | Glass chime when a Claude session finishes (configurable — see below) |
| `tavily` MCP server | Real-time web search via Tavily |
| `zotero` MCP server | Read/search your Zotero library |

---

## Install

```
/plugin install jacob-environment@jacob-skills
/reload-plugins
```

---

## Per-user setup

### 1. Set MCP API keys (required for Tavily + Zotero to work)

Add to `~/.zshenv` (or your shell's equivalent):

```bash
# Tavily — get a free key at https://tavily.com/
export TAVILY_API_KEY="tvly-..."

# Zotero — from https://www.zotero.org/settings/keys
export ZOTERO_API_KEY="..."
export ZOTERO_LIBRARY_ID="..."           # numeric, from your Zotero profile URL
```

Open a new terminal and restart Claude Code so the env-vars take effect.

### 2. Install `zotero-mcp` (required for Zotero)

The plugin invokes `zotero-mcp` from your PATH. Install via pip / pipx / uv — whatever you use for Python tools. Example:

```bash
pip install --user zotero-mcp     # or: pipx install zotero-mcp
```

Verify with `which zotero-mcp` — if it resolves, the plugin will find it.

### 3. (Optional) Configure the completion sound

The Stop hook runs `bin/play_finish_sound.sh`, which respects `~/.config/claude-chime/chime.conf`:

```bash
mkdir -p ~/.config/claude-chime
cat > ~/.config/claude-chime/chime.conf <<'EOF'
CHIME_SOUND=/System/Library/Sounds/Glass.aiff
CHIME_VOLUME=0.7
CHIME_MUTE=false
EOF
```

Set `CHIME_MUTE=true` to silence completely without uninstalling. SSH sessions auto-skip the chime.

---

## What this plugin does NOT touch

- Your global `~/.claude/CLAUDE.md` — plugins can't override that. Sync that separately.
- Your `~/.claude/settings.json` — only `agent` and `subagentStatusLine` keys can be plugin-shipped per Anthropic's plugin spec; other settings (theme, statusLine, permissions, etc.) stay per-user.
- Your API keys — only the *shape* of the MCP config ships; values are env-var-substituted at runtime.

---

## Uninstall

```
/plugin uninstall jacob-environment@jacob-skills
```

This removes the hooks and MCP servers cleanly. Your environment variables and `~/.config/claude-chime/` config persist (those are yours).

---

## For Jacob: migrating off the standalone setup

Once this plugin is installed and confirmed working on your machine, remove the duplicate hook entries from `~/.claude/settings.json`:

- Delete the `hooks.Notification` block (now shipped by this plugin)
- Delete the `hooks.PermissionRequest` block (now shipped by this plugin)

The `~/.claude.json` `mcpServers` block can stay as-is or be cleaned up — the plugin's `.mcp.json` registers the same servers under the same names. If both are present, the plugin definition takes precedence at session start.
