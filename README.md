# Claude Desktop Zh Flow

Codex skill and helper script for maintaining a Chinese-localized Claude Desktop installation.

On macOS, this repository provides a repeatable restore -> update -> re-patch workflow for Claude Desktop. It restores an official Anthropic-signed `Claude.app`, lets the user update Claude Desktop manually, then reapplies the zh-CN patch in safe mode.

On Windows, use the upstream `javaht/claude-desktop-zh-cn` Windows installer or script directly. This repository does not wrap the Windows installer; it documents the recommended entry point so Mac and Windows users can find the right path.

## macOS Usage

Install or copy this directory as a Codex skill, then run the helper script:

```bash
/usr/bin/python3 scripts/claude_zh_flow.py status
```

Normal update flow:

```bash
/usr/bin/python3 scripts/claude_zh_flow.py restore
```

After Claude Desktop finishes updating manually:

```bash
/usr/bin/python3 scripts/claude_zh_flow.py patch
```

Useful maintenance commands:

```bash
/usr/bin/python3 scripts/claude_zh_flow.py status
/usr/bin/python3 scripts/claude_zh_flow.py doctor
/usr/bin/python3 scripts/claude_zh_flow.py audit
/usr/bin/python3 scripts/claude_zh_flow.py prune-backups
/usr/bin/python3 scripts/claude_zh_flow.py restore
/usr/bin/python3 scripts/claude_zh_flow.py patch
```

The patch command expects a local checkout of the upstream patcher:

```bash
git clone https://github.com/javaht/claude-desktop-zh-cn.git work/claude-desktop-zh-cn-latest
```

Alternatively, point the helper to an existing checkout:

```bash
export CLAUDE_ZH_PATCHER_ROOT=/path/to/claude-desktop-zh-cn
```

## Windows Usage

Use the upstream Windows installer from `javaht/claude-desktop-zh-cn`:

```powershell
git clone https://github.com/javaht/claude-desktop-zh-cn.git
cd claude-desktop-zh-cn
.\install-windows.bat
```

If PowerShell execution policy blocks scripts, open PowerShell as the current user and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run the installer again.

After Claude Desktop updates on Windows, rerun the upstream Windows installer to reapply the localization.

## Notes

- `restore` expects at least one official Anthropic-signed backup in `/Applications`.
- `patch` expects a local checkout of `javaht/claude-desktop-zh-cn`.
- `CLAUDE_ZH_PATCHER_ROOT` can point to that checkout explicitly.
- `prune-backups` is dry-run by default and deletes only with `--delete`.
- This repository is a personal workflow wrapper around the upstream localization project, not an official Anthropic tool.
