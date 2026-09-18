from __future__ import annotations
from typing import Dict, Any
import datetime, json
from pathlib import Path
from app.modules.base import ModuleResult, BaseModule
from app.export.packager import write_text
from app.rag.llm import LLM

class MicroToolGeneratorModule(BaseModule):
    name = "micro_tool_generator"

    def generate(self, topic: str, constraints: Dict[str, Any]) -> ModuleResult:
        from app.flywheel.slug import slugify
        slug = slugify(topic)
        root = self.artifact_root(slug, "micro_tool_generator")
        appdir = root / "micro_tool"
        appdir.mkdir(parents=True, exist_ok=True)

        llm = LLM()
        title = constraints.get("app_title") or f"{topic} Micro Tools"
        about = llm.try_generate(
            f"""Write a short 'About' blurb for a tiny offline web app called '{title}'.
It includes 3 tools: checklist builder, Fibonacci cadence planner, and pricing ladder notes.
Tone: practical, no hype."""
        ) or "Offline micro tools to help you plan, track, and ship assets using 369/Φ/Fib structure."

        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>{about}</p>
    <div class="badge">369 • Φ • Fib</div>
  </header>

  <nav>
    <button data-tab="checklist" class="active">Checklist</button>
    <button data-tab="cadence">Fib Cadence</button>
    <button data-tab="pricing">Pricing Ladder</button>
  </nav>

  <main>
    <section id="tab-checklist" class="tab active">
      <h2>Checklist Builder</h2>
      <p>Create a 3/6/9 checklist and export to markdown.</p>
      <textarea id="checklistInput" placeholder="One item per line..."></textarea>
      <div class="row">
        <button id="exportChecklist">Export Markdown</button>
        <span id="checklistStatus"></span>
      </div>
      <pre id="checklistOut"></pre>
    </section>

    <section id="tab-cadence" class="tab">
      <h2>Fibonacci Release Cadence</h2>
      <p>Plan release checkpoints: 1,2,3,5,8,13 days.</p>
      <input id="startDate" type="date" />
      <button id="buildCadence">Build Plan</button>
      <pre id="cadenceOut"></pre>
    </section>

    <section id="tab-pricing" class="tab">
      <h2>Pricing Ladder Notes</h2>
      <p>Draft an Entry/Core/Premium ladder (Φ proportions).</p>
      <label>Entry ($)</label><input id="pEntry" type="number" value="9" />
      <label>Core ($)</label><input id="pCore" type="number" value="29" />
      <label>Premium ($)</label><input id="pPremium" type="number" value="99" />
      <button id="buildPricing">Generate Copy</button>
      <pre id="pricingOut"></pre>
    </section>
  </main>

  <footer>
    <small>Generated locally • {datetime.datetime.utcnow().date().isoformat()}</small>
  </footer>

  <script src="app.js"></script>
</body>
</html>
"""

        css = """body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:960px;margin:0 auto;padding:18px;line-height:1.4}
header{padding:12px 0;border-bottom:1px solid #ddd}
.badge{display:inline-block;padding:4px 10px;border:1px solid #999;border-radius:999px;font-size:12px;margin-top:8px}
nav{display:flex;gap:8px;margin:16px 0}
nav button{padding:10px 12px;border:1px solid #ccc;background:#fff;border-radius:10px;cursor:pointer}
nav button.active{border-color:#111}
.tab{display:none}
.tab.active{display:block}
textarea{width:100%;min-height:140px}
.row{display:flex;gap:12px;align-items:center;margin-top:8px}
pre{white-space:pre-wrap;background:#f7f7f7;padding:12px;border-radius:12px;border:1px solid #eee}
label{display:block;margin-top:8px}
input{padding:8px;border-radius:10px;border:1px solid #ccc;width:180px}
footer{margin-top:22px;color:#666}
"""

        js = """const fib=[1,2,3,5,8,13];
const tabs=document.querySelectorAll('nav button');
const sections={
  checklist:document.getElementById('tab-checklist'),
  cadence:document.getElementById('tab-cadence'),
  pricing:document.getElementById('tab-pricing'),
};
tabs.forEach(b=>{
  b.addEventListener('click',()=>{
    tabs.forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    Object.values(sections).forEach(s=>s.classList.remove('active'));
    sections[b.dataset.tab].classList.add('active');
  });
});

document.getElementById('exportChecklist').addEventListener('click',()=>{
  const items=document.getElementById('checklistInput').value.split(/\n+/).map(s=>s.trim()).filter(Boolean);
  const md=['# Checklist (3/6/9)',''];
  items.forEach((it,i)=>md.push(`${i+1}. ${it}`));
  const out=md.join('\n');
  document.getElementById('checklistOut').textContent=out;
  document.getElementById('checklistStatus').textContent='Copied to preview below';
});

document.getElementById('buildCadence').addEventListener('click',()=>{
  const d=document.getElementById('startDate').value;
  if(!d){document.getElementById('cadenceOut').textContent='Pick a start date.';return;}
  const start=new Date(d+'T00:00:00');
  const lines=['# Fib Cadence Plan',''];
  fib.forEach(n=>{
    const dt=new Date(start); dt.setDate(dt.getDate()+n);
    lines.push(`Day ${n}: ${dt.toISOString().slice(0,10)}`);
  });
  document.getElementById('cadenceOut').textContent=lines.join('\n');
});

document.getElementById('buildPricing').addEventListener('click',()=>{
  const e=Number(document.getElementById('pEntry').value||9);
  const c=Number(document.getElementById('pCore').value||29);
  const p=Number(document.getElementById('pPremium').value||99);
  const txt=[
    '# Pricing Ladder',
    '',
    `Entry: $${e} — quick win + starter download`,
    `Core: $${c} — full pack + templates`,
    `Premium: $${p} — licensing bundle + priority support`,
    '',
    'Note: keep promises realistic; focus on outcomes you can deliver.'
  ].join('\n');
  document.getElementById('pricingOut').textContent=txt;
});
"""

        readme = f"""# {title}

Local-only micro-tool (static HTML).

## Run
Open `index.html` in a browser.

## What it includes (369)
- Checklist Builder (3/6/9)
- Fibonacci cadence planner (1/2/3/5/8/13)
- Pricing ladder notes (Entry/Core/Premium)

Generated: {datetime.datetime.utcnow().isoformat()}
"""

        manifest = {
            "topic": topic,
            "title": title,
            "alignment": "369_phi_fib",
            "files": ["index.html","styles.css","app.js","README.md"],
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

        paths = []
        for name, content in [("index.html",html),("styles.css",css),("app.js",js),("README.md",readme)]:
            p = appdir / name
            write_text(p, content)
            paths.append(str(p))
        mpath = appdir / "manifest.json"
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        paths.append(str(mpath))

        return ModuleResult(artifact_paths=paths, metadata={"type":"static_micro_tool","title": title})
