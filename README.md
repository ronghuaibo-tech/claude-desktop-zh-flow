# Claude Desktop Zh Flow

Claude Desktop 汉化更新维护流程。这个仓库提供一个 Codex skill 和辅助脚本，用来维护已经中文化的 Claude Desktop。

This repository provides a Codex skill and helper script for maintaining a Chinese-localized Claude Desktop installation.

## 中文说明

这个项目不是重新发明一套汉化补丁，而是在已有 Claude Desktop 中文补丁的基础上，补齐了日常使用中最容易出问题的部分：更新前恢复官方签名版本、更新后重新打补丁、检查签名和中文资源、统计漏翻文案、管理旧备份。

macOS 上，Claude Desktop 汉化后会修改 `Claude.app` 内部文件，导致官方 Anthropic 签名失效。补丁器会重新本地签名为 `adhoc`，这能让应用继续运行，但 Claude 自带更新器通常要求官方签名链，所以直接自动更新容易失败或卡住。

本仓库的推荐流程是：

```text
恢复官方签名 Claude.app -> 手动更新 Claude Desktop -> 重新应用 zh-CN 补丁 -> 自检
```

Windows 上请直接使用上游项目提供的 Windows 安装脚本。本仓库主要补强 macOS 上的更新维护流程，同时在 README 中保留 Windows 使用入口，方便不同系统用户找到正确方法。

## 来源与引用

本项目基于并引用上游 Claude Desktop 中文补丁项目：

- 上游项目：[`javaht/claude-desktop-zh-cn`](https://github.com/javaht/claude-desktop-zh-cn)
- 本仓库调用的核心补丁器：`scripts/patch_claude_zh_cn.py`
- 本仓库默认以安全模式调用上游补丁器：`--skip-asar-patch --launch`

也就是说：真正的 Claude Desktop 中文资源、硬编码文案替换和 macOS 补丁能力来自上游项目；本仓库是在这个补丁基础上增加“更新流程管理、自检、审计和备份维护”。

## 优化完善点

相比直接运行原补丁，本仓库主要补充了这些能力：

- **更新前恢复官方签名版本**：从 `/Applications` 中最新可用的官方 Anthropic 签名备份恢复 `Claude.app`，避免中文化后的 `adhoc` 签名阻塞 Claude 自动更新。
- **更新后安全重新汉化**：统一调用上游补丁器的安全模式，跳过风险更高的 asar 在线页面注入，优先保证桌面应用稳定启动。
- **双配置语言同步**：同时维护 `~/Library/Application Support/Claude/config.json` 和 `~/Library/Application Support/Claude-3p/config.json` 的 `locale`。
- **深度健康检查**：新增 `doctor`，检查深度签名、关键 entitlement、中文资源和语言配置。
- **漏英审计**：新增 `audit`，自动比对 `en-US` 和 `zh-CN` 前端资源，统计仍与英文一致的 fallback 文案，并按 `usage`、`limit`、`connector`、`cowork` 等关键词聚类。
- **备份清理预览**：新增 `prune-backups`，默认只预览可清理的旧备份，只有显式加 `--delete` 才删除。
- **补丁仓库路径更灵活**：支持 `CLAUDE_ZH_PATCHER_ROOT`，也会自动查找当前工作区和历史常用目录。
- **重复流程固化为 Codex skill**：把“开始流程”“更新好了”“自检”“备份维护”等操作封装成可复用流程，减少每次手动记命令的成本。

## English Summary

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
