from __future__ import annotations

from .cohort import start_cohort


def main() -> int:
    started = start_cohort()
    print(f"cohort={started.cohort_id} status={started.status} started_at={started.started_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
