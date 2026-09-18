from __future__ import annotations
import argparse, json
from pathlib import Path
from app.db.migrate import main as migrate_main
from app.db import queries
from app.ingest.pipeline import ingest_text, ingest_file
from app.modules import REGISTRY
from app.factory.factory import seed_queue, run_next
from app.factory.catalog import export_catalog
from app.scheduler.task_worker import run_due, run_loop

def main():
    p = argparse.ArgumentParser(description="EmberVault Income Engine CLI (local-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("initdb")

    ing_t = sub.add_parser("ingest-text")
    ing_t.add_argument("--title", required=True)
    ing_t.add_argument("--text", required=True)
    ing_t.add_argument("--meta", default="{}")

    ing_f = sub.add_parser("ingest-file")
    ing_f.add_argument("--path", required=True)
    ing_f.add_argument("--meta", default="{}")

    gen = sub.add_parser("generate")
    gen.add_argument("--module", required=True, choices=list(REGISTRY.keys()))
    gen.add_argument("--topic", required=True)
    gen.add_argument("--constraints", default="{}")


    fac = sub.add_parser("factory-seed")
    fac.add_argument("--focus", required=True)
    fac.add_argument("--niches", default="")  # comma-separated
    fac.add_argument("--top_n", type=int, default=9)
    fac.add_argument("--priority", type=int, default=0)
    fac.add_argument("--no_schedule", action="store_true")

    sub.add_parser("factory-run-next")

    sub.add_parser("export-catalog")

    wr = sub.add_parser("worker-run-due")
    wr.add_argument("--max", type=int, default=3)

    wl = sub.add_parser("worker-loop")
    wl.add_argument("--poll", type=int, default=15)
    wl.add_argument("--batch", type=int, default=3)

    rl = sub.add_parser("runs-list")
    rl.add_argument("--status", default="")
    rl.add_argument("--limit", type=int, default=50)

    rg = sub.add_parser("runs-get")
    rg.add_argument("--run_id", type=int, required=True)

    args = p.parse_args()

    if args.cmd == "initdb":
        migrate_main()
        print("DB ready.")
        return

    if args.cmd == "ingest-text":
        meta = json.loads(args.meta)
        res = ingest_text(args.title, args.text, meta)
        print(json.dumps(res, indent=2))
        return

    if args.cmd == "ingest-file":
        meta = json.loads(args.meta)
        res = ingest_file(Path(args.path), Path(args.path).name, meta)
        print(json.dumps(res, indent=2))
        return


    if args.cmd == "factory-seed":
        niches = [x.strip() for x in (args.niches or "").split(",") if x.strip()] or None
        res = seed_queue(args.focus, niches=niches, top_n=int(args.top_n), priority=int(args.priority), schedule_fib=(not args.no_schedule))
        print(json.dumps(res, indent=2))
        return

    if args.cmd == "factory-run-next":
        res = run_next()
        print(json.dumps(res, indent=2))
        return

    if args.cmd == "export-catalog":
        res = export_catalog()
        print(json.dumps(res, indent=2))
        return

    if args.cmd == "worker-run-due":
        res = run_due(max_tasks=int(args.max))
        print(json.dumps(res, indent=2))
        return

    if args.cmd == "worker-loop":
        run_loop(poll_seconds=int(args.poll), batch=int(args.batch))
        return

    if args.cmd == "runs-list":
        rows = queries.list_runs(limit=int(args.limit), status=(args.status or None))
        print(json.dumps({"runs": rows}, indent=2))
        return

    if args.cmd == "runs-get":
        print(json.dumps(queries.get_run(int(args.run_id)), indent=2))
        return

    if args.cmd == "generate":
        c = json.loads(args.constraints)
        m = REGISTRY[args.module]
        res = m.generate(args.topic, c)
        print(json.dumps(res.__dict__, indent=2))
        return

if __name__ == "__main__":
    main()
