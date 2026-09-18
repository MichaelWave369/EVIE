from __future__ import annotations
from typing import Any
from .base import ModuleResult
from .utils import write_text, write_json, ensure_dir
import os, html

def md_to_html(md: str) -> str:
    lines = md.splitlines()
    out=[]
    in_ul=False
    for ln in lines:
        if ln.startswith("#"):
            if in_ul:
                out.append("</ul>"); in_ul=False
            level=len(ln)-len(ln.lstrip("#"))
            out.append(f"<h{level}>{html.escape(ln[level:].strip())}</h{level}>")
        elif ln.startswith("- "):
            if not in_ul:
                out.append("<ul>"); in_ul=True
            out.append(f"<li>{html.escape(ln[2:].strip())}</li>")
        elif ln.strip()=="":
            if in_ul:
                out.append("</ul>"); in_ul=False
        else:
            if in_ul:
                out.append("</ul>"); in_ul=False
            out.append(f"<p>{html.escape(ln.strip())}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)

class SEOSitePublisher:
    name = "seo_site_publisher"
    def generate(self, *, topic: str, run_folder: str, sku: str, tier: str, price_cents: int, platforms: list[str], constraints: dict[str, Any]) -> ModuleResult:
        site_dir = f"{run_folder}/artifacts/{self.name}/site"
        ensure_dir(site_dir)
        base_url = (constraints.get("base_url") or "").rstrip("/")
        pages=[]
        pg_root = os.path.join(run_folder, "artifacts", "programmatic_seo_generator", "pages")
        if os.path.isdir(pg_root):
            for fn in sorted(os.listdir(pg_root)):
                if fn.endswith(".md"):
                    md_path = os.path.join(pg_root, fn)
                    name = os.path.splitext(fn)[0]
                    body = md_to_html(open(md_path, encoding="utf-8").read())
                    out_path = os.path.join(site_dir, f"{name}.html")
                    write_text(out_path, f"<!doctype html><html><head><meta charset='utf-8'><title>{topic}</title><style>body{{font-family:Arial;margin:24px;max-width:900px}}</style></head><body><a href='index.html'>Home</a>{body}</body></html>")
                    pages.append({"name": name, "html": out_path, "url": f"{base_url}/{name}.html" if base_url else ""})
        links = "\n".join([f"<li><a href='{p['name']}.html'>{p['name']}</a></li>" for p in pages])
        write_text(os.path.join(site_dir, "index.html"), f"<!doctype html><html><head><meta charset='utf-8'><title>{topic} — Site</title></head><body><h1>{topic} — Site</h1><ul>{links}</ul></body></html>")
        write_json(os.path.join(site_dir, "pages.json"), pages)
        if base_url:
            sm = ["<?xml version='1.0' encoding='UTF-8'?>", "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
            sm.append(f"<url><loc>{base_url}/index.html</loc></url>")
            for p in pages:
                if p["url"]:
                    sm.append(f"<url><loc>{p['url']}</loc></url>")
            sm.append("</urlset>")
            write_text(os.path.join(site_dir, "sitemap.xml"), "\n".join(sm))
        artifacts = [os.path.join(site_dir, "index.html"), os.path.join(site_dir, "pages.json")] + [p["html"] for p in pages]
        if base_url:
            artifacts.append(os.path.join(site_dir, "sitemap.xml"))
        return ModuleResult(name=self.name, artifacts=artifacts, summary={"pages": len(pages)})
