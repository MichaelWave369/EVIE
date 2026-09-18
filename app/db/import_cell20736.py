from __future__ import annotations
import csv
from pathlib import Path
from app.db.schema import connect

def import_cell20736_csv(csv_path: Path) -> None:
    con = connect()
    # Expect columns: Cell20736ID, Cell1728ID, DomainID, PhaseID, StateID, LensID, CanonicalKey, SafetyTier, GateProfile, OperatorDefault, AllowedOutputs
    with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append((
                int(r["Cell20736ID"]),
                int(r.get("Cell1728ID") or 0),
                int(r["DomainID"]),
                int(r["PhaseID"]),
                int(r["StateID"]),
                int(r["LensID"]),
                r["CanonicalKey"],
                int(r.get("SafetyTier") or 0),
                r.get("GateProfile"),
                r.get("OperatorDefault"),
                r.get("AllowedOutputs"),
            ))
    con.executemany(
        """INSERT OR REPLACE INTO cell20736(
            cell20736_id, cell1728_id, domain_id, phase_id, state_id, lens_id,
            canonical_key, safety_tier, gate_profile, operator_default, allowed_outputs
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        rows
    )
    con.commit()
    con.close()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Path to Cell20736.csv")
    args = p.parse_args()
    import_cell20736_csv(Path(args.csv))
    print("Imported Cell20736 rules.")
