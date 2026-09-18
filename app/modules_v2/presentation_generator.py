"""
EVIE Presentation Generator Module
Generates beautiful PPTX slide decks from any topic or ingested content.
Drop this file into: D:/EVIEv4.0/app/modules_v2/presentation_generator.py
"""

import subprocess
import json
import os
import tempfile
import shutil
from pathlib import Path
from app.modules.base import BaseModule
from .base import ModuleResult


PPTX_SCRIPT_TEMPLATE = """
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const TOPIC = {topic_json};
const SLIDES = {slides_json};
const THEME = {theme_json};

const makeShadow = () => ({{ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.15 }});

let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = THEME.author || 'EVIE — EmberVault Income Engine';
pres.title = TOPIC;

function hexColor(c) {{ return c.replace('#',''); }}

const PRIMARY = hexColor(THEME.primary || '2D1B4E');
const ACCENT = hexColor(THEME.accent || 'C9952C');
const LIGHT = hexColor(THEME.light || 'F0EBF8');
const WHITE = 'FFFFFF';
const DARK_TEXT = '1C1C1C';

// TITLE SLIDE
let title_slide = pres.addSlide();
title_slide.background = {{ color: PRIMARY }};

title_slide.addShape(pres.shapes.RECTANGLE, {{
  x: 0, y: 0, w: 0.18, h: 5.625,
  fill: {{ color: ACCENT }}, line: {{ color: ACCENT }}
}});

title_slide.addText(THEME.brand || '', {{
  x: 0.5, y: 0.5, w: 9, h: 0.4,
  fontSize: 10, color: ACCENT, bold: true, fontFace: "Calibri",
  charSpacing: 4
}});

const titleWords = TOPIC.split(' ');
const midpoint = Math.ceil(titleWords.length / 2);
const line1 = titleWords.slice(0, midpoint).join(' ');
const line2 = titleWords.slice(midpoint).join(' ');

title_slide.addText(line1, {{
  x: 0.5, y: 1.1, w: 8.5, h: 1.0,
  fontSize: 48, color: WHITE, bold: true, fontFace: "Georgia"
}});

if (line2) {{
  title_slide.addText(line2, {{
    x: 0.5, y: 2.0, w: 8.5, h: 1.0,
    fontSize: 48, color: ACCENT, bold: true, fontFace: "Georgia"
  }});
}}

title_slide.addText(THEME.subtitle || '', {{
  x: 0.5, y: 3.3, w: 9, h: 0.45,
  fontSize: 14, color: 'B8A0D4', italic: true, fontFace: "Calibri"
}});

title_slide.addShape(pres.shapes.RECTANGLE, {{
  x: 0, y: 5.1, w: 10, h: 0.525,
  fill: {{ color: ACCENT, transparency: 85 }}, line: {{ color: ACCENT, transparency: 85 }}
}});

title_slide.addText(THEME.url || '', {{
  x: 0.5, y: 5.1, w: 9, h: 0.525,
  fontSize: 11, color: 'D4B86A', fontFace: "Calibri", valign: "middle"
}});

// CONTENT SLIDES
SLIDES.forEach((slide_data, idx) => {{
  let slide = pres.addSlide();

  // Different layouts based on slide type
  const layout = slide_data.layout || 'standard';

  if (layout === 'section') {{
    // Full dark section header slide
    slide.background = {{ color: PRIMARY }};

    slide.addShape(pres.shapes.RECTANGLE, {{
      x: 0, y: 2.1, w: 10, h: 0.06,
      fill: {{ color: ACCENT, transparency: 40 }}, line: {{ color: ACCENT, transparency: 40 }}
    }});

    slide.addText(slide_data.number || String(idx + 1).padStart(2, '0'), {{
      x: 0.5, y: 1.0, w: 9, h: 0.8,
      fontSize: 52, color: ACCENT, bold: true, fontFace: "Georgia", align: "center"
    }});

    slide.addText(slide_data.title, {{
      x: 0.5, y: 1.85, w: 9, h: 0.7,
      fontSize: 26, color: WHITE, bold: true, fontFace: "Georgia", align: "center"
    }});

    if (slide_data.subtitle) {{
      slide.addText(slide_data.subtitle, {{
        x: 0.5, y: 2.7, w: 9, h: 0.5,
        fontSize: 15, color: 'B8A0D4', italic: true, fontFace: "Calibri", align: "center"
      }});
    }}

    if (slide_data.body) {{
      slide.addText(slide_data.body, {{
        x: 1.5, y: 3.4, w: 7, h: 1.5,
        fontSize: 14, color: 'D0C0E8', fontFace: "Calibri", align: "center"
      }});
    }}

  }} else if (layout === 'cards') {{
    // Grid of cards layout
    slide.background = {{ color: 'FDFAF5' }};

    slide.addShape(pres.shapes.RECTANGLE, {{
      x: 0, y: 0, w: 10, h: 0.82,
      fill: {{ color: PRIMARY }}, line: {{ color: PRIMARY }}
    }});

    slide.addText(slide_data.title, {{
      x: 0.4, y: 0, w: 9.2, h: 0.82,
      fontSize: 20, color: ACCENT, bold: true, fontFace: "Georgia",
      align: "left", valign: "middle", charSpacing: 2
    }});

    const items = slide_data.items || [];
    const cols = items.length <= 3 ? items.length : 3;
    const rows = Math.ceil(items.length / cols);
    const cardW = (9.2 / cols) - 0.15;
    const cardH = rows === 1 ? 3.8 : 1.9;

    items.forEach((item, i) => {{
      const col = i % cols;
      const row = Math.floor(i / cols);
      const x = 0.3 + col * (cardW + 0.18);
      const y = 1.0 + row * (cardH + 0.18);

      slide.addShape(pres.shapes.RECTANGLE, {{
        x, y, w: cardW, h: cardH,
        fill: {{ color: i % 2 === 0 ? LIGHT : WHITE }},
        line: {{ color: 'D4C5E8' }},
        shadow: makeShadow()
      }});

      if (item.icon) {{
        slide.addText(item.icon, {{
          x, y: y + 0.1, w: cardW, h: 0.55,
          fontSize: 24, align: "center"
        }});
      }}

      slide.addText(item.title || item, {{
        x: x + 0.1, y: y + (item.icon ? 0.6 : 0.15), w: cardW - 0.2, h: 0.45,
        fontSize: 13, color: PRIMARY, bold: true, fontFace: "Georgia", align: "center"
      }});

      if (item.body) {{
        slide.addText(item.body, {{
          x: x + 0.12, y: y + (item.icon ? 1.05 : 0.65), w: cardW - 0.24, h: cardH - (item.icon ? 1.15 : 0.75),
          fontSize: 11, color: DARK_TEXT, fontFace: "Calibri", align: "center"
        }});
      }}
    }});

  }} else if (layout === 'bullets') {{
    // Standard bullets layout
    slide.background = {{ color: 'FDFAF5' }};

    slide.addShape(pres.shapes.RECTANGLE, {{
      x: 0, y: 0, w: 10, h: 0.82,
      fill: {{ color: PRIMARY }}, line: {{ color: PRIMARY }}
    }});

    slide.addText(slide_data.title, {{
      x: 0.4, y: 0, w: 9.2, h: 0.82,
      fontSize: 20, color: ACCENT, bold: true, fontFace: "Georgia",
      align: "left", valign: "middle", charSpacing: 2
    }});

    if (slide_data.intro) {{
      slide.addText(slide_data.intro, {{
        x: 0.5, y: 1.0, w: 9, h: 0.5,
        fontSize: 13, color: '444444', italic: true, fontFace: "Calibri"
      }});
    }}

    const bullets = slide_data.bullets || [];
    const bulletItems = bullets.map((b, bi) => ({{
      text: (typeof b === 'string' ? b : b.text),
      options: {{ bullet: true, breakLine: bi < bullets.length - 1, fontSize: 13, color: DARK_TEXT }}
    }}));

    if (bulletItems.length > 0) {{
      slide.addText(bulletItems, {{
        x: 0.6, y: slide_data.intro ? 1.6 : 1.1, w: 8.8, h: 3.8,
        fontFace: "Calibri"
      }});
    }}

  }} else {{
    // Standard two-column or body layout
    slide.background = {{ color: 'FDFAF5' }};

    slide.addShape(pres.shapes.RECTANGLE, {{
      x: 0, y: 0, w: 10, h: 0.82,
      fill: {{ color: PRIMARY }}, line: {{ color: PRIMARY }}
    }});

    slide.addText(slide_data.title, {{
      x: 0.4, y: 0, w: 9.2, h: 0.82,
      fontSize: 20, color: ACCENT, bold: true, fontFace: "Georgia",
      align: "left", valign: "middle", charSpacing: 2
    }});

    if (slide_data.body) {{
      slide.addText(slide_data.body, {{
        x: 0.5, y: 1.0, w: 9, h: 4.3,
        fontSize: 14, color: DARK_TEXT, fontFace: "Calibri"
      }});
    }}
  }}

  // Footer on every content slide
  slide.addText(THEME.brand || '', {{
    x: 0.3, y: 5.3, w: 5, h: 0.25,
    fontSize: 9, color: 'AAAAAA', fontFace: "Calibri"
  }});

  slide.addText(String(idx + 2), {{
    x: 9.5, y: 5.3, w: 0.4, h: 0.25,
    fontSize: 9, color: 'AAAAAA', fontFace: "Calibri", align: "right"
  }});
}});

// CTA SLIDE
let cta = pres.addSlide();
cta.background = {{ color: PRIMARY }};

cta.addShape(pres.shapes.OVAL, {{
  x: 3.5, y: 0.4, w: 3.0, h: 3.0,
  fill: {{ color: ACCENT, transparency: 88 }}, line: {{ color: ACCENT, transparency: 60 }}
}});

cta.addText("✦", {{ x: 3.5, y: 0.7, w: 3.0, h: 1.2, fontSize: 64, color: ACCENT, align: "center" }});

cta.addText(THEME.cta_headline || 'Ready to begin?', {{
  x: 0.5, y: 2.2, w: 9, h: 0.7,
  fontSize: 30, color: WHITE, bold: true, fontFace: "Georgia", align: "center"
}});

cta.addText(THEME.cta_sub || '', {{
  x: 1, y: 2.9, w: 8, h: 0.5,
  fontSize: 15, color: 'B8A0D4', italic: true, fontFace: "Calibri", align: "center"
}});

if (THEME.cta_button) {{
  cta.addShape(pres.shapes.RECTANGLE, {{
    x: 3.0, y: 3.55, w: 4.0, h: 0.7,
    fill: {{ color: ACCENT }}, line: {{ color: ACCENT }},
    shadow: makeShadow()
  }});
  cta.addText(THEME.cta_button, {{
    x: 3.0, y: 3.55, w: 4.0, h: 0.7,
    fontSize: 16, color: PRIMARY, bold: true, fontFace: "Georgia", align: "center", valign: "middle"
  }});
}}

cta.addText(THEME.url || '', {{
  x: 1, y: 4.45, w: 8, h: 0.4,
  fontSize: 14, color: ACCENT, fontFace: "Calibri", align: "center"
}});

pres.writeFile({{ fileName: "{output_path}" }})
  .then(() => console.log("PPTX_DONE:" + "{output_path}"));
"""


THEMES = {
    "porch": {
        "primary": "2D1B4E",
        "accent": "C9952C",
        "light": "F0EBF8",
        "author": "The Porch is Eternal",
        "brand": "✦ The Porch is Eternal",
        "url": "microneesia.gumroad.com",
    },
    "evie": {
        "primary": "1A1A2E",
        "accent": "FF6B35",
        "light": "FFF0E8",
        "author": "EVIE — EmberVault Income Engine",
        "brand": "🔥 EmberVault Income Engine",
        "url": "phi369labs.com",
    },
    "wellness": {
        "primary": "1E4D2B",
        "accent": "7AC74F",
        "light": "EBF5EF",
        "author": "Sovereign Wellness",
        "brand": "Sovereign Wellness",
        "url": "microneesia.gumroad.com",
    },
    "dark": {
        "primary": "121212",
        "accent": "00E5FF",
        "light": "1E1E1E",
        "author": "PHI369 Labs",
        "brand": "PHI369 Labs",
        "url": "phi369labs.com",
    },
}


class PresentationGenerator(BaseModule):
    """
    Generates beautiful PPTX slide decks from topic + constraints.
    
    Example constraints:
    {
        "slides": 8,
        "theme": "porch",  // porch | evie | wellness | dark
        "style": "educational",  // educational | sales | workshop | overview
        "audience": "wellness seekers",
        "cta": "Get the guide at microneesia.gumroad.com",
        "include_sections": ["overview", "framework", "examples", "cta"]
    }
    """

    name = "presentation_generator"
    description = "Generate beautiful PowerPoint presentations from any topic or ingested content"

    def generate(
        self,
        *,
        topic: str,
        run_folder: str,
        sku: str,
        tier: str,
        price_cents: int,
        platforms: list[str],
        constraints: dict,
    ) -> ModuleResult:
        if shutil.which("node") is None:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": "presentation_generator requires Node.js in PATH. Install Node to enable PPTX rendering.",
                    "missing_dependency": "node",
                },
            )

        merged = dict(constraints or {})
        merged.setdefault("output_dir", run_folder)
        context = str(merged.get("context") or "")
        try:
            out = self.run(topic=topic, constraints=merged, context=context)
            artifact = out.get("artifact_path")
            artifacts = [artifact] if artifact else []
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"presentation_generator failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        num_slides = constraints.get("slides", 8)
        theme_name = constraints.get("theme", "porch")
        style = constraints.get("style", "educational")
        audience = constraints.get("audience", "general audience")
        cta = constraints.get("cta", "")
        custom_theme = constraints.get("custom_theme", {})

        theme = {**THEMES.get(theme_name, THEMES["porch"]), **custom_theme}

        # Build slide content using LLM
        slide_prompt = self._build_slide_prompt(topic, num_slides, style, audience, cta, context)
        slide_content = self._call_llm(slide_prompt)
        slides = self._parse_slides(slide_content, topic, style)

        # Generate the PPTX
        output_path = self._get_output_path(topic, constraints)
        self._generate_pptx(topic, slides, theme, output_path)

        return {
            "artifact_path": output_path,
            "slide_count": len(slides) + 2,  # +2 for title and CTA
            "theme": theme_name,
            "topic": topic,
        }

    def _build_slide_prompt(self, topic, num_slides, style, audience, cta, context):
        ctx_section = f"\nUse this ingested content as the source:\n{context[:3000]}" if context else ""
        return f"""Create a {num_slides}-slide presentation outline on: {topic}
Audience: {audience}
Style: {style}
CTA: {cta}
{ctx_section}

Return a JSON array of slide objects. Each slide must have:
- "layout": one of "section", "cards", "bullets", "standard"
- "title": slide title (short, punchy)
- For "cards" layout: "items" array with objects having "icon" (emoji), "title", "body"
- For "bullets" layout: "bullets" array of strings, optional "intro"
- For "section" layout: "subtitle", "body", optional "number"
- For "standard" layout: "body" text

Make it visually varied — mix layouts. Use "section" slides to introduce major phases.
Keep text concise — slides are visual, not documents.
Return ONLY the JSON array, no other text."""

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM backend."""
        from app.settings import settings
        
        if settings.llm_backend == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        elif settings.llm_backend == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            return resp.choices[0].message.content
        else:
            return self._fallback_slides()

    def _parse_slides(self, content: str, topic: str, style: str) -> list:
        """Parse LLM output into slide objects."""
        import re
        # Strip markdown fences if present
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        try:
            slides = json.loads(content)
            if isinstance(slides, list):
                return slides
        except Exception:
            pass
        
        # Fallback: basic slide structure
        return self._fallback_slides_for_topic(topic)

    def _fallback_slides_for_topic(self, topic: str) -> list:
        return [
            {"layout": "section", "title": "Overview", "subtitle": topic, "body": "Key concepts and framework"},
            {"layout": "bullets", "title": "Key Points", "bullets": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]},
            {"layout": "cards", "title": "Core Components", "items": [
                {"icon": "✦", "title": "Component 1", "body": "Description"},
                {"icon": "🌀", "title": "Component 2", "body": "Description"},
                {"icon": "💡", "title": "Component 3", "body": "Description"},
            ]},
            {"layout": "standard", "title": "How It Works", "body": "Detailed explanation of the process and methodology."},
        ]

    def _get_output_path(self, topic: str, constraints: dict | None = None) -> str:
        import re
        from datetime import datetime
        slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path((constraints or {}).get("output_dir") or "data/artifacts/presentations")
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / f"presentation_{slug}__{timestamp}.pptx")

    def _generate_pptx(self, topic: str, slides: list, theme: dict, output_path: str):
        """Write temp JS file and run it with Node."""
        script = PPTX_SCRIPT_TEMPLATE.format(
            topic_json=json.dumps(topic),
            slides_json=json.dumps(slides),
            theme_json=json.dumps(theme),
            output_path=output_path.replace("\\", "/"),
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script)
            tmp_path = f.name
        
        try:
            result = subprocess.run(
                ["node", tmp_path],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                raise RuntimeError(f"Node error: {result.stderr}")
        finally:
            os.unlink(tmp_path)
