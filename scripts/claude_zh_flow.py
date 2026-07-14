#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


APP = Path("/Applications/Claude.app")
APPLICATIONS = Path("/Applications")
TEAM_ID = "Q6L2SF6YDW"
BACKUP_GLOB = "Claude.backup-before-zh-CN-*.app"
PATCHED_GLOB = "Claude.zh-patched-before-update-*.app"
FRONTEND_I18N = Path("Contents/Resources/ion-dist/i18n")
SHIPIT_CACHE = Path.home() / "Library/Caches/com.anthropic.claudefordesktop.ShipIt"
CONFIG_DIRS = [
    Path.home() / "Library/Application Support/Claude",
    Path.home() / "Library/Application Support/Claude-3p",
]
DEFAULT_PATCHER_CANDIDATES = [
    Path("/Users/a0000/Documents/Codex/2026-06-01/claude/work/claude-desktop-zh-cn-latest"),
    Path("/Users/a0000/Documents/Codex/2026-06-01/claude/work/claude-desktop-zh-cn"),
]
AUDIT_KEYWORDS = [
    "approval",
    "artifact",
    "billing",
    "connector",
    "cowork",
    "credit",
    "delete",
    "file",
    "limit",
    "managed",
    "memory",
    "model",
    "permission",
    "preview",
    "project",
    "role",
    "scheduled",
    "sign in",
    "slack",
    "spend",
    "sso",
    "task",
    "usage",
    "workspace",
]
KEEP_ENGLISH_RE = re.compile(
    r"^(?:[A-Z][A-Za-z0-9.+#/-]*|[A-Z0-9_./:+-]+|[\d\s%.,:/()+-]+)$"
)
ENGLISH_WORD_RE = re.compile(r"[A-Za-z]{3,}")
HAN_RE = re.compile(r"[\u4e00-\u9fff]")


def run(cmd: list[str], *, check: bool = False, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=check,
    )


def log(message: str) -> None:
    print(message, flush=True)


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def patcher_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_root = os.environ.get("CLAUDE_ZH_PATCHER_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    cwd = Path.cwd()
    candidates.extend([
        cwd / "work/claude-desktop-zh-cn-latest",
        cwd / "work/claude-desktop-zh-cn",
    ])
    candidates.extend(DEFAULT_PATCHER_CANDIDATES)
    return unique_paths(candidates)


def app_version(app: Path) -> str | None:
    if not app.exists():
        return None
    result = run(["defaults", "read", str(app / "Contents/Info"), "CFBundleShortVersionString"])
    value = (result.stdout or "").strip()
    return value or None


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def flatten_strings(data: object, prefix: str = "") -> dict[str, str]:
    if isinstance(data, dict):
        rows: dict[str, str] = {}
        for key, value in data.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.update(flatten_strings(value, child_prefix))
        return rows
    if isinstance(data, str):
        return {prefix: data}
    return {}


def has_han(value: str) -> bool:
    return bool(HAN_RE.search(value))


def is_english_like(value: str) -> bool:
    return bool(ENGLISH_WORD_RE.search(value))


def should_keep_english(value: str) -> bool:
    stripped = value.strip()
    return bool(KEEP_ENGLISH_RE.match(stripped))


def codesign_info(app: Path) -> str:
    if not app.exists():
        return "(missing)"
    result = run(["codesign", "-dv", str(app)])
    return result.stdout or ""


def team_identifier(app: Path) -> str | None:
    info = codesign_info(app)
    match = re.search(r"TeamIdentifier=(.+)", info)
    return match.group(1).strip() if match else None


def signature_summary(app: Path) -> str:
    info = codesign_info(app)
    lines = []
    for line in info.splitlines():
        if line.startswith(("Signature", "Timestamp", "TeamIdentifier")):
            lines.append(line)
    return "\n".join(lines) if lines else info.strip()


def is_official(app: Path) -> bool:
    return team_identifier(app) == TEAM_ID


def zh_resources(app: Path = APP) -> list[Path]:
    roots = [
        app / "Contents/Resources",
        app / "Contents/Resources/ion-dist/i18n",
        app / "Contents/Resources/ion-dist/i18n/statsig",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("zh-CN.json", "zh-CN.lproj"):
            found.extend(root.glob(pattern))
    return sorted(found)


def frontend_i18n_path(locale: str, app: Path = APP) -> Path:
    return app / FRONTEND_I18N / f"{locale}.json"


def config_path(config_dir: Path) -> Path:
    return config_dir / "config.json"


def set_locale(locale: str) -> None:
    for directory in CONFIG_DIRS:
        path = config_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, object] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                backup = path.with_suffix(".json.bak-invalid")
                shutil.copy2(path, backup)
                log(f"Backed up invalid config: {backup}")
        data["locale"] = locale
        path.write_text(json.dumps(data, ensure_ascii=False, indent="\t") + "\n", encoding="utf-8")
        log(f"Set locale {locale}: {path}")


def current_locales() -> list[str]:
    rows = []
    for directory in CONFIG_DIRS:
        path = config_path(directory)
        if not path.exists():
            rows.append(f"{path}: (missing)")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append(f"{path}: {data.get('locale')!r}")
        except Exception as exc:
            rows.append(f"{path}: invalid JSON ({exc})")
    return rows


def list_backups() -> list[Path]:
    return sorted(APPLICATIONS.glob(BACKUP_GLOB))


def list_patched_backups() -> list[Path]:
    return sorted(APPLICATIONS.glob(PATCHED_GLOB))


def path_size_kib(path: Path) -> int:
    result = run(["du", "-sk", str(path)])
    if result.returncode != 0:
        return 0
    first = (result.stdout or "0").split()[0]
    return int(first) if first.isdigit() else 0


def format_kib(kib: int) -> str:
    size = float(kib)
    for unit in ("KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GiB"


def choose_backup(current_version: str | None) -> Path:
    official = [path for path in list_backups() if is_official(path)]
    if not official:
        raise SystemExit("No official Anthropic-signed Claude backup found in /Applications.")
    if current_version:
        matching = [path for path in official if app_version(path) == current_version]
        if matching:
            return matching[-1]
    return official[-1]


def quit_claude() -> None:
    run(["osascript", "-e", 'tell application "Claude" to quit'])
    for _ in range(40):
        result = run([
            "pgrep",
            "-f",
            r"/Applications/Claude\.app/Contents/(MacOS/Claude|Frameworks/Claude Helper)",
        ])
        if result.returncode != 0:
            return
        time.sleep(0.5)


def restore() -> None:
    current_version = app_version(APP)
    backup = choose_backup(current_version)
    log(f"Selected official backup: {backup}")
    log(f"Backup version: {app_version(backup)}")
    log(signature_summary(backup))

    quit_claude()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    patched = APPLICATIONS / f"Claude.zh-patched-before-update-{stamp}.app"
    if APP.exists():
        shutil.move(str(APP), str(patched))
        log(f"Moved current app to: {patched}")
    run(["ditto", str(backup), str(APP)], check=True)
    run(["xattr", "-dr", "com.apple.quarantine", str(APP)])
    if SHIPIT_CACHE.exists():
        shutil.rmtree(SHIPIT_CACHE)
        log(f"Removed update cache: {SHIPIT_CACHE}")
    set_locale("en-US")
    verify_official()


def verify_official() -> None:
    version = app_version(APP)
    log(f"Current app version: {version}")
    log(signature_summary(APP))
    if not is_official(APP):
        raise SystemExit("Restored app is not official-signed.")
    found = zh_resources(APP)
    if found:
        raise SystemExit("Unexpected zh-CN resources remain:\n" + "\n".join(map(str, found)))
    log("Official restore verified.")


def find_patcher_root() -> Path:
    for root in patcher_candidates():
        patcher = root / "scripts/patch_claude_zh_cn.py"
        if patcher.exists():
            return root
    raise SystemExit(
        "Cannot find javaht/claude-desktop-zh-cn patcher. "
        "Set CLAUDE_ZH_PATCHER_ROOT or clone it to work/claude-desktop-zh-cn-latest first."
    )


def patch(update_patcher: bool) -> None:
    root = find_patcher_root()
    if update_patcher:
        log(f"Updating patcher repo: {root}")
        result = run(["git", "-C", str(root), "fetch", "origin", "main", "--tags"])
        if result.returncode == 0:
            result = run(["git", "-C", str(root), "reset", "--hard", "origin/main"])
        if result.returncode != 0:
            log("Patcher update failed; continuing with existing local checkout.")
            if result.stdout:
                log(result.stdout.strip())

    patcher = root / "scripts/patch_claude_zh_cn.py"
    cmd = [
        "/usr/bin/python3",
        str(patcher),
        "--user-home",
        str(Path.home()),
        "--lang",
        "zh-CN",
        "--skip-asar-patch",
        "--launch",
    ]
    result = run(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    set_locale("zh-CN")
    verify_patched()


def verify_patched() -> None:
    log(f"Current app version: {app_version(APP)}")
    log(signature_summary(APP))
    if is_official(APP):
        raise SystemExit("Patch did not change signature; expected adhoc-signed app.")
    found = zh_resources(APP)
    if not found:
        raise SystemExit("No zh-CN resources found after patch.")
    for path in found:
        log(f"zh resource: {path}")
    log("Patched app verified.")


def audit_translation(limit: int, json_output: Path | None = None) -> None:
    limit = max(0, limit)
    en_path = frontend_i18n_path("en-US")
    zh_path = frontend_i18n_path("zh-CN")
    if not en_path.exists():
        raise SystemExit(f"Missing frontend en-US resource: {en_path}")
    if not zh_path.exists():
        raise SystemExit(f"Missing frontend zh-CN resource: {zh_path}")

    en = flatten_strings(load_json(en_path))
    zh = flatten_strings(load_json(zh_path))
    same_as_english: list[dict[str, str]] = []
    likely_keep: list[dict[str, str]] = []
    keyword_counts: collections.Counter[str] = collections.Counter()
    keyword_examples: dict[str, list[dict[str, str]]] = collections.defaultdict(list)

    for key, source in sorted(en.items()):
        target = zh.get(key)
        if not isinstance(target, str) or target != source or not is_english_like(source):
            continue
        row = {"key": key, "text": source}
        if should_keep_english(source):
            likely_keep.append(row)
            continue
        same_as_english.append(row)
        lowered = source.lower()
        for keyword in AUDIT_KEYWORDS:
            if keyword in lowered:
                keyword_counts[keyword] += 1
                if len(keyword_examples[keyword]) < 5:
                    keyword_examples[keyword].append(row)

    zh_strings = list(zh.values())
    with_chinese = sum(1 for value in zh_strings if has_han(value))
    report = {
        "app": str(APP),
        "version": app_version(APP),
        "installed_strings": len(zh_strings),
        "strings_with_chinese": with_chinese,
        "same_as_english_review_needed": len(same_as_english),
        "same_as_english_likely_keep": len(likely_keep),
        "keyword_counts": dict(keyword_counts.most_common()),
        "samples": same_as_english[:limit],
        "keyword_examples": {
            keyword: examples for keyword, examples in keyword_examples.items()
        },
    }

    log(f"Translation audit for Claude {report['version']}")
    log(f"Installed frontend strings: {report['installed_strings']}")
    log(f"Strings containing Chinese: {report['strings_with_chinese']}")
    log(f"Same as English, review needed: {report['same_as_english_review_needed']}")
    log(f"Same as English, likely safe to keep: {report['same_as_english_likely_keep']}")
    log("")
    log("Keyword hotspots:")
    for keyword, count in keyword_counts.most_common(12):
        log(f"  {keyword}: {count}")
    if same_as_english and limit:
        log("")
        log(f"Top {min(limit, len(same_as_english))} review samples:")
        for row in same_as_english[:limit]:
            text = row["text"].replace("\n", " ")
            if len(text) > 140:
                text = text[:137] + "..."
            log(f"  {row['key']}: {text}")
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        log("")
        log(f"Wrote audit JSON: {json_output}")


def codesign_deep_verify(app: Path = APP) -> subprocess.CompletedProcess[str]:
    return run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])


def entitlements_text(app: Path = APP) -> str:
    result = run(["codesign", "-d", "--entitlements", "-", str(app)])
    return result.stdout or ""


def doctor() -> None:
    log(f"App: {APP}")
    log(f"Version: {app_version(APP)}")
    log(signature_summary(APP))
    log("")
    deep = codesign_deep_verify(APP)
    if deep.returncode == 0:
        log("Deep code-sign verification: OK")
    else:
        log("Deep code-sign verification: FAILED")
        if deep.stdout:
            log(deep.stdout.strip())
    entitlements = entitlements_text(APP)
    for entitlement in [
        "com.apple.security.virtualization",
        "com.apple.security.cs.allow-jit",
        "com.apple.security.cs.disable-library-validation",
    ]:
        marker = "OK" if entitlement in entitlements else "missing"
        log(f"Entitlement {entitlement}: {marker}")
    log("")
    log("Locales:")
    for line in current_locales():
        log(f"  {line}")
    log("")
    found = zh_resources(APP)
    log(f"zh-CN resources: {len(found)}")
    for path in found:
        log(f"  {path}")


def prune_backups(
    keep_official_per_version: int,
    keep_patched: int,
    delete: bool,
) -> None:
    keep_official_per_version = max(0, keep_official_per_version)
    keep_patched = max(0, keep_patched)
    candidates: list[Path] = []
    by_version: dict[str, list[Path]] = collections.defaultdict(list)
    for path in list_backups():
        version = app_version(path) or "unknown"
        by_version[version].append(path)
    for paths in by_version.values():
        paths.sort()
        if len(paths) > keep_official_per_version:
            candidates.extend(paths if keep_official_per_version == 0 else paths[:-keep_official_per_version])

    patched = list_patched_backups()
    patched.sort()
    if len(patched) > keep_patched:
        candidates.extend(patched if keep_patched == 0 else patched[:-keep_patched])

    candidates = unique_paths(sorted(candidates))
    if not candidates:
        log("No backup cleanup candidates.")
        return

    total_kib = sum(path_size_kib(path) for path in candidates)
    action = "Deleting" if delete else "Dry-run cleanup candidates"
    log(f"{action}: {len(candidates)} app backups, {format_kib(total_kib)}")
    for path in candidates:
        log(f"  {format_kib(path_size_kib(path))}  {path}  version={app_version(path)}")

    if not delete:
        log("")
        log("Dry run only. Re-run with --delete to remove these backups.")
        return

    for path in candidates:
        shutil.rmtree(path)
        log(f"Deleted: {path}")


def status() -> None:
    log(f"App: {APP}")
    log(f"Version: {app_version(APP)}")
    log(signature_summary(APP))
    log("")
    log("Locales:")
    for line in current_locales():
        log(f"  {line}")
    log("")
    log("zh-CN resources:")
    found = zh_resources(APP)
    if found:
        for path in found:
            log(f"  {path}")
    else:
        log("  (none)")
    log("")
    log("Official backups:")
    for path in list_backups():
        marker = "official" if is_official(path) else "not-official"
        log(f"  {path}  version={app_version(path)}  {marker}")
    log("")
    log("Patched backups:")
    for path in list_patched_backups():
        log(f"  {path}  version={app_version(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Desktop zh-CN update/localization helper.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("doctor")
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--limit", type=int, default=30)
    audit_parser.add_argument("--json-output", type=Path)
    prune_parser = sub.add_parser("prune-backups")
    prune_parser.add_argument("--keep-official-per-version", type=int, default=1)
    prune_parser.add_argument("--keep-patched", type=int, default=2)
    prune_parser.add_argument("--delete", action="store_true")
    sub.add_parser("restore")
    patch_parser = sub.add_parser("patch")
    patch_parser.add_argument("--update-patcher", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "doctor":
        doctor()
    elif args.command == "audit":
        audit_translation(args.limit, args.json_output)
    elif args.command == "prune-backups":
        prune_backups(args.keep_official_per_version, args.keep_patched, args.delete)
    elif args.command == "restore":
        restore()
    elif args.command == "patch":
        patch(args.update_patcher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
