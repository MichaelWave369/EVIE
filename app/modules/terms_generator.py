from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import datetime

from app.modules.base import ModuleResult
from app.rag.llm import LLM
from app.settings import settings
from app.export.packager import write_text


class TermsGeneratorModule:
    """License/Terms generator (local-only).

    Produces:
    - Personal / Commercial / Resale license terms
    - Refund policy template
    - Privacy policy template (local-first)
    - Disclaimers (no guarantees, informational only)
    - Affiliate disclosure snippet (optional)

    NOTE: This is not legal advice. These are drafts you should review.
    """

    name = "terms_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        llm = LLM.from_settings()
        brand = constraints.get("brand", "EmberVault")
        product_type = constraints.get("product_type", "digital download")
        jurisdiction = constraints.get("jurisdiction", "US-CA")
        allow_commercial = bool(constraints.get("allow_commercial", True))
        allow_resale = bool(constraints.get("allow_resale", False))
        support_email = constraints.get("support_email", "support@example.com")

        prompt = f"""Draft licensing + terms documents for a {product_type}.

Brand: {brand}
Product/topic: {topic}
Jurisdiction: {jurisdiction}
Commercial use allowed: {allow_commercial}
Resale allowed: {allow_resale}
Support contact: {support_email}

Write 369 aligned docs:
1) Personal License Terms (simple, plain English)
2) Commercial License Terms (if allowed, else include 'not offered')
3) Resale/Redistribution Terms (if allowed, else include 'not offered')
4) Refund Policy (clear; no guarantees; digital download policies)
5) Privacy Policy for local-first app (what data is stored locally; no cloud by default)
6) Disclaimers (informational; no financial guarantees; user responsibility)
7) Affiliate Disclosure snippet (if affiliate links may be used)

Rules:
- Keep each doc concise but usable
- Add a "Not legal advice" notice at the top
- Avoid aggressive/unsafe claims
- Include a '369 • Φ • Fib alignment' footer note (branding only)

Return in markdown, separated with headings:
## PERSONAL_LICENSE
## COMMERCIAL_LICENSE
## RESALE_LICENSE
## REFUND_POLICY
## PRIVACY_POLICY
## DISCLAIMERS
## AFFILIATE_DISCLOSURE
"""

        text = llm.chat([{"role": "user", "content": prompt}])

        # Split into sections
        def _extract(section: str) -> str:
            marker = f"## {section}"
            if marker not in text:
                return f"# {section.replace('_',' ').title()}\n\n(LLM backend disabled or section missing.)\n"
            part = text.split(marker, 1)[1]
            # until next ## 
            next_idx = part.find("\n## ")
            body = part if next_idx == -1 else part[:next_idx]
            return f"# {section.replace('_',' ').title()}\n\n{body.strip()}\n"

        out_dir = Path(settings.data_dir) / "artifacts" / "terms"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        personal = out_dir / f"personal_license__{ts}.md"
        commercial = out_dir / f"commercial_license__{ts}.md"
        resale = out_dir / f"resale_license__{ts}.md"
        refund = out_dir / f"refund_policy__{ts}.md"
        privacy = out_dir / f"privacy_policy__{ts}.md"
        disclaimers = out_dir / f"disclaimers__{ts}.md"
        affiliate = out_dir / f"affiliate_disclosure__{ts}.md"
        pack = out_dir / f"terms_pack__{ts}.md"

        write_text(personal, _extract("PERSONAL_LICENSE"))
        write_text(commercial, _extract("COMMERCIAL_LICENSE"))
        write_text(resale, _extract("RESALE_LICENSE"))
        write_text(refund, _extract("REFUND_POLICY"))
        write_text(privacy, _extract("PRIVACY_POLICY"))
        write_text(disclaimers, _extract("DISCLAIMERS"))
        write_text(affiliate, _extract("AFFILIATE_DISCLOSURE"))
        write_text(pack, text)

        return ModuleResult(
            artifact_paths=[
                str(pack),
                str(personal),
                str(commercial),
                str(resale),
                str(refund),
                str(privacy),
                str(disclaimers),
                str(affiliate),
            ],
            metadata={"topic": topic, "module": self.name, "brand": brand, "jurisdiction": jurisdiction},
        )
