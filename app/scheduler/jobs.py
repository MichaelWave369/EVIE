from __future__ import annotations
import datetime, json
from typing import Dict, Any, List
from app.db.schema import connect
from app.db import queries
from app.taxonomy.enums import FIB_DAYS

# 3 Pillars / 6 Loops / 9 Bots (encoded as labels for task routing)
PILLARS = ["create", "distribute", "compound"]
LOOPS = ["research", "build", "publish", "convert", "deliver", "optimize"]
BOTS = ["intake", "index", "outline", "draft", "package", "schedule", "storefront", "support", "analytics"]

def enqueue_task(module: str, task_type: str, payload: Dict[str, Any], schedule_at: str | None = None, run_id: int | None = None) -> int:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    try:
        cur = con.execute(
            "INSERT INTO tasks(module, task_type, payload_json, schedule_at, status, created_at, run_id) VALUES (?,?,?,?,?,?,?)",
            (module, task_type, json.dumps(payload, ensure_ascii=False), schedule_at, "queued", now, run_id),
        )
    except Exception:
        # backward-compatible if run_id column doesn't exist
        cur = con.execute(
            "INSERT INTO tasks(module, task_type, payload_json, schedule_at, status, created_at) VALUES (?,?,?,?,?,?)",
            (module, task_type, json.dumps(payload, ensure_ascii=False), schedule_at, "queued", now),
        )
    tid = int(cur.lastrowid)
    con.commit()
    con.close()
    return tid

def daily_analytics_capsule():
    # placeholder: summarize recent audit/task activity and store as a document later
    queries.log_audit("system", "daily_analytics_capsule", None, None, {"note": "stub"})

def fib_publish_plan(seed_date: datetime.date | None = None) -> List[datetime.date]:
    d0 = seed_date or datetime.date.today()
    return [d0 + datetime.timedelta(days=n) for n in FIB_DAYS]
