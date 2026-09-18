from __future__ import annotations
import json
from app.db.migrate import main as migrate_main
from app.factory.catalog import export_catalog

def main():
    migrate_main()
    res = export_catalog()
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
