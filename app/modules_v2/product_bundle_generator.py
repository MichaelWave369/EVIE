from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import ensure_dir, write_text, write_json
import os, shutil

BUCKETS = ["ebooks","templates","newsletter","youtube","seo","pod","software","storefront","legal","visuals","misc"]

class ProductBundleGenerator:
    name = "product_bundle_generator"

    def _bucket_for(self, module_name: str) -> str:
        bucket = "misc"
        if "seo" in module_name:
            bucket = "seo"
        if "pod" in module_name:
            bucket = "pod"
        if "creative" in module_name:
            bucket = "visuals"
        if "storefront" in module_name:
            bucket = "storefront"
        if "license" in module_name or "support" in module_name:
            bucket = "legal"
        if "funnel" in module_name or "conversion" in module_name or "offer" in module_name:
            bucket = "templates"
        return bucket

    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        # IMPORTANT: write the SKU pack OUTSIDE the artifacts tree to avoid recursive self-copy.
        out_dir = f"{run_folder}/artifacts/{self.name}"
        ensure_dir(out_dir)

        bundle_root = os.path.join(run_folder, "sku_pack")
        bundle_dir = os.path.join(bundle_root, f"sku_pack__{sku}__{tier}")
        if os.path.exists(bundle_dir):
            shutil.rmtree(bundle_dir)
        for b in BUCKETS:
            os.makedirs(os.path.join(bundle_dir, b), exist_ok=True)

        art_root = os.path.join(run_folder, "artifacts")
        if os.path.isdir(art_root):
            for mod in os.listdir(art_root):
                if mod == self.name:
                    continue
                src = os.path.join(art_root, mod)
                if not os.path.isdir(src):
                    continue
                bucket = self._bucket_for(mod)
                dst = os.path.join(bundle_dir, bucket, mod)
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # Manifest
        write_text(os.path.join(bundle_dir, "README.md"), f"SKU pack for {sku} ({tier})\n")
        manifest = {"sku": sku, "tier": tier, "bundle_dir": bundle_dir, "buckets": BUCKETS}
        write_json(os.path.join(bundle_dir, "manifest.json"), manifest)

        # Pointer file inside artifacts (small)
        write_json(os.path.join(out_dir, "sku_pack_pointer.json"), {"bundle_dir": bundle_dir})
        return ModuleResult(name=self.name, artifacts=[os.path.join(out_dir, "sku_pack_pointer.json"), bundle_dir], summary={"bundle_dir": bundle_dir})
