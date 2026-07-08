from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "nac.codex-worktree-audit/v0.1"
PRIMARY_BRANCHES = {"main", "master"}


def build_worktree_audit(repo_root: Path) -> dict[str, Any]:
    root = _git_root(repo_root)
    head_branch = _git_optional(root, ["branch", "--show-current"]).strip()
    worktrees = _worktrees(root)
    local_branches = _local_branches(root, head_branch, worktrees)
    remote_branches = _remote_branches(root, head_branch)
    cleanup_candidates = _cleanup_candidates(worktrees, local_branches, remote_branches)
    dirty_worktrees = [item for item in worktrees if item["dirty_count"] > 0]
    dirty_extra_worktrees = [item for item in dirty_worktrees if not item["is_primary"]]
    gone_upstreams = [item for item in local_branches if item["upstream_gone"]]

    status = "PASSED"
    if cleanup_candidates or dirty_extra_worktrees or gone_upstreams:
        status = "NEEDS_CLEANUP"
    elif dirty_worktrees:
        status = "IN_PROGRESS"

    summary = {
        "repo_root": str(root),
        "head_branch": head_branch,
        "worktree_count": len(worktrees),
        "extra_worktree_count": sum(1 for item in worktrees if not item["is_primary"]),
        "dirty_worktree_count": len(dirty_worktrees),
        "local_branch_count": len(local_branches),
        "local_non_main_branch_count": sum(1 for item in local_branches if not item["is_main"]),
        "remote_branch_count": len(remote_branches),
        "remote_non_main_branch_count": sum(1 for item in remote_branches if not item["is_main"]),
        "local_gone_upstream_branch_count": len(gone_upstreams),
        "cleanup_candidate_count": len(cleanup_candidates),
        "destructive_actions_executed": False,
        "github_api_used": False,
        "network_used": False,
        "stores_secrets": False,
        "pr_status_checked": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "summary": summary,
        "worktrees": worktrees,
        "local_branches": local_branches,
        "remote_branches": remote_branches,
        "cleanup_candidates": cleanup_candidates,
        "next_step": _next_step(cleanup_candidates),
    }


def format_worktree_audit_text(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "NaC Git Worktree Audit",
        f"- Status: {payload['status']}",
        f"- Repository: {summary['repo_root']}",
        f"- Head branch: {summary['head_branch'] or '(detached)'}",
        f"- Worktrees: {summary['worktree_count']} ({summary['extra_worktree_count']} extra)",
        f"- Dirty worktrees: {summary['dirty_worktree_count']}",
        f"- Local branches: {summary['local_branch_count']} ({summary['local_non_main_branch_count']} non-main)",
        f"- Remote branches: {summary['remote_branch_count']} ({summary['remote_non_main_branch_count']} non-main)",
        f"- Gone upstream branches: {summary['local_gone_upstream_branch_count']}",
        f"- Cleanup candidates: {summary['cleanup_candidate_count']}",
        "- Destructive actions executed: false",
        "- GitHub API used: false",
        "- Network used: false",
    ]
    if payload["cleanup_candidates"]:
        lines.append("")
        lines.append("Cleanup candidates")
        for candidate in payload["cleanup_candidates"]:
            lines.append(
                f"- {candidate['type']}: {candidate['target']} "
                f"({candidate['reason']}; owner_gate_required=true)"
            )
    lines.append("")
    lines.append(f"Next step: {payload['next_step']}")
    return "\n".join(lines)


def _git_root(repo_root: Path) -> Path:
    result = _git(repo_root, ["rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def _worktrees(repo_root: Path) -> list[dict[str, Any]]:
    records = _parse_worktree_porcelain(_git(repo_root, ["worktree", "list", "--porcelain"]).stdout)
    primary_path = repo_root.resolve()
    items: list[dict[str, Any]] = []
    for record in records:
        path = Path(record.get("worktree", "")).resolve()
        branch_ref = record.get("branch", "")
        branch = branch_ref.removeprefix("refs/heads/")
        dirty_count = _dirty_count(path)
        is_primary = path == primary_path
        items.append(
            {
                "path": str(path),
                "branch": branch,
                "head": record.get("HEAD", ""),
                "is_primary": is_primary,
                "is_locked": "locked" in record,
                "is_prunable": "prunable" in record,
                "dirty_count": dirty_count,
                "cleanup_candidate": not is_primary and dirty_count == 0,
            }
        )
    return items


def _local_branches(repo_root: Path, head_branch: str, worktrees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    worktree_branches = {item["branch"] for item in worktrees if item["branch"]}
    main_ref = _main_ref(repo_root, remote=False)
    output = _git(
        repo_root,
        [
            "for-each-ref",
            "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)\t%(worktreepath)",
            "refs/heads",
        ],
    ).stdout
    branches: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        name, upstream, upstream_track, worktree_path = _split_tab(line, 4)
        is_main = name in PRIMARY_BRANCHES
        upstream_gone = "[gone]" in upstream_track
        cleanup_candidate = not is_main and name != head_branch
        if cleanup_candidate and name in worktree_branches:
            cleanup_reason = "non_main_branch_with_worktree_remove_worktree_first"
        elif upstream_gone:
            cleanup_reason = "gone_upstream_branch"
        elif cleanup_candidate:
            cleanup_reason = "local_non_main_branch"
        else:
            cleanup_reason = "none"
        ahead, behind = _ahead_behind(repo_root, main_ref, name)
        branches.append(
            {
                "name": name,
                "upstream": upstream,
                "upstream_gone": upstream_gone,
                "is_current": name == head_branch,
                "is_main": is_main,
                "ahead_of_main": ahead,
                "behind_main": behind,
                "has_worktree": bool(worktree_path) or name in worktree_branches,
                "cleanup_candidate": cleanup_candidate,
                "cleanup_reason": cleanup_reason,
                "owner_gate_required": cleanup_candidate,
            }
        )
    return sorted(branches, key=lambda item: item["name"])


def _remote_branches(repo_root: Path, head_branch: str) -> list[dict[str, Any]]:
    main_ref = _main_ref(repo_root, remote=True)
    output = _git_optional(
        repo_root,
        ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
    )
    branches: list[dict[str, Any]] = []
    for line in output.splitlines():
        name = line.strip()
        if not name or name in {"origin", "origin/HEAD"}:
            continue
        short_name = name.split("/", 1)[1] if "/" in name else name
        is_main = short_name in PRIMARY_BRANCHES
        cleanup_candidate = not is_main and short_name != head_branch
        ahead, behind = _ahead_behind(repo_root, main_ref, name)
        branches.append(
            {
                "name": name,
                "short_name": short_name,
                "is_main": is_main,
                "ahead_of_main": ahead,
                "behind_main": behind,
                "cleanup_candidate": cleanup_candidate,
                "cleanup_reason": "remote_non_main_needs_open_pr_check_before_delete"
                if cleanup_candidate
                else "none",
                "owner_gate_required": cleanup_candidate,
                "pr_status_checked": False,
            }
        )
    return sorted(branches, key=lambda item: item["name"])


def _cleanup_candidates(
    worktrees: list[dict[str, Any]],
    local_branches: list[dict[str, Any]],
    remote_branches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in worktrees:
        if item["cleanup_candidate"]:
            candidates.append(
                _candidate(
                    "worktree",
                    item["path"],
                    "extra_clean_worktree",
                    "remove_worktree",
                )
            )
    for item in local_branches:
        if item["cleanup_candidate"]:
            candidates.append(
                _candidate(
                    "local_branch",
                    item["name"],
                    item["cleanup_reason"],
                    "delete_local_branch",
                )
            )
    for item in remote_branches:
        if item["cleanup_candidate"]:
            candidates.append(
                _candidate(
                    "remote_branch",
                    item["name"],
                    item["cleanup_reason"],
                    "delete_remote_branch_after_open_pr_check",
                )
            )
    return candidates


def _candidate(kind: str, target: str, reason: str, suggested_action: str) -> dict[str, Any]:
    return {
        "type": kind,
        "target": target,
        "reason": reason,
        "suggested_action": suggested_action,
        "owner_gate_required": True,
        "destructive_action_executed": False,
    }


def _next_step(cleanup_candidates: list[dict[str, Any]]) -> str:
    if not cleanup_candidates:
        return "No cleanup candidate found; keep using worktrees only for isolated parallel branches."
    return "Review cleanup candidates, then request one owner-approved batch cleanup."


def _parse_worktree_porcelain(output: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def _dirty_count(worktree_path: Path) -> int:
    try:
        output = _git(worktree_path, ["status", "--porcelain"]).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0
    return sum(1 for line in output.splitlines() if line.strip())


def _main_ref(repo_root: Path, *, remote: bool) -> str:
    candidates = ("origin/main", "origin/master") if remote else ("main", "master")
    for candidate in candidates:
        if _git_optional(repo_root, ["rev-parse", "--verify", "--quiet", candidate]).strip():
            return candidate
    current = _git_optional(repo_root, ["branch", "--show-current"]).strip()
    return current or "HEAD"


def _ahead_behind(repo_root: Path, base: str, ref: str) -> tuple[int | None, int | None]:
    if not base or not ref or base == ref:
        return 0, 0
    result = _git_optional(repo_root, ["rev-list", "--left-right", "--count", f"{base}...{ref}"])
    parts = result.split()
    if len(parts) != 2:
        return None, None
    try:
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return None, None
    return ahead, behind


def _split_tab(line: str, fields: int) -> list[str]:
    parts = line.split("\t")
    if len(parts) < fields:
        parts.extend([""] * (fields - len(parts)))
    return parts[:fields]


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )


def _git_optional(repo_root: Path, args: list[str]) -> str:
    try:
        return _git(repo_root, args).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
