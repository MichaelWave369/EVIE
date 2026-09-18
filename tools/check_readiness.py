from __future__ import annotations

import json

from app.ops.readiness import run_readiness_checks


if __name__ == "__main__":
    report = run_readiness_checks()
    print(json.dumps(report, indent=2))
