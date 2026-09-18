from __future__ import annotations
from app.db.schema import init_db
from app.db.seed_taxonomy import seed_taxonomy

def main():
    init_db()
    seed_taxonomy()
    print("DB initialized.")

if __name__ == "__main__":
    main()
