---
name: claude-desktop-zh-flow
description: Maintain the user's patched Chinese-localized Claude Desktop on macOS. Use when the user asks to start the Claude Desktop update/localization flow, restore the original Claude.app before updating, re-apply the Chinese UI patch after a manual update, diagnose why the Chinese patch blocks auto-update, or manage backups created by the Claude Desktop zh-CN patch workflow.
---

# Claude Desktop Zh Flow

## Overview

Use this skill for the user's repeat workflow around Claude Desktop UI localization on macOS:

1. Restore `/Applications/Claude.app` from the latest matching official Anthropic-signed backup.
2. Let the user manually update Claude Desktop.
3. Re-apply the zh-CN patch in safe mode.

The underlying reason for the workflow: localizing Claude modifies files inside `Claude.app`, invalidating the official Anthropic signature. The patcher re-signs locally as `adhoc`; Claude's updater validates signatures, so auto-update will fail or spin until the official signed app is restored.

## Quick Commands

Run the helper script:

```bash
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py status
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py doctor
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py audit
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py prune-backups
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py restore
/usr/bin/python3 /Users/a0000/.codex/skills/claude-desktop-zh-flow/scripts/claude_zh_flow.py patch
```

Use `status` before changing anything.

## Workflow

### When The User Says "开始流程"

1. Run `status`.
2. Run `restore`.
3. Tell the user to manually update Claude Desktop.
4. Stop and wait for the user to say the update is done.

Do not run `patch` before the user confirms the manual update is finished.

### When The User Says "更新好了"

1. Run `status` and confirm `/Applications/Claude.app` is official-signed (`TeamIdentifier=Q6L2SF6YDW`).
2. Run `patch`.
3. Run `status` again.
4. Report the installed version, that locale is `zh-CN`, and the new official backup path.

### When The User Asks Why Updates Fail

Explain briefly:

- The zh-CN patch changes files inside `/Applications/Claude.app`.
- macOS app code signing is invalidated by that change.
- The patcher has to re-sign locally as `adhoc`.
- Claude's updater expects an official Anthropic-signed app/update chain, so auto-update can fail.
- The safe practice is restore official app -> update -> re-patch.

Avoid recommending updater signature bypasses. They are fragile and may affect sandboxing, Cowork, permissions, and future starts.

## Helper Behavior

`restore`:

- Quits Claude Desktop.
- Chooses the newest official-signed backup matching the current app version when possible.
- Moves the current patched app to `/Applications/Claude.zh-patched-before-update-YYYYMMDD-HHMMSS.app`.
- Copies the official backup back to `/Applications/Claude.app`.
- Clears the ShipIt update cache.
- Sets `~/Library/Application Support/Claude/config.json` and `Claude-3p/config.json` locale to `en-US`.
- Verifies official signature and absence of `zh-CN` resources.

`patch`:

- Finds the local `javaht/claude-desktop-zh-cn` checkout, preferring `CLAUDE_ZH_PATCHER_ROOT`, then the current task's `work/claude-desktop-zh-cn-latest`, then the known historical checkout.
- Runs its macOS patcher with `--skip-asar-patch --launch`.
- Sets both Claude config files to `zh-CN`.
- Verifies the app version, zh-CN resources, and the expected `adhoc` signature.

`doctor`:

- Runs a deeper local health check without changing files.
- Verifies deep code signing, key entitlements, locale config, and zh-CN resources.

`audit`:

- Compares installed `en-US` and `zh-CN` frontend resources.
- Reports English fallback strings, keyword hotspots, and optionally writes a JSON report.

`prune-backups`:

- Shows backup cleanup candidates without deleting by default.
- Keeps one official backup per version and the newest two patched backups unless overridden.
- Deletes only when explicitly run with `--delete`.

## Notes

- Safe mode intentionally skips online-page injection and 3P model validation patches.
- It is normal for some long main-process menu labels to be skipped in length-preserving safe mode.
- If the patch repository cannot update because of network errors, use the existing local checkout rather than blocking the flow.
- If no official signed backup exists, tell the user to install or download an official Claude Desktop package manually before continuing.
