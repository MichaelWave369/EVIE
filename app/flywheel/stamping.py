from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple
import datetime
import hashlib
import hmac
import json

from PIL import Image, ImageDraw, ImageFont

from app.settings import settings
from app.security.crypto import get_local_secret


_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
_TEXT_EXTS = {".md", ".txt"}

def _license_text_for_tier(sku: str, version: str, tier: str, rules: Dict[str, Any] | None = None) -> str:
    """
    Produce a local license text based on a SKU tier.

    Tiers are an internal convention (entry/core/premium/resale/enterprise).
    You can override clauses via `rules`:
      rules = { "entry": {"title": "...", "bullets": [...], "redistribution": "..."} , ... }
    """
    tier = (tier or "core").lower().strip()
    rules = rules or {}
    r = rules.get(tier) or {}

    title = r.get("title") or f"License — {sku} ({version}) — {tier.upper()} tier"
    bullets = r.get("bullets")

    # Safe defaults (non-legal template). Keep clear and conservative.
    defaults = {
        "entry": [
            "Personal use: allowed.",
            "Commercial use: allowed for finished works you publish/sell.",
            "Redistribution of raw source files: not allowed.",
            "Resale rights: not included."
        ],
        "core": [
            "Personal use: allowed.",
            "Commercial use: allowed for finished works you publish/sell, including client work.",
            "Redistribution of raw source files: not allowed.",
            "Resale rights: not included (unless you explicitly grant it)."
        ],
        "premium": [
            "Personal use: allowed.",
            "Commercial use: allowed for finished works you publish/sell, including client work.",
            "Internal team use: allowed.",
            "Redistribution of raw source files: not allowed.",
            "Resale rights: not included by default."
        ],
        "resale": [
            "Personal use: allowed.",
            "Commercial use: allowed.",
            "Resale of this bundle as a packaged product: allowed, if you preserve license + proof files.",
            "Redistribution of individual raw files outside the bundle: not allowed.",
            "No implication of endorsement; you are responsible for your storefront claims."
        ],
        "enterprise": [
            "Personal use: allowed.",
            "Commercial use: allowed, including internal and client deliverables.",
            "Team-wide use: allowed.",
            "Redistribution of raw source files: only as explicitly permitted in your internal policy.",
            "Resale rights: by agreement."
        ],
    }
    tier_bullets = bullets or defaults.get(tier) or defaults["core"]

    redistribution = r.get("redistribution") or ""
    attribution = r.get("attribution") or "Optional but appreciated: include `EV369 • Φ • Fib` as a tiny credit line."
    disclaimer = r.get("disclaimer") or "This is a template license generated locally. Review and adapt for your needs."

    return (
        f"# {title}\n\n"
        f"{disclaimer}\n\n"
        "## Permissions (summary)\n"
        + "\n".join([f"- {b}" for b in tier_bullets]) + "\n\n"
        + (f"## Redistribution notes\n{redistribution}\n\n" if redistribution else "")
        + "## Attribution\n"
        + f"{attribution}\n\n"
        "## Integrity\n"
        "See `FINGERPRINTS.sha256` + `PROOF_OF_CREATION.json` for file hashes and a local integrity seal.\n"
    )



def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hmac_seal(lines: List[str]) -> str:
    secret = get_local_secret()
    msg = "\n".join(lines).encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _try_stamp_text(p: Path, stamp_line: str) -> bool:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    marker = "<!-- EV369_STAMP -->"
    if marker in txt:
        return False
    footer = (
        "\n\n---\n"
        f"<!-- EV369_STAMP -->\n"
        f"{stamp_line}\n"
        "---\n"
    )
    try:
        p.write_text(txt + footer, encoding="utf-8")
        return True
    except Exception:
        return False


def _watermark_image(src: Path, dst: Path, text: str) -> bool:
    try:
        img = Image.open(src).convert("RGBA")
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        font = ImageFont.load_default()
        pad = max(12, int(min(w, h) * 0.015))
        # Bottom-right anchor
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = max(pad, w - tw - pad)
        y = max(pad, h - th - pad)
        # Subtle shadow
        d.text((x + 1, y + 1), text, fill=(0, 0, 0, 120), font=font)
        d.text((x, y), text, fill=(255, 255, 255, 170), font=font)
        out = Image.alpha_composite(img, overlay)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.convert("RGBA").save(dst)
        return True
    except Exception:
        return False


def stamp_artifacts(
    sku: str,
    version: str,
    artifact_paths: List[str],
    topic_slug: str,
    tier: str = "core",
    tier_rules: Dict[str, Any] | None = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Create licensing + proof-of-creation artifacts.

    - Records SHA256 for every artifact
    - Creates a local HMAC seal using a per-machine secret
    - Adds optional text-file footer stamps
    - Creates watermarked copies of image artifacts (does not overwrite originals)

    Returns (new_artifact_paths, metadata)
    """
    stamp_root = Path(settings.data_dir) / "artifacts" / "licensing_stamps" / topic_slug / version
    stamp_root.mkdir(parents=True, exist_ok=True)

    stamp_label = f"{sku} {version} | 369 • Φ • Fib"
    now = datetime.datetime.utcnow().isoformat()

    records: List[Dict[str, Any]] = []
    stamped_text_count = 0
    watermarked: List[str] = []

    # Compute fingerprints
    for s in artifact_paths:
        if not s:
            continue
        p = Path(s)
        if not p.exists() or not p.is_file():
            continue
        rel = None
        try:
            rel = str(p.relative_to(Path(settings.data_dir))).replace("\\", "/")
        except Exception:
            rel = str(p.name)
        h = sha256_file(p)
        records.append({"path": rel, "sha256": h, "bytes": p.stat().st_size})

        # Optional text footer (non-destructive? we do modify .md/.txt in-place)
        if p.suffix.lower() in _TEXT_EXTS:
            if _try_stamp_text(p, stamp_label):
                stamped_text_count += 1

        # Watermarked copies for images
        if p.suffix.lower() in _IMAGE_EXTS:
            wm_name = p.stem + "__watermarked" + p.suffix.lower()
            dst = stamp_root / "watermarked" / wm_name
            if _watermark_image(p, dst, stamp_label):
                watermarked.append(str(dst))

    # Stable seal based on sorted lines
    lines = [f"{r['path']} {r['sha256']}" for r in sorted(records, key=lambda x: x["path"])]
    seal = _hmac_seal(lines)

    # Write fingerprints
    sha_path = stamp_root / "FINGERPRINTS.sha256"
    sha_text = "\n".join(lines) + "\n"
    sha_path.write_text(sha_text, encoding="utf-8")

    proof = {
        "sku": sku,
        "version": version,
        "tier": tier,

        "created_at": now,
        "alignment": "369 • Φ • Fib",
        "record_count": len(records),
        "hmac_seal_sha256": seal,
        "records": records,
    }
    proof_path = stamp_root / "PROOF_OF_CREATION.json"
    proof_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    license_md = _license_text_for_tier(sku=sku, version=version, tier=tier, rules=tier_rules)
    lic_path = stamp_root / "LICENSE.md"
    lic_path.write_text(license_md, encoding="utf-8")

    report = (
        f"# Stamping Report\n\n"
        f"SKU: **{sku}**\n\n"
        f"Version: **{version}**\n\n"
        f"Tier: **{tier}**\n\n"
        f"Created: {now}\n\n"
        f"Artifacts hashed: **{len(records)}**\n\n"
        f"Text files stamped (footer): **{stamped_text_count}**\n\n"
        f"Watermarked image copies: **{len(watermarked)}**\n\n"
        f"Integrity seal (HMAC-SHA256): `{seal}`\n"
    )
    rep_path = stamp_root / "STAMP_REPORT.md"
    rep_path.write_text(report, encoding="utf-8")

    new_paths = [str(lic_path), str(sha_path), str(proof_path), str(rep_path)] + watermarked
    meta = {
        "stamp_root": str(stamp_root),
        "record_count": len(records),
        "stamped_text": stamped_text_count,
        "watermarked_images": len(watermarked),
        "seal": seal,
    }
    return new_paths, meta
