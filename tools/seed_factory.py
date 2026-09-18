from __future__ import annotations
import argparse, json
from app.db.migrate import main as migrate_main
from app.factory.factory import seed_queue

def main():
    p = argparse.ArgumentParser(description="Seed a 9-pack product queue (local-only)")
    p.add_argument("--focus", required=True)
    p.add_argument("--niches", default="")
    p.add_argument("--top_n", type=int, default=9)
    p.add_argument("--priority", type=int, default=0)
    p.add_argument("--no_schedule", action="store_true")
    args = p.parse_args()

    migrate_main()
    niches = [x.strip() for x in (args.niches or "").split(",") if x.strip()] or None
    res = seed_queue(args.focus, niches=niches, top_n=int(args.top_n), priority=int(args.priority), schedule_fib=(not args.no_schedule))
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
