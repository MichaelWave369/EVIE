from __future__ import annotations

from typing import Dict, Any, List

from app.modules.base import ModuleResult
from app.flywheel.slug import slugify
from app.flywheel.stamping import stamp_artifacts


class LicensingStamperModule:
    """Creates a proof-of-creation + licensing stamp pack for a set of artifacts.

    Constraints:
    - artifact_paths: list[str] (required)
    - sku: optional sku override
    - version: optional version override

    This module is also invoked automatically during Flywheel offer builds.
    """

    name = "licensing_stamper"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        artifact_paths: List[str] = list(constraints.get("artifact_paths") or [])
        sku = str(constraints.get("sku") or f"EV369-{slugify(topic)}")
        version = str(constraints.get("version") or "draft")
        topic_slug = slugify(topic)

        new_paths, meta = stamp_artifacts(
            sku=sku,
            version=version,
            artifact_paths=artifact_paths,
            topic_slug=topic_slug,
        )
        return ModuleResult(artifact_paths=new_paths, metadata={"sku": sku, "version": version, **meta})
