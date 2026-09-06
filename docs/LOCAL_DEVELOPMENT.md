# Local development

## Supported runtime

- Python 3.11+
- WSL/Linux/macOS shell; equivalent commands work in PowerShell with an activated Python environment.

## Fresh-clone bootstrap

```bash
python -m venv .venv && source .venv/bin/activate && python -m pip install -e '.[dev]'
```

## One-command acceptance test

```bash
python -m pytest
```

The 5% → 10% gate is intentionally offline: tests require no API keys, no network calls and no broker configuration.

## Smoke commands

```bash
python -m engine.cli decide
python -m engine.cli evaluate
python -m engine.cli rebuild
```

At this stage these commands only verify stable interfaces. External providers are introduced in later gates.
