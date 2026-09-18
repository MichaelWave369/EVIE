from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.settings import settings
from app.db import queries
from app.export.packager import package_bundle, write_text
from app.security.redact import redact_text, redact_obj


def _out_dir() -> Path:
    d = Path(settings.data_dir) / "exports" / "packets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (s or "packet"))[:80]


def _pdf_write_lines(c: canvas.Canvas, lines: List[str], x: float, y: float, leading: float = 14) -> float:
    for line in lines:
        c.drawString(x, y, line[:160])
        y -= leading
        if y < 0.75 * inch:
            c.showPage()
            y = letter[1] - 1.0 * inch
    return y


def build_product_packet(product_id: int, *, redact: bool = True) -> Dict[str, Any]:
    """Build a shareable packet for a product.

    Output:
      - PDF overview (sales + audit summary)
      - JSON manifest (provenance)
      - ZIP bundle containing the packet + attached assets

    NOTE: This is local-only; paths are inside EVIE's data_dir.
    """
    p = queries.get_product(int(product_id))
    assets = queries.list_assets(int(product_id))
    versions = queries.list_product_versions(int(product_id))
    evidence = []
    try:
        evidence = queries.list_evidence(product_id=int(product_id), limit=200)
    except Exception:
        evidence = []

    # Redact sensitive fields for shareable exports
    p_out = redact_obj(p) if redact else p
    assets_out = redact_obj(assets) if redact else assets
    versions_out = redact_obj(versions) if redact else versions
    evidence_out = redact_obj(evidence) if redact else evidence

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = f"{_safe_name(p.get('sku') or 'product')}_{ts}"

    out_dir = _out_dir()
    pdf_path = out_dir / f"{base}.pdf"
    manifest_path = out_dir / f"{base}.manifest.json"

    manifest = {
        "type": "evie_product_packet",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "redacted": bool(redact),
        "product": p_out,
        "assets": assets_out,
        "versions": versions_out,
        "evidence": evidence_out,
    }
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    # --- PDF ---
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter

    c.setTitle(f"EVIE Product Packet — {p.get('name') or p.get('sku')}")

    y = h - 1.0 * inch
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1.0 * inch, y, "EVIE Product Packet")
    y -= 0.35 * inch

    c.setFont("Helvetica", 11)
    y = _pdf_write_lines(
        c,
        [
            f"Generated: {datetime.datetime.utcnow().isoformat()} UTC",
            f"SKU: {redact_text(str(p.get('sku') or '')) if redact else (p.get('sku') or '')}",
            f"Name: {redact_text(str(p.get('name') or '')) if redact else (p.get('name') or '')}",
            f"Module: {p.get('module') or ''}",
            f"Status: {p.get('status') or ''}",
            f"Price (cents): {p.get('price_cents')}",
        ],
        1.0 * inch,
        y,
    )

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Description")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)
    desc = p.get("description") or ""
    if redact:
        desc = redact_text(desc)
    y = _pdf_write_lines(c, (desc.splitlines() or [""])[:80], 1.0 * inch, y)

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Assets")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)
    if assets_out:
        lines = [f"- {a.get('asset_type')}: {a.get('path')}" for a in assets_out]
    else:
        lines = ["(none)"]
    y = _pdf_write_lines(c, lines, 1.0 * inch, y)

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Versions")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)
    if versions_out:
        lines = [f"- {v.get('version')}: {v.get('bundle_zip')}" for v in versions_out]
    else:
        lines = ["(none)"]
    y = _pdf_write_lines(c, lines, 1.0 * inch, y)

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Evidence")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)
    if evidence_out:
        lines = [f"- [{e.get('kind')}] {e.get('title')}" for e in evidence_out[:60]]
    else:
        lines = ["(none)"]
    y = _pdf_write_lines(c, lines, 1.0 * inch, y)

    c.showPage()
    c.save()

    # --- ZIP ---
    files: List[Path] = [pdf_path, manifest_path]

    # Attach any asset files that live under data_dir
    data_dir = Path(settings.data_dir).resolve()
    for a in assets:
        try:
            pth = Path(str(a.get("path") or "")).resolve()
            if str(pth).startswith(str(data_dir)) and pth.exists() and pth.is_file():
                files.append(pth)
        except Exception:
            continue

    zip_path = package_bundle(f"packet_{_safe_name(p.get('sku') or 'product')}", files)

    return {
        "pdf_path": str(pdf_path),
        "manifest_path": str(manifest_path),
        "zip_path": str(zip_path),
        "redacted": bool(redact),
    }
