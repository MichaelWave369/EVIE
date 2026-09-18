from __future__ import annotations
import json, datetime, sqlite3
from app.db.schema import connect
from app.taxonomy.enums import DOMAINS, PHASES, STATES, LENSES, canonical_key

def seed_taxonomy() -> None:
    con = connect()
    now = datetime.datetime.utcnow().isoformat()
    # domains/phases/states
    con.executemany("INSERT OR REPLACE INTO taxonomy_domain(domain_id, domain_name) VALUES (?,?)",
                    [(k,v) for k,v in DOMAINS.items()])
    con.executemany("INSERT OR REPLACE INTO taxonomy_phase(phase_id, phase_name) VALUES (?,?)",
                    [(k,v) for k,v in PHASES.items()])
    con.executemany("INSERT OR REPLACE INTO taxonomy_state(state_id, state_name) VALUES (?,?)",
                    [(k,v) for k,v in STATES.items()])
    con.executemany(
        "INSERT OR REPLACE INTO taxonomy_lens(lens_id, lens_code, lens_name, lens_description, safety_tier, gate_profile, operator_default, allowed_outputs) VALUES (?,?,?,?,?,?,?,?)",
        [(l.id, l.code, l.name, l.description, l.safety_tier, l.gate_profile, l.operator_default, l.allowed_outputs) for l in LENSES.values()]
    )

    # seed cell rules with simple deterministic default from lens safety tier if full dataset not present
    rows = []
    cell_id = 1
    cell1728 = 1
    for d in DOMAINS:
        for p in PHASES:
            for s in STATES:
                for lid, lens in LENSES.items():
                    ck = canonical_key(d,p,s,lid)
                    rows.append((cell_id, cell1728, d,p,s,lid, ck, lens.safety_tier, lens.gate_profile, lens.operator_default, lens.allowed_outputs))
                    cell_id += 1
                cell1728 += 1

    con.executemany(
        "INSERT OR REPLACE INTO cell20736(cell20736_id, cell1728_id, domain_id, phase_id, state_id, lens_id, canonical_key, safety_tier, gate_profile, operator_default, allowed_outputs) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows
    )
    con.commit()
    con.close()

if __name__ == "__main__":
    seed_taxonomy()
    print("Seeded taxonomy + cell20736 fallback rules.")
