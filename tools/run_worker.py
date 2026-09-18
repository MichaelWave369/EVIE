from __future__ import annotations
import argparse
from app.db.migrate import main as migrate_main
from app.scheduler.task_worker import run_loop, run_due

def main():
    p = argparse.ArgumentParser(description="EmberVault task worker (local-only)")
    p.add_argument("--loop", action="store_true", help="Run continuously")
    p.add_argument("--poll", type=int, default=15)
    p.add_argument("--batch", type=int, default=3)
    p.add_argument("--once", action="store_true", help="Run due tasks once and exit")
    p.add_argument("--max", type=int, default=3)
    args = p.parse_args()

    migrate_main()

    if args.once and not args.loop:
        print(run_due(max_tasks=int(args.max)))
        return

    run_loop(poll_seconds=int(args.poll), batch=int(args.batch))

if __name__ == "__main__":
    main()
