from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import datetime, json, re, html

from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.flywheel.slug import slugify
from app.settings import settings


def _md_to_html(md: str) -> str:
    """Very small, dependency-free markdown-ish renderer.

    Supports:
    - # / ## / ### headings
    - unordered lists (- / *)
    - code blocks ```...```
    - inline code `x`
    - links [text](url)
    - paragraphs
    """
    if md is None:
        md = ""
    md = md.replace("\r\n", "\n")

    # Code blocks
    code_blocks: List[str] = []
    def _code_repl(m):
        code_blocks.append(m.group(1))
        return f"@@CODEBLOCK{len(code_blocks)-1}@@"
    md = re.sub(r"```\s*\n(.*?)\n```", _code_repl, md, flags=re.DOTALL)

    lines = md.split("\n")
    out: List[str] = []
    in_ul = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw in lines:
        line = raw.rstrip()

        if not line.strip():
            close_ul()
            continue

        if line.startswith("### "):
            close_ul()
            out.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            continue
        if line.startswith("## "):
            close_ul()
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            continue
        if line.startswith("# "):
            close_ul()
            out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
            continue

        m = re.match(r"^\s*[-\*]\s+(.*)$", line)
        if m:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(m.group(1).strip())}</li>")
            continue

        close_ul()
        # inline code
        esc = html.escape(line)
        esc = re.sub(r"`([^`]+)`", lambda m: f"<code>{html.escape(m.group(1))}</code>", esc)
        # links
        esc = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>', esc)
        out.append(f"<p>{esc}</p>")

    close_ul()

    rendered = "\n".join(out)

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        block = "<pre><code>" + html.escape(code) + "</code></pre>"
        rendered = rendered.replace(f"@@CODEBLOCK{i}@@", block)

    return rendered


def _infer_title(md: str, fallback: str) -> str:
    for line in (md or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def _guess_md_files(artifact_paths: List[str], data_dir: str, topic_slug: str) -> List[Path]:
    files: List[Path] = []
    for p in artifact_paths or []:
        try:
            pp = Path(p)
            if pp.is_file() and pp.suffix.lower() in {".md", ".markdown"}:
                files.append(pp)
        except Exception:
            continue

    if files:
        return sorted(list({f.resolve() for f in files}))

    # fallback: scan common artifact namespaces
    root = Path(data_dir) / "artifacts"
    if not root.exists():
        return []
    patterns = [
        root / "programmatic_seo_generator" / topic_slug,
        root / "affiliate_comparison_scale" / topic_slug,
        root / "affiliate_site_mode" / topic_slug,
    ]
    for base in patterns:
        if base.exists():
            for f in base.rglob("*.md"):
                files.append(f)
    return sorted(list({f.resolve() for f in files}))


class SEOSiteCompilerModule(BaseModule):
    name = "seo_site_compiler"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        topic_slug = slugify(topic)
        artifact_paths = constraints.get("artifact_paths", [])
        site_title = constraints.get("site_title") or f"{topic} — Site"
        base_url = (constraints.get("base_url") or "").rstrip("/")
        max_pages = int(constraints.get("max_pages", 369))

        md_files = _guess_md_files(artifact_paths, settings.data_dir, topic_slug)[:max_pages]
        out_root = self.artifact_root(topic_slug, self.name) / "site"
        pages_dir = out_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        page_records: List[Dict[str, Any]] = []
        for f in md_files:
            md = f.read_text(encoding="utf-8", errors="ignore")
            title = _infer_title(md, f.stem.replace("_", " ").title())
            html_body = _md_to_html(md)
            slug = re.sub(r"[^a-z0-9\-]+", "-", f.stem.lower()).strip("-") or "page"
            out_path = pages_dir / f"{slug}.html"

            full = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — {html.escape(site_title)}</title>
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
  <header class="top">
    <a href="../index.html" class="brand">{html.escape(site_title)}</a>
    <div class="tag">369 • Φ • Fib</div>
  </header>
  <main class="container">
    <article class="card">
      {html_body}
    </article>
  </main>
  <footer class="footer">
    <div>Generated locally by EmberVault • {datetime.datetime.utcnow().date().isoformat()}</div>
  </footer>
</body>
</html>
"""
            write_text(out_path, full)
            url = f"{base_url}/pages/{slug}.html" if base_url else f"pages/{slug}.html"
            page_records.append({"title": title, "slug": slug, "source": str(f), "url": url})

        # assets
        css = """/* EmberVault SEO Site (local-only) */
:root{--bg:#0b1020;--card:#121a33;--text:#e9eefc;--muted:#9bb0d6;--accent:#5eead4}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu;background:var(--bg);color:var(--text)}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.container{max-width:960px;margin:0 auto;padding:24px}
.top{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;border-bottom:1px solid rgba(255,255,255,.08);position:sticky;top:0;background:rgba(11,16,32,.92);backdrop-filter: blur(6px)}
.brand{font-weight:700}
.tag{font-size:12px;color:var(--muted)}
.card{background:var(--card);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.item{padding:14px;border-radius:14px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03)}
.item .t{font-weight:650;margin-bottom:6px}
.item .s{color:var(--muted);font-size:12px}
.footer{padding:28px 24px;color:var(--muted);font-size:12px;text-align:center}
h1,h2,h3{margin-top:18px}
pre{overflow:auto;background:rgba(0,0,0,.35);padding:14px;border-radius:12px}
code{background:rgba(0,0,0,.25);padding:2px 6px;border-radius:8px}
ul{padding-left:18px}
"""
        write_text(out_root / "assets" / "styles.css", css)

        index_items = []
        for pr in page_records:
            index_items.append(f"""<div class="item"><div class="t"><a href="{html.escape(pr['url'])}">{html.escape(pr['title'])}</a></div><div class="s">{html.escape(Path(pr['source']).name)}</div></div>""")
        index_html = f"""<!doctype html>
<html><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(site_title)}</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <header class="top">
    <div class="brand">{html.escape(site_title)}</div>
    <div class="tag">369 • Φ • Fib</div>
  </header>
  <main class="container">
    <div class="card">
      <h1>{html.escape(site_title)}</h1>
      <p>Static site compiled locally from your EmberVault markdown artifacts. No cloud required.</p>
      <div class="grid">
        {''.join(index_items)}
      </div>
    </div>
  </main>
  <footer class="footer">Generated {datetime.datetime.utcnow().isoformat()} • Local-only</footer>
</body></html>
"""
        write_text(out_root / "index.html", index_html)

        # sitemap.xml (simple)
        if base_url:
            sm_urls = []
            sm_urls.append(f"<url><loc>{base_url}/index.html</loc></url>")
            for pr in page_records:
                sm_urls.append(f"<url><loc>{base_url}/pages/{pr['slug']}.html</loc></url>")
            sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
""" + "\n".join(sm_urls) + "\n</urlset>\n"
            write_text(out_root / "sitemap.xml", sitemap)

        write_text(out_root / "pages.json", json.dumps(page_records, indent=2))

        meta = {
            "site_title": site_title,
            "base_url": base_url,
            "page_count": len(page_records),
            "topic_slug": topic_slug,
        }
        return ModuleResult(
            artifact_paths=[str(out_root), str(out_root / "index.html"), str(out_root / "pages.json")],
            metadata=meta,
        )
