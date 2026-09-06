from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

from .public_data import build_public_dashboard

SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?:OPENAI_API_KEY|ALPACA_API_KEY|ALPACA_API_SECRET)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
        re.I,
    ),
)

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".js", ".css", ".html"
}


def scan_repository(root: str | Path) -> list[str]:
    root = Path(root)
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(text):
                findings.append(f"{path.relative_to(root)} matched {pattern.pattern}")
    return findings


def assert_repository_secret_free(root: str | Path) -> None:
    findings = scan_repository(root)
    if findings:
        raise RuntimeError("potential committed secret values found:\n" + "\n".join(findings))


def assert_dashboard_rebuild(
    *,
    decisions_path: str | Path = "data/decisions.jsonl",
    evaluations_path: str | Path = "data/evaluations.jsonl",
    health_path: str | Path = "data/health.json",
    committed_dashboard_path: str | Path = "data/public/dashboard.json",
) -> None:
    committed = Path(committed_dashboard_path)
    if not committed.exists():
        raise RuntimeError("committed public dashboard is missing")
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "dashboard.json"
        build_public_dashboard(
            decisions_path=decisions_path,
            evaluations_path=evaluations_path,
            health_path=health_path,
            output_path=rebuilt,
        )
        if rebuilt.read_bytes() != committed.read_bytes():
            raise RuntimeError("dashboard rebuild differs from committed public artifact")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args()
    assert_repository_secret_free(args.repo_root)
    if not args.skip_rebuild:
        assert_dashboard_rebuild()
    print("hardening=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
