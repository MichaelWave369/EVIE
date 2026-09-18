from __future__ import annotations

import json
import os

from app.ops.smoke import run_smoke_tests


if __name__ == "__main__":
    topic = os.getenv("EV_SMOKE_TOPIC", "EVIE Smoke Topic")
    report = run_smoke_tests(topic=topic)
    print(json.dumps(report, indent=2))
