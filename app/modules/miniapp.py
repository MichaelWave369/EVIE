from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import datetime, json
from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.security.crypto import encrypt_str, decrypt_str

def _get_key_dir() -> Path:
    d = Path(settings.data_dir) / "license_keys"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _get_or_create_ed25519_keypair() -> Dict[str, Path]:
    kd = _get_key_dir()
    priv_path = kd / "ed25519_private.pem.enc"
    pub_path = kd / "ed25519_public.pem"
    if priv_path.exists() and pub_path.exists():
        return {"private": priv_path, "public": pub_path}

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    # Encrypt private PEM with local Fernet key (stored in data/local_key.bin)
    priv_enc = encrypt_str(priv_pem)
    write_text(priv_path, priv_enc)
    write_text(pub_path, pub_pem)
    return {"private": priv_path, "public": pub_path}

def _load_private_key() -> ed25519.Ed25519PrivateKey:
    paths = _get_or_create_ed25519_keypair()
    priv_enc = Path(paths["private"]).read_text(encoding="utf-8")
    priv_pem = decrypt_str(priv_enc).encode("utf-8")
    return serialization.load_pem_private_key(priv_pem, password=None)

class MiniAppProductizerModule:
    """Generate a local-first mini-app product package:
    - license keys (signed)
    - SKU + pricing ladder
    - offline verify snippet
    - release notes + onboarding docs
    You plug in your actual app later (Tauri/Python/etc.)."""
    name = "miniapp"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        app_name = constraints.get("app_name", f"{topic} Mini-App")
        sku = constraints.get("sku", app_name.lower().replace(" ", "-")[:24])
        count = int(constraints.get("key_count", 25))
        tiers = constraints.get("tiers", [
            {"tier":"personal","price_cents":1900},
            {"tier":"commercial","price_cents":4900},
            {"tier":"enterprise","price_cents":19900},
        ])

        prompt = f"""Create a mini-app product spec, aligned to 369/Φ/Fib.

App name: {app_name}
Topic: {topic}
Include:
- Value proposition
- 3 core features, 6 supporting features, 9 automation hooks
- Packaging plan (installer, docs, license, changelog)
- 1/2/3/5/8 release roadmap
- Store listing copy + FAQ
"""
        spec = llm.chat([{"role":"user","content":prompt}])

        # Generate license keys (signed payloads)
        priv = _load_private_key()
        pub_paths = _get_or_create_ed25519_keypair()
        pub_pem = Path(pub_paths["public"]).read_text(encoding="utf-8")

        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(settings.data_dir) / "artifacts" / "miniapp" / f"{sku}__{ts}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # keys.csv
        rows = ["key_id,tier,license_key"]
        for i in range(count):
            tier = tiers[i % len(tiers)]["tier"]
            payload = {
                "key_id": f"{sku}-{ts}-{i:04d}",
                "sku": sku,
                "tier": tier,
                "issued_at_utc": datetime.datetime.utcnow().isoformat()+"Z",
            }
            payload_json = json.dumps(payload, separators=(",",":")).encode("utf-8")
            sig = priv.sign(payload_json)
            license_key = (payload_json.hex() + "." + sig.hex())
            rows.append(f"{payload['key_id']},{tier},{license_key}")

        write_text(out_dir / "keys.csv", "\n".join(rows))
        write_text(out_dir / "public_key.pem", pub_pem)
        write_text(out_dir / "PRODUCT_SPEC.md", spec)
        write_text(out_dir / "pricing.json", json.dumps({"sku": sku, "tiers": tiers}, indent=2))

        verify_snippet = f"""# Offline license verification (Python)
import json, binascii
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

PUB_PEM = open("public_key.pem","rb").read()
pub = serialization.load_pem_public_key(PUB_PEM)

def verify(license_key: str) -> dict:
    payload_hex, sig_hex = license_key.split(".")
    payload = bytes.fromhex(payload_hex)
    sig = bytes.fromhex(sig_hex)
    pub.verify(sig, payload)  # raises if invalid
    return json.loads(payload.decode("utf-8"))

# example:
# data = verify("<license_key>")
# print(data)
"""
        write_text(out_dir / "verify_license.py", verify_snippet)

        return ModuleResult(
            artifact_paths=[str(out_dir / "PRODUCT_SPEC.md"), str(out_dir / "keys.csv"), str(out_dir / "verify_license.py")],
            metadata={"topic": topic, "module": self.name, "sku": sku, "out_dir": str(out_dir)}
        )
