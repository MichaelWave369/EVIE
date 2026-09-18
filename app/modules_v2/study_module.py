"""
EVIE Study Module
Generates flashcards, quizzes, and reports from any topic or vault content.

Three modes:
  FLASHCARDS — LLM generates Q/A pairs → interactive HTML flip-card deck + JSON
  QUIZ       — LLM generates questions with choices + explanations → scored HTML quiz
  REPORT     — LLM generates structured analysis → formatted PDF + HTML

All outputs use the NotebookLM dark aesthetic.
HTML outputs are fully self-contained — open in any browser, no internet needed.

Drop into: D:/EVIEv4.0/app/modules_v2/study_module.py
"""

import os, re, json
from pathlib import Path
from datetime import datetime
from typing import Optional
import importlib.util
from app.modules.base import BaseModule
from .base import ModuleResult


# ── LLM Prompts ───────────────────────────────────────────────────────────────

FLASHCARD_PROMPT = """You are an expert educator creating study flashcards.
Generate {count} high-quality flashcards on: "{topic}"

{context_section}

Rules:
- Front: concise, clear question or term (max 15 words)
- Back: precise answer with key details (max 60 words)
- Vary difficulty: mix foundational, intermediate, and advanced cards
- Group into 3-4 categories
- Make cards genuinely useful for learning and retention

Return ONLY valid JSON, no explanation:
{{
  "title": "deck title",
  "topic": "{topic}",
  "categories": [
    {{
      "name": "Category Name",
      "color": "teal",
      "cards": [
        {{"front": "question text", "back": "answer text", "difficulty": "easy|medium|hard"}},
        ...
      ]
    }}
  ]
}}

Colors must be one of: teal, purple, gold, blue, coral"""


QUIZ_PROMPT = """You are an expert educator creating a learning quiz.
Generate {count} questions on: "{topic}"

{context_section}

Rules:
- Mix question types: multiple_choice (60%), true_false (20%), short_answer (20%)
- For multiple_choice: 4 options, only 1 correct
- Include a brief explanation for every answer (why it's correct + why others are wrong)
- Vary difficulty across questions
- Questions should test real understanding, not just memorization

Return ONLY valid JSON, no explanation:
{{
  "title": "quiz title",
  "topic": "{topic}",
  "time_estimate_minutes": {time_est},
  "questions": [
    {{
      "id": 1,
      "type": "multiple_choice",
      "difficulty": "easy|medium|hard",
      "question": "question text",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "explanation of why A is correct and others aren't"
    }},
    {{
      "id": 2,
      "type": "true_false",
      "difficulty": "medium",
      "question": "statement to evaluate",
      "correct": true,
      "explanation": "explanation"
    }},
    {{
      "id": 3,
      "type": "short_answer",
      "difficulty": "hard",
      "question": "question requiring brief written response",
      "sample_answer": "model answer",
      "key_points": ["key point 1", "key point 2"]
    }}
  ]
}}"""


REPORT_PROMPT = """You are an expert analyst writing a comprehensive report.
Write a detailed report on: "{topic}"

{context_section}

Report structure (use exactly these section keys):
- executive_summary: 2-3 paragraph overview, key findings upfront
- background: context, history, why this matters
- key_findings: 4-6 specific findings as a list with brief explanations  
- deep_analysis: 3-4 paragraphs of detailed analysis
- practical_applications: how to apply this knowledge, actionable steps
- recommendations: 3-5 specific recommendations
- conclusion: 1-2 paragraphs wrapping up

Return ONLY valid JSON:
{{
  "title": "report title",
  "subtitle": "descriptive subtitle",
  "topic": "{topic}",
  "date": "{date}",
  "sections": {{
    "executive_summary": "text...",
    "background": "text...",
    "key_findings": ["finding 1", "finding 2", ...],
    "deep_analysis": "text...",
    "practical_applications": "text...",
    "recommendations": ["rec 1", "rec 2", ...],
    "conclusion": "text..."
  }},
  "tags": ["tag1", "tag2", "tag3"],
  "reading_time_minutes": 8
}}"""


# ── LLM caller ────────────────────────────────────────────────────────────────

def _call_llm(prompt: str, max_tokens: int = 4000) -> str:
    try:
        from app.settings import settings
        if settings.llm_backend == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        elif settings.llm_backend == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"  LLM error: {e}")
    return ""


def _parse_json(raw: str) -> Optional[dict]:
    """Extract and parse JSON from LLM response."""
    # Strip markdown code fences
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        # Try to find JSON block
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


# ── HTML Builders ─────────────────────────────────────────────────────────────

def build_flashcard_html(data: dict, topic: str) -> str:
    title = data.get("title", topic)
    categories = data.get("categories", [])

    # Flatten all cards with category info
    all_cards = []
    color_map = {
        "teal":   ("#52C4C4", "#0D2B2B"),
        "purple": ("#8C64DC", "#1A0D33"),
        "gold":   ("#C9A34B", "#2B1F00"),
        "blue":   ("#64A0FF", "#0D1A33"),
        "coral":  ("#FF7C64", "#2B1000"),
    }

    for cat in categories:
        color_key = cat.get("color", "teal")
        accent, dark = color_map.get(color_key, color_map["teal"])
        for card in cat.get("cards", []):
            all_cards.append({
                **card,
                "category": cat["name"],
                "accent": accent,
                "dark": dark,
            })

    cards_json = json.dumps(all_cards)
    total = len(all_cards)

    cat_buttons = ""
    seen = set()
    for cat in categories:
        if cat["name"] not in seen:
            seen.add(cat["name"])
            color_key = cat.get("color", "teal")
            accent, _ = color_map.get(color_key, color_map["teal"])
            cat_buttons += f'<button class="cat-btn" data-cat="{cat["name"]}" style="--accent:{accent}">{cat["name"]}</button>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Flashcards</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

  :root {{
    --bg:      #080C1C;
    --card-bg: #121A37;
    --border:  #2D50A0;
    --accent:  #52C4C4;
    --gold:    #C9A34B;
    --white:   #FFFFFF;
    --muted:   #8CA0D2;
    --label:   #6488C8;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--white);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }}

  /* Dot grid */
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(circle, rgba(80,110,180,0.12) 1px, transparent 1px);
    background-size: 36px 36px;
    pointer-events: none;
    z-index: 0;
  }}

  /* Glow orbs */
  body::after {{
    content: '';
    position: fixed;
    top: -200px; left: 50%;
    transform: translateX(-50%);
    width: 700px; height: 700px;
    background: radial-gradient(circle, rgba(82,196,196,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }}

  .container {{ position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 40px 24px; }}

  /* Header */
  .brand {{ text-align: center; font-size: 12px; font-weight: 600; letter-spacing: 4px; color: var(--gold); margin-bottom: 12px; }}
  h1 {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(28px, 5vw, 48px);
    text-align: center;
    background: linear-gradient(135deg, #fff 0%, #52C4C4 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}
  .subtitle {{ text-align: center; color: var(--muted); font-size: 15px; margin-bottom: 32px; }}

  /* Progress bar */
  .progress-wrap {{ background: rgba(45,80,160,0.3); border-radius: 4px; height: 6px; margin-bottom: 12px; overflow: hidden; }}
  .progress-bar {{ height: 100%; background: linear-gradient(90deg, var(--accent), #8C64DC); border-radius: 4px; transition: width 0.4s ease; width: 0%; }}
  .progress-label {{ display: flex; justify-content: space-between; font-size: 13px; color: var(--muted); margin-bottom: 28px; }}
  .progress-label span {{ color: var(--accent); font-weight: 600; }}

  /* Category filter */
  .filter-row {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-bottom: 32px; }}
  .cat-btn {{
    padding: 7px 18px; border-radius: 20px; border: 1px solid;
    border-color: var(--accent); color: var(--accent);
    background: rgba(82,196,196,0.08); cursor: pointer;
    font-family: 'DM Sans', sans-serif; font-size: 13px; font-weight: 600;
    transition: all 0.2s;
  }}
  .cat-btn:hover, .cat-btn.active {{ background: rgba(82,196,196,0.2); }}
  .cat-btn[data-cat="all"] {{ border-color: var(--gold); color: var(--gold); background: rgba(201,163,75,0.08); }}
  .cat-btn[data-cat="all"]:hover, .cat-btn[data-cat="all"].active {{ background: rgba(201,163,75,0.2); }}

  /* Card arena */
  .card-arena {{ perspective: 1200px; min-height: 320px; display: flex; align-items: center; justify-content: center; margin-bottom: 28px; }}

  .flashcard {{
    width: 100%; max-width: 680px;
    height: 300px;
    position: relative;
    cursor: pointer;
    transform-style: preserve-3d;
    transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }}
  .flashcard.flipped {{ transform: rotateY(180deg); }}

  .card-face {{
    position: absolute; inset: 0;
    backface-visibility: hidden;
    border-radius: 20px;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    padding: 40px 48px;
    text-align: center;
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(45,80,160,0.5);
  }}

  .card-front {{
    background: linear-gradient(135deg, #121A37 0%, #0F1530 100%);
    border-top: 3px solid var(--card-accent, var(--accent));
  }}

  .card-back {{
    background: linear-gradient(135deg, #0D1F2D 0%, #0A1520 100%);
    transform: rotateY(180deg);
    border-top: 3px solid var(--card-accent, var(--accent));
  }}

  .card-label {{ font-size: 11px; font-weight: 700; letter-spacing: 3px; color: var(--card-accent, var(--accent)); margin-bottom: 16px; }}
  .card-cat {{ font-size: 12px; color: var(--muted); position: absolute; top: 20px; left: 24px; }}
  .card-diff {{ position: absolute; top: 20px; right: 24px; font-size: 11px; padding: 3px 10px; border-radius: 10px; }}
  .diff-easy   {{ background: rgba(82,196,196,0.15); color: #52C4C4; }}
  .diff-medium {{ background: rgba(201,163,75,0.15); color: #C9A34B; }}
  .diff-hard   {{ background: rgba(140,100,220,0.15); color: #8C64DC; }}

  .card-front .card-text {{
    font-family: 'Playfair Display', serif;
    font-size: clamp(18px, 3vw, 26px);
    line-height: 1.45;
    color: var(--white);
  }}

  .card-back .card-text {{
    font-size: clamp(14px, 2.2vw, 18px);
    line-height: 1.65;
    color: #D0E8E8;
  }}

  .flip-hint {{
    position: absolute; bottom: 18px;
    font-size: 12px; color: rgba(140,160,210,0.6);
    display: flex; align-items: center; gap: 6px;
  }}
  .flip-hint svg {{ width: 14px; height: 14px; opacity: 0.6; }}

  /* Controls */
  .controls {{ display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 40px; }}

  .btn {{
    padding: 12px 28px; border-radius: 10px; border: none;
    font-family: 'DM Sans', sans-serif; font-size: 15px; font-weight: 600;
    cursor: pointer; transition: all 0.2s;
  }}
  .btn-prev {{ background: rgba(45,80,160,0.3); color: var(--muted); }}
  .btn-prev:hover {{ background: rgba(45,80,160,0.5); color: var(--white); }}
  .btn-next {{
    background: linear-gradient(135deg, #52C4C4, #8C64DC);
    color: #080C1C; min-width: 140px;
    box-shadow: 0 4px 20px rgba(82,196,196,0.3);
  }}
  .btn-next:hover {{ transform: translateY(-2px); box-shadow: 0 8px 28px rgba(82,196,196,0.4); }}
  .btn-shuffle {{ background: rgba(201,163,75,0.15); color: var(--gold); border: 1px solid rgba(201,163,75,0.3); }}
  .btn-shuffle:hover {{ background: rgba(201,163,75,0.25); }}

  .card-counter {{ font-size: 14px; color: var(--muted); min-width: 80px; text-align: center; }}
  .card-counter span {{ color: var(--white); font-weight: 600; }}

  /* Known/Unknown buttons */
  .know-row {{ display: flex; gap: 12px; justify-content: center; margin-bottom: 48px; }}
  .btn-know {{ background: rgba(82,196,196,0.15); color: #52C4C4; border: 1px solid rgba(82,196,196,0.3); padding: 9px 24px; border-radius: 8px; cursor: pointer; font-family: 'DM Sans', sans-serif; font-weight: 600; transition: all 0.2s; }}
  .btn-know:hover {{ background: rgba(82,196,196,0.28); }}
  .btn-unknown {{ background: rgba(140,100,220,0.15); color: #8C64DC; border: 1px solid rgba(140,100,220,0.3); padding: 9px 24px; border-radius: 8px; cursor: pointer; font-family: 'DM Sans', sans-serif; font-weight: 600; transition: all 0.2s; }}
  .btn-unknown:hover {{ background: rgba(140,100,220,0.28); }}

  /* Stats row */
  .stats {{ display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; padding: 24px; background: rgba(18,26,55,0.6); border-radius: 16px; border: 1px solid rgba(45,80,160,0.3); margin-bottom: 40px; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-family: 'Playfair Display', serif; font-size: 28px; color: var(--white); }}
  .stat-num.green {{ color: #52C4C4; }} .stat-num.purple {{ color: #8C64DC; }} .stat-num.gold {{ color: #C9A34B; }}
  .stat-label {{ font-size: 12px; color: var(--muted); margin-top: 2px; letter-spacing: 1px; }}

  /* All cards list */
  .all-cards {{ display: none; }}
  .all-cards.visible {{ display: block; }}
  .card-list-item {{
    background: rgba(18,26,55,0.5); border: 1px solid rgba(45,80,160,0.3);
    border-radius: 14px; padding: 20px 24px; margin-bottom: 14px;
    border-left: 3px solid var(--accent);
    animation: fadeUp 0.3s ease forwards;
  }}
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:none; }} }}
  .card-list-front {{ font-family: 'Playfair Display', serif; font-size: 17px; color: var(--white); margin-bottom: 10px; }}
  .card-list-back {{ font-size: 14px; color: var(--muted); line-height: 1.6; }}

  .btn-list-toggle {{ display: block; margin: 0 auto 20px; background: transparent; border: 1px solid rgba(45,80,160,0.4); color: var(--muted); padding: 8px 22px; border-radius: 8px; cursor: pointer; font-family: 'DM Sans', sans-serif; transition: all 0.2s; }}
  .btn-list-toggle:hover {{ border-color: var(--accent); color: var(--accent); }}

  .footer {{ text-align: center; font-size: 12px; color: var(--label); margin-top: 20px; letter-spacing: 2px; }}
</style>
</head>
<body>
<div class="container">

  <div class="brand">✦ THE PORCH IS ETERNAL · PHI369 LABS ✦</div>
  <h1>{title}</h1>
  <div class="subtitle">Study Deck · {total} Cards</div>

  <div class="progress-wrap"><div class="progress-bar" id="progressBar"></div></div>
  <div class="progress-label"><span id="progressPct">0%</span> complete <span id="knownCount">0</span> known</div>

  <div class="filter-row">
    <button class="cat-btn active" data-cat="all" onclick="filterCat('all')">All Cards</button>
    {cat_buttons}
  </div>

  <div class="card-arena" id="arena">
    <div class="flashcard" id="flashcard" onclick="flipCard()">
      <div class="card-face card-front" id="cardFront">
        <span class="card-cat" id="cardCat"></span>
        <span class="card-diff" id="cardDiff"></span>
        <div class="card-label">QUESTION</div>
        <div class="card-text" id="frontText"></div>
        <div class="flip-hint"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>tap to flip</div>
      </div>
      <div class="card-face card-back" id="cardBack">
        <span class="card-cat" id="cardCatBack"></span>
        <div class="card-label" style="color:#8CA0D2">ANSWER</div>
        <div class="card-text" id="backText"></div>
      </div>
    </div>
  </div>

  <div class="controls">
    <button class="btn btn-prev" onclick="prevCard()">← Prev</button>
    <span class="card-counter"><span id="currentNum">1</span> / <span id="totalNum">{total}</span></span>
    <button class="btn btn-next" onclick="nextCard()">Next →</button>
    <button class="btn btn-shuffle" onclick="shuffleDeck()">⇄ Shuffle</button>
  </div>

  <div class="know-row">
    <button class="btn-know" onclick="markKnown()">✓ Know it</button>
    <button class="btn-unknown" onclick="markUnknown()">↻ Study more</button>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num" id="statTotal">{total}</div><div class="stat-label">TOTAL</div></div>
    <div class="stat"><div class="stat-num green" id="statKnown">0</div><div class="stat-label">KNOWN</div></div>
    <div class="stat"><div class="stat-num purple" id="statStudy">0</div><div class="stat-label">STUDYING</div></div>
    <div class="stat"><div class="stat-num gold" id="statPct">0%</div><div class="stat-label">MASTERY</div></div>
  </div>

  <button class="btn-list-toggle" onclick="toggleList()">☰ View All Cards</button>
  <div class="all-cards" id="allCards"></div>

  <div class="footer">✦ EVIE · The Porch is Eternal ✦</div>
</div>

<script>
const ALL_CARDS = {cards_json};
let deck = [...ALL_CARDS];
let current = 0;
let known = new Set();
let studying = new Set();
let isFlipped = false;
let activeFilter = 'all';

function filterCat(cat) {{
  activeFilter = cat;
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.toggle('active', b.dataset.cat === cat));
  deck = cat === 'all' ? [...ALL_CARDS] : ALL_CARDS.filter(c => c.category === cat);
  current = 0;
  showCard();
}}

function showCard() {{
  if (!deck.length) return;
  const card = deck[current];
  const fc = document.getElementById('flashcard');

  // Reset flip
  isFlipped = false;
  fc.classList.remove('flipped');
  fc.style.setProperty('--card-accent', card.accent);
  document.getElementById('cardFront').style.setProperty('--card-accent', card.accent);
  document.getElementById('cardBack').style.setProperty('--card-accent', card.accent);

  document.getElementById('frontText').textContent = card.front;
  document.getElementById('backText').textContent = card.back;
  document.getElementById('cardCat').textContent = card.category;
  document.getElementById('cardCatBack').textContent = card.category;
  document.getElementById('cardFront').style.borderTopColor = card.accent;
  document.getElementById('cardBack').style.borderTopColor = card.accent;

  const diff = document.getElementById('cardDiff');
  diff.textContent = card.difficulty;
  diff.className = 'card-diff diff-' + card.difficulty;

  document.getElementById('currentNum').textContent = current + 1;
  document.getElementById('totalNum').textContent = deck.length;
  updateProgress();
}}

function flipCard() {{
  isFlipped = !isFlipped;
  document.getElementById('flashcard').classList.toggle('flipped', isFlipped);
}}

function nextCard() {{
  if (current < deck.length - 1) {{ current++; showCard(); }}
  else {{ current = 0; showCard(); }}
}}

function prevCard() {{
  if (current > 0) {{ current--; showCard(); }}
  else {{ current = deck.length - 1; showCard(); }}
}}

function shuffleDeck() {{
  deck.sort(() => Math.random() - 0.5);
  current = 0;
  showCard();
}}

function markKnown() {{
  const card = deck[current];
  known.add(card.front);
  studying.delete(card.front);
  nextCard();
  updateStats();
}}

function markUnknown() {{
  const card = deck[current];
  studying.add(card.front);
  known.delete(card.front);
  nextCard();
  updateStats();
}}

function updateStats() {{
  const k = known.size, s = studying.size, t = ALL_CARDS.length;
  const pct = Math.round(k / t * 100);
  document.getElementById('statKnown').textContent = k;
  document.getElementById('statStudy').textContent = s;
  document.getElementById('statPct').textContent = pct + '%';
  updateProgress();
}}

function updateProgress() {{
  const pct = Math.round(known.size / ALL_CARDS.length * 100);
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPct').textContent = pct + '%';
  document.getElementById('knownCount').textContent = known.size;
}}

function toggleList() {{
  const el = document.getElementById('allCards');
  el.classList.toggle('visible');
  if (el.classList.contains('visible') && !el.innerHTML) {{
    el.innerHTML = ALL_CARDS.map(c => `
      <div class="card-list-item" style="border-left-color: ${{c.accent}}">
        <div class="card-list-front">${{c.front}}</div>
        <div class="card-list-back">${{c.back}}</div>
      </div>`).join('');
  }}
}}

// Keyboard navigation
document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight') nextCard();
  else if (e.key === 'ArrowLeft') prevCard();
  else if (e.key === ' ') {{ e.preventDefault(); flipCard(); }}
  else if (e.key === 'k') markKnown();
  else if (e.key === 's') markUnknown();
}});

showCard();
</script>
</body>
</html>"""


def build_quiz_html(data: dict, topic: str) -> str:
    title = data.get("title", topic)
    questions = data.get("questions", [])
    time_est = data.get("time_estimate_minutes", len(questions) * 1.5)
    questions_json = json.dumps(questions)
    total = len(questions)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Quiz</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
  :root {{ --bg:#080C1C; --card:#121A37; --border:#2D50A0; --accent:#52C4C4; --gold:#C9A34B; --white:#FFF; --muted:#8CA0D2; --purple:#8C64DC; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--white); font-family:'DM Sans',sans-serif; min-height:100vh; }}
  body::before {{ content:''; position:fixed; inset:0; background-image:radial-gradient(circle,rgba(80,110,180,.1) 1px,transparent 1px); background-size:36px 36px; pointer-events:none; }}
  .container {{ position:relative; z-index:1; max-width:780px; margin:0 auto; padding:40px 24px; }}
  .brand {{ text-align:center; font-size:11px; letter-spacing:4px; color:var(--gold); margin-bottom:10px; font-weight:600; }}
  h1 {{ font-family:'Playfair Display',serif; font-size:clamp(24px,4vw,40px); text-align:center; background:linear-gradient(135deg,#fff,#52C4C4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:8px; }}
  .meta {{ text-align:center; color:var(--muted); font-size:14px; margin-bottom:36px; }}
  .meta span {{ color:var(--accent); }}

  /* Question card */
  .q-card {{
    background:linear-gradient(135deg,#121A37,#0F1530);
    border:1px solid rgba(45,80,160,0.5);
    border-radius:18px; padding:32px 36px; margin-bottom:20px;
    border-top:3px solid var(--accent);
    animation:slideIn 0.3s ease;
  }}
  @keyframes slideIn {{ from{{opacity:0;transform:translateY(16px)}} to{{opacity:1;transform:none}} }}

  .q-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }}
  .q-num {{ font-size:12px; color:var(--accent); font-weight:700; letter-spacing:2px; }}
  .q-diff {{ font-size:11px; padding:3px 10px; border-radius:8px; }}
  .diff-easy{{ background:rgba(82,196,196,.15); color:#52C4C4; }}
  .diff-medium{{ background:rgba(201,163,75,.15); color:#C9A34B; }}
  .diff-hard{{ background:rgba(140,100,220,.15); color:#8C64DC; }}

  .q-text {{ font-family:'Playfair Display',serif; font-size:clamp(17px,2.5vw,22px); line-height:1.5; margin-bottom:24px; }}

  /* Options */
  .options {{ display:flex; flex-direction:column; gap:10px; }}
  .option {{
    background:rgba(18,26,55,.6); border:1px solid rgba(45,80,160,.35);
    border-radius:12px; padding:14px 20px;
    cursor:pointer; display:flex; align-items:center; gap:14px;
    transition:all .2s; font-size:15px;
  }}
  .option:hover {{ border-color:var(--accent); background:rgba(82,196,196,.08); }}
  .option.correct {{ border-color:#52C4C4; background:rgba(82,196,196,.15); }}
  .option.wrong   {{ border-color:#FF6B6B; background:rgba(255,107,107,.12); }}
  .option-letter {{
    width:32px; height:32px; border-radius:50%; border:1px solid rgba(45,80,160,.5);
    display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:700; color:var(--muted); flex-shrink:0;
    transition:all .2s;
  }}
  .option.correct .option-letter {{ background:var(--accent); color:#080C1C; border-color:var(--accent); }}
  .option.wrong   .option-letter {{ background:#FF6B6B; color:#fff; border-color:#FF6B6B; }}

  /* True/False */
  .tf-row {{ display:flex; gap:14px; }}
  .tf-btn {{
    flex:1; padding:16px; border-radius:12px; border:1px solid rgba(45,80,160,.35);
    background:rgba(18,26,55,.6); cursor:pointer; font-size:16px; font-weight:600;
    transition:all .2s; color:var(--white);
  }}
  .tf-btn:hover {{ border-color:var(--accent); }}
  .tf-btn.correct {{ border-color:#52C4C4; background:rgba(82,196,196,.15); color:#52C4C4; }}
  .tf-btn.wrong   {{ border-color:#FF6B6B; background:rgba(255,107,107,.12); color:#FF6B6B; }}

  /* Short answer */
  .sa-input {{
    width:100%; background:rgba(18,26,55,.8); border:1px solid rgba(45,80,160,.4);
    border-radius:12px; padding:14px 18px; color:var(--white); font-size:15px;
    font-family:'DM Sans',sans-serif; resize:vertical; min-height:80px;
    transition:border .2s;
  }}
  .sa-input:focus {{ outline:none; border-color:var(--accent); }}

  /* Explanation */
  .explanation {{
    display:none; margin-top:18px; padding:16px 20px;
    background:rgba(82,196,196,.07); border-radius:12px;
    border-left:3px solid var(--accent); font-size:14px; color:#C0D8D8; line-height:1.7;
  }}
  .explanation.visible {{ display:block; animation:fadeIn .3s ease; }}
  @keyframes fadeIn {{ from{{opacity:0}} to{{opacity:1}} }}
  .key-points {{ margin-top:10px; }}
  .key-points li {{ margin-left:18px; margin-top:6px; color:var(--muted); }}

  /* Navigation */
  .nav {{ display:flex; justify-content:space-between; align-items:center; margin-top:24px; }}
  .btn {{ padding:12px 28px; border-radius:10px; border:none; font-family:'DM Sans',sans-serif; font-size:15px; font-weight:600; cursor:pointer; transition:all .2s; }}
  .btn-prev {{ background:rgba(45,80,160,.25); color:var(--muted); }}
  .btn-prev:hover {{ background:rgba(45,80,160,.4); color:var(--white); }}
  .btn-submit {{
    background:linear-gradient(135deg,#52C4C4,#8C64DC); color:#080C1C;
    box-shadow:0 4px 20px rgba(82,196,196,.3);
  }}
  .btn-submit:hover {{ transform:translateY(-2px); box-shadow:0 8px 28px rgba(82,196,196,.4); }}

  /* Progress */
  .prog-wrap {{ background:rgba(45,80,160,.25); border-radius:4px; height:5px; margin-bottom:32px; overflow:hidden; }}
  .prog-fill {{ height:100%; background:linear-gradient(90deg,var(--accent),var(--purple)); border-radius:4px; transition:width .4s; }}

  /* Score screen */
  .score-screen {{ display:none; text-align:center; padding:40px 20px; }}
  .score-screen.visible {{ display:block; animation:slideIn .4s ease; }}
  .score-ring {{ width:160px; height:160px; border-radius:50%; margin:0 auto 28px; display:flex; flex-direction:column; align-items:center; justify-content:center; border:3px solid var(--accent); box-shadow:0 0 40px rgba(82,196,196,.3); }}
  .score-pct {{ font-family:'Playfair Display',serif; font-size:48px; background:linear-gradient(135deg,#fff,#52C4C4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .score-label {{ font-size:13px; color:var(--muted); margin-top:-4px; }}
  .score-msg {{ font-family:'Playfair Display',serif; font-size:24px; margin-bottom:12px; }}
  .score-sub {{ color:var(--muted); font-size:15px; margin-bottom:32px; }}
  .score-breakdown {{ display:flex; gap:20px; justify-content:center; flex-wrap:wrap; margin-bottom:32px; }}
  .score-stat {{ background:rgba(18,26,55,.6); border:1px solid rgba(45,80,160,.3); border-radius:14px; padding:18px 24px; min-width:100px; }}
  .score-stat-num {{ font-family:'Playfair Display',serif; font-size:28px; }}
  .score-stat-lbl {{ font-size:12px; color:var(--muted); margin-top:4px; letter-spacing:1px; }}
  .btn-retry {{ background:linear-gradient(135deg,#52C4C4,#8C64DC); color:#080C1C; padding:14px 36px; border-radius:12px; font-size:16px; font-weight:700; }}

  .footer {{ text-align:center; font-size:12px; color:rgba(100,136,200,.5); margin-top:40px; letter-spacing:2px; }}
</style>
</head>
<body>
<div class="container">
  <div class="brand">✦ THE PORCH IS ETERNAL · PHI369 LABS ✦</div>
  <h1>{title}</h1>
  <div class="meta"><span>{total}</span> Questions · Est. <span>{int(time_est)}</span> min</div>

  <div class="prog-wrap"><div class="prog-fill" id="progFill" style="width:0%"></div></div>

  <div id="quizBody"></div>

  <div class="score-screen" id="scoreScreen">
    <div class="score-ring"><div class="score-pct" id="scorePct">0%</div><div class="score-label">SCORE</div></div>
    <div class="score-msg" id="scoreMsg"></div>
    <div class="score-sub" id="scoreSub"></div>
    <div class="score-breakdown">
      <div class="score-stat"><div class="score-stat-num" id="sCorrect" style="color:#52C4C4">0</div><div class="score-stat-lbl">CORRECT</div></div>
      <div class="score-stat"><div class="score-stat-num" id="sWrong" style="color:#FF6B6B">0</div><div class="score-stat-lbl">WRONG</div></div>
      <div class="score-stat"><div class="score-stat-num" id="sSkip" style="color:#C9A34B">0</div><div class="score-stat-lbl">SKIPPED</div></div>
    </div>
    <button class="btn btn-retry" onclick="restartQuiz()">↻ Try Again</button>
  </div>

  <div class="footer">✦ EVIE · The Porch is Eternal ✦</div>
</div>

<script>
const QUESTIONS = {questions_json};
let current = 0;
let answers = {{}};
let answered = {{}};

const messages = [
  ["Sovereign Mastery!", "You've integrated this knowledge deeply."],
  ["Strong Understanding", "Most concepts are clear — keep refining."],
  ["Good Foundation", "Solid base. Review the tricky ones and revisit."],
  ["Keep Going", "Every study session compounds. You're building."],
];

function render() {{
  const q = QUESTIONS[current];
  const body = document.getElementById('quizBody');
  const pct = Math.round((current / QUESTIONS.length) * 100);
  document.getElementById('progFill').style.width = pct + '%';

  let optionsHtml = '';
  if (q.type === 'multiple_choice') {{
    optionsHtml = `<div class="options">` + q.options.map((opt, i) =>
      `<div class="option ${{answered[current] ? (i===q.correct_index?'correct':(answers[current]===i?'wrong':'')) : ''}}" onclick="answerMC(${{i}})">
        <div class="option-letter">${{'ABCD'[i]}}</div><span>${{opt}}</span></div>`
    ).join('') + `</div>`;
  }} else if (q.type === 'true_false') {{
    const userAns = answers[current];
    optionsHtml = `<div class="tf-row">
      <button class="tf-btn ${{answered[current]?(q.correct?'correct':(userAns===true?'correct':'')):(userAns===true?'selected':'') }}" onclick="answerTF(true)">✓ True</button>
      <button class="tf-btn ${{answered[current]?(!q.correct?'correct':(userAns===false?'wrong':'')):''}}" onclick="answerTF(false)">✗ False</button>
    </div>`;
  }} else {{
    const saved = answers[current] || '';
    optionsHtml = `<textarea class="sa-input" id="saInput" placeholder="Type your answer..." rows="3">${{saved}}</textarea>`;
  }}

  const expVisible = answered[current] ? 'visible' : '';
  let expContent = q.explanation || '';
  if (q.type === 'short_answer' && q.key_points) {{
    expContent += `<div class="key-points"><strong>Key points:</strong><ul>` + q.key_points.map(p=>`<li>${{p}}</li>`).join('') + `</ul></div>`;
  }}
  if (q.type === 'short_answer' && q.sample_answer) {{
    expContent = `<strong>Sample answer:</strong> ${{q.sample_answer}}<br><br>` + expContent;
  }}

  body.innerHTML = `
    <div class="q-card">
      <div class="q-header">
        <span class="q-num">QUESTION ${{current+1}} / ${{QUESTIONS.length}}</span>
        <span class="q-diff diff-${{q.difficulty}}">${{q.difficulty}}</span>
      </div>
      <div class="q-text">${{q.question}}</div>
      ${{optionsHtml}}
      <div class="explanation ${{expVisible}}" id="explanation">${{expContent}}</div>
    </div>
    <div class="nav">
      ${{current > 0 ? '<button class="btn btn-prev" onclick="prevQ()">← Back</button>' : '<span></span>'}}
      ${{q.type === 'short_answer' && !answered[current]
        ? '<button class="btn btn-submit" onclick="submitSA()">Check Answer</button>'
        : answered[current]
          ? (current < QUESTIONS.length-1
              ? '<button class="btn btn-submit" onclick="nextQ()">Next →</button>'
              : '<button class="btn btn-submit" onclick="showScore()">See Results →</button>')
          : '<span></span>'
      }}
    </div>`;
}}

function answerMC(i) {{
  if (answered[current]) return;
  answered[current] = true;
  answers[current] = i;
  render();
  document.getElementById('explanation').classList.add('visible');
  // Highlight
  setTimeout(() => {{
    document.querySelectorAll('.option').forEach((el,idx) => {{
      if (idx === QUESTIONS[current].correct_index) el.classList.add('correct');
      else if (idx === i && i !== QUESTIONS[current].correct_index) el.classList.add('wrong');
    }});
  }}, 10);
}}

function answerTF(val) {{
  if (answered[current]) return;
  answered[current] = true;
  answers[current] = val;
  render();
  document.getElementById('explanation').classList.add('visible');
}}

function submitSA() {{
  const input = document.getElementById('saInput');
  if (input) {{ answers[current] = input.value; answered[current] = true; render(); document.getElementById('explanation').classList.add('visible'); }}
}}

function nextQ() {{ if (current < QUESTIONS.length-1) {{ current++; render(); window.scrollTo(0,0); }} else showScore(); }}
function prevQ() {{ if (current > 0) {{ current--; render(); window.scrollTo(0,0); }} }}

function showScore() {{
  document.getElementById('quizBody').style.display = 'none';
  const ss = document.getElementById('scoreScreen');
  ss.classList.add('visible');

  let correct=0, wrong=0, skip=0;
  QUESTIONS.forEach((q,i) => {{
    if (!answered[i]) {{ skip++; return; }}
    if (q.type==='multiple_choice') {{ if (answers[i]===q.correct_index) correct++; else wrong++; }}
    else if (q.type==='true_false') {{ if (answers[i]===q.correct) correct++; else wrong++; }}
    else correct += 0.5; // partial credit for short answer
  }});

  const pct = Math.round(correct / QUESTIONS.length * 100);
  const msgIdx = pct>=85?0:pct>=70?1:pct>=50?2:3;
  document.getElementById('scorePct').textContent = pct+'%';
  document.getElementById('scoreMsg').textContent = messages[msgIdx][0];
  document.getElementById('scoreSub').textContent = messages[msgIdx][1];
  document.getElementById('sCorrect').textContent = Math.round(correct);
  document.getElementById('sWrong').textContent = wrong;
  document.getElementById('sSkip').textContent = skip;
  document.getElementById('progFill').style.width = '100%';
}}

function restartQuiz() {{
  current=0; answers={{}}; answered={{}};
  document.getElementById('quizBody').style.display = 'block';
  document.getElementById('scoreScreen').classList.remove('visible');
  render();
}}

render();
</script>
</body>
</html>"""


def build_report_pdf(data: dict, out_path: str):
    """Build a styled PDF report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
        ListFlowable, ListItem, KeepTogether, PageBreak
    )

    W, H = letter

    # Colors
    DARK  = colors.HexColor("#080C1C")
    ACCENT= colors.HexColor("#52C4C4")
    GOLD  = colors.HexColor("#C9A34B")
    MUTED = colors.HexColor("#8CA0D2")
    CARD  = colors.HexColor("#121A37")
    WHITE = colors.white

    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.9*inch, rightMargin=0.9*inch,
        topMargin=1*inch, bottomMargin=0.9*inch,
        title=data.get("title","Report"),
        author="The Porch is Eternal · PHI369 Labs"
    )

    styles = {
        "brand":   ParagraphStyle("brand",   fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD,   spaceAfter=4,  alignment=1, charSpace=3),
        "title":   ParagraphStyle("title",   fontName="Times-Bold",        fontSize=28, textColor=WHITE,  spaceAfter=6,  alignment=1, leading=34),
        "subtitle":ParagraphStyle("subtitle",fontName="Helvetica",         fontSize=13, textColor=MUTED,  spaceAfter=20, alignment=1),
        "h2":      ParagraphStyle("h2",      fontName="Times-Bold",        fontSize=16, textColor=ACCENT, spaceBefore=22, spaceAfter=8, leading=22),
        "body":    ParagraphStyle("body",    fontName="Helvetica",         fontSize=11, textColor=colors.HexColor("#C8D8E8"), spaceAfter=10, leading=18),
        "bullet":  ParagraphStyle("bullet",  fontName="Helvetica",         fontSize=11, textColor=colors.HexColor("#C8D8E8"), leftIndent=16, spaceAfter=6, leading=17),
        "label":   ParagraphStyle("label",   fontName="Helvetica-Bold",    fontSize=9,  textColor=MUTED,  spaceAfter=8,  charSpace=2),
        "footer":  ParagraphStyle("footer",  fontName="Helvetica",         fontSize=8,  textColor=MUTED,  alignment=1),
    }

    def bg_canvas(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        # Header bar
        canvas.setFillColor(CARD)
        canvas.rect(0, H - 0.6*inch, W, 0.6*inch, fill=1, stroke=0)
        # Accent line
        canvas.setFillColor(ACCENT)
        canvas.rect(0, H - 0.62*inch, W, 3, fill=1, stroke=0)
        # Footer
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(W/2, 0.5*inch, f"✦  The Porch is Eternal  ·  PHI369 Labs  ·  Page {doc.page}  ✦")
        canvas.restoreState()

    sections = data.get("sections", {})
    title    = data.get("title", "Report")
    subtitle = data.get("subtitle", "")
    date     = data.get("date", datetime.now().strftime("%B %d, %Y"))
    tags     = data.get("tags", [])
    read_min = data.get("reading_time_minutes", 8)

    story = []

    # Title page block
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("✦  THE PORCH IS ETERNAL  ·  PHI369 LABS  ✦", styles["brand"]))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(title, styles["title"]))
    if subtitle:
        story.append(Paragraph(subtitle, styles["subtitle"]))
    story.append(HRFlowable(width="75%", thickness=1.5, color=ACCENT, spaceAfter=12))
    story.append(Paragraph(f"{date}  ·  {read_min} min read  ·  {', '.join(tags)}", styles["footer"]))
    story.append(Spacer(1, 0.4*inch))

    # Section order
    section_order = [
        ("executive_summary", "Executive Summary"),
        ("background",        "Background"),
        ("key_findings",      "Key Findings"),
        ("deep_analysis",     "Deep Analysis"),
        ("practical_applications", "Practical Applications"),
        ("recommendations",   "Recommendations"),
        ("conclusion",        "Conclusion"),
    ]

    for key, label in section_order:
        content = sections.get(key)
        if not content:
            continue

        story.append(Paragraph(label.upper(), styles["label"]))
        story.append(Paragraph(label, styles["h2"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#2D50A0"), spaceAfter=10))

        if isinstance(content, list):
            for item in content:
                story.append(Paragraph(f"<bullet>•</bullet>  {item}", styles["bullet"]))
            story.append(Spacer(1, 0.1*inch))
        else:
            # Split into paragraphs
            for para in content.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para, styles["body"]))

        story.append(Spacer(1, 0.15*inch))

    doc.build(story, onFirstPage=bg_canvas, onLaterPages=bg_canvas)


def build_report_html(data: dict) -> str:
    """Build a styled HTML report."""
    title    = data.get("title", "Report")
    subtitle = data.get("subtitle", "")
    date     = data.get("date", datetime.now().strftime("%B %d, %Y"))
    tags     = data.get("tags", [])
    read_min = data.get("reading_time_minutes", 8)
    sections = data.get("sections", {})

    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)

    section_order = [
        ("executive_summary","Executive Summary"),
        ("background","Background"),
        ("key_findings","Key Findings"),
        ("deep_analysis","Deep Analysis"),
        ("practical_applications","Practical Applications"),
        ("recommendations","Recommendations"),
        ("conclusion","Conclusion"),
    ]

    sections_html = ""
    for key, label in section_order:
        content = sections.get(key)
        if not content: continue
        if isinstance(content, list):
            items = "".join(f"<li>{item}</li>" for item in content)
            body = f"<ul class='finding-list'>{items}</ul>"
        else:
            paras = "".join(f"<p>{p.strip()}</p>" for p in content.split("\n\n") if p.strip())
            body = paras
        sections_html += f"""
        <section class="report-section">
          <div class="section-label">{label.upper()}</div>
          <h2>{label}</h2>
          <div class="section-body">{body}</div>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap');
  :root {{ --bg:#080C1C; --card:#0F1630; --border:#2D50A0; --accent:#52C4C4; --gold:#C9A34B; --white:#F0F4FF; --muted:#8CA0D2; --body:#B8CCE8; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--white); font-family:'DM Sans',sans-serif; line-height:1.7; }}
  body::before {{ content:''; position:fixed; inset:0; background-image:radial-gradient(circle,rgba(80,110,180,.08) 1px,transparent 1px); background-size:40px 40px; pointer-events:none; z-index:0; }}

  .page {{ position:relative; z-index:1; max-width:820px; margin:0 auto; padding:60px 40px; }}

  /* Header */
  .report-header {{ text-align:center; margin-bottom:52px; padding-bottom:40px; border-bottom:1px solid rgba(45,80,160,.3); }}
  .brand {{ font-size:11px; letter-spacing:4px; color:var(--gold); font-weight:600; margin-bottom:18px; }}
  h1 {{ font-family:'Playfair Display',serif; font-size:clamp(28px,5vw,46px); line-height:1.2; background:linear-gradient(135deg,#fff 0%,#52C4C4 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:12px; }}
  .report-subtitle {{ font-size:16px; color:var(--muted); font-style:italic; margin-bottom:20px; }}
  .report-meta {{ font-size:13px; color:var(--muted); margin-bottom:16px; }}
  .report-meta span {{ color:var(--accent); }}
  .tags {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }}
  .tag {{ background:rgba(82,196,196,.1); border:1px solid rgba(82,196,196,.3); color:var(--accent); padding:4px 14px; border-radius:14px; font-size:12px; font-weight:600; }}

  /* Sections */
  .report-section {{ margin-bottom:48px; }}
  .section-label {{ font-size:10px; letter-spacing:3px; color:var(--muted); font-weight:700; margin-bottom:6px; }}
  h2 {{ font-family:'Playfair Display',serif; font-size:24px; color:var(--accent); margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid rgba(45,80,160,.25); }}
  .section-body p {{ color:var(--body); font-size:15px; margin-bottom:14px; line-height:1.8; }}
  .finding-list {{ list-style:none; display:flex; flex-direction:column; gap:12px; }}
  .finding-list li {{
    background:rgba(18,26,55,.6); border:1px solid rgba(45,80,160,.3);
    border-left:3px solid var(--accent); border-radius:10px;
    padding:14px 18px; color:var(--body); font-size:15px; line-height:1.65;
  }}
  .finding-list li::before {{ content:'✦ '; color:var(--accent); }}

  /* Footer */
  .report-footer {{ margin-top:60px; padding-top:24px; border-top:1px solid rgba(45,80,160,.2); text-align:center; font-size:12px; color:rgba(100,136,200,.5); letter-spacing:2px; }}
</style>
</head>
<body>
<div class="page">
  <header class="report-header">
    <div class="brand">✦ THE PORCH IS ETERNAL · PHI369 LABS ✦</div>
    <h1>{title}</h1>
    <p class="report-subtitle">{subtitle}</p>
    <div class="report-meta">{date} · <span>{read_min} min read</span></div>
    <div class="tags">{tags_html}</div>
  </header>

  {sections_html}

  <footer class="report-footer">✦  EVIE  ·  The Porch is Eternal  ·  PHI369 Labs  ✦</footer>
</div>
</body>
</html>"""


# ── EVIE Module class ─────────────────────────────────────────────────────────

class StudyModule(BaseModule):
    """
    EVIE Study Module — flashcards, quizzes, and reports from any topic.

    Constraint examples:

    FLASHCARDS:
    {
      "mode": "flashcards",
      "count": 20,
      "topic_override": ""   // leave blank to use topic arg
    }

    QUIZ:
    {
      "mode": "quiz",
      "count": 15,
      "difficulty": "mixed"  // easy | medium | hard | mixed
    }

    REPORT:
    {
      "mode": "report",
      "output_formats": ["pdf", "html"]  // one or both
    }
    """

    name        = "study_module"
    description = "Generate flashcards, quizzes, and reports from any topic or vault content"

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
        merged = dict(constraints or {})
        merged.setdefault("output_dir", run_folder)
        mode = str(merged.get("mode", "flashcards")).lower()
        output_formats = merged.get("output_formats") or ["pdf", "html"]
        if mode == "report" and "pdf" in output_formats and importlib.util.find_spec("reportlab") is None:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": "study_module report(pdf) requires reportlab. Install reportlab or request HTML-only output.",
                    "missing_dependency": "reportlab",
                },
            )

        context = str(merged.get("context") or "")
        try:
            out = self.run(topic=topic, constraints=merged, context=context)
            artifacts = [v for k, v in out.items() if k.endswith("_path") and isinstance(v, str)]
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"study_module failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        mode  = constraints.get("mode", "flashcards")
        count = constraints.get("count", 20)
        topic = constraints.get("topic_override", topic) or topic

        ctx_section = f"Use this source material:\n{context[:3000]}" if context else ""
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:30]

        if mode == "flashcards":
            return self._flashcards(topic, count, ctx_section, slug, ts, constraints)
        elif mode == "quiz":
            return self._quiz(topic, count, ctx_section, slug, ts, constraints)
        elif mode == "report":
            return self._report(topic, ctx_section, slug, ts, constraints)
        else:
            return {"error": f"Unknown mode '{mode}'. Use: flashcards | quiz | report"}

    def _flashcards(self, topic, count, ctx_section, slug, ts, constraints):
        print(f"  📚 Generating {count} flashcards on: {topic}")
        prompt = FLASHCARD_PROMPT.format(topic=topic, count=count, context_section=ctx_section)
        raw = _call_llm(prompt, max_tokens=4000)
        data = _parse_json(raw) or self._fallback_cards(topic)

        html = build_flashcard_html(data, topic)
        out_dir = Path(constraints.get("output_dir") or "data/artifacts/study")
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = str(out_dir / f"flashcards_{slug}_{ts}.html")
        json_path = str(out_dir / f"flashcards_{slug}_{ts}.json")
        Path(html_path).write_text(html, encoding="utf-8")
        Path(json_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

        total_cards = sum(len(c.get("cards",[])) for c in data.get("categories",[]))
        print(f"  ✅ {total_cards} cards → {html_path}")
        return {"mode": "flashcards", "html_path": html_path, "json_path": json_path, "card_count": total_cards}

    def _quiz(self, topic, count, ctx_section, slug, ts, constraints):
        diff = constraints.get("difficulty", "mixed")
        time_est = round(count * 1.5)
        print(f"  📝 Generating {count} quiz questions on: {topic}")
        prompt = QUIZ_PROMPT.format(topic=topic, count=count, context_section=ctx_section, time_est=time_est)
        raw = _call_llm(prompt, max_tokens=5000)
        data = _parse_json(raw) or self._fallback_quiz(topic)

        html = build_quiz_html(data, topic)
        out_dir = Path(constraints.get("output_dir") or "data/artifacts/study")
        out_dir.mkdir(parents=True, exist_ok=True)

        html_path = str(out_dir / f"quiz_{slug}_{ts}.html")
        json_path = str(out_dir / f"quiz_{slug}_{ts}.json")
        Path(html_path).write_text(html, encoding="utf-8")
        Path(json_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

        q_count = len(data.get("questions", []))
        print(f"  ✅ {q_count} questions → {html_path}")
        return {"mode": "quiz", "html_path": html_path, "json_path": json_path, "question_count": q_count}

    def _report(self, topic, ctx_section, slug, ts, constraints):
        print(f"  📊 Generating report on: {topic}")
        date_str = datetime.now().strftime("%B %d, %Y")
        prompt = REPORT_PROMPT.format(topic=topic, context_section=ctx_section, date=date_str)
        raw = _call_llm(prompt, max_tokens=6000)
        data = _parse_json(raw) or {"title": topic, "subtitle":"", "sections":{}, "tags":[], "reading_time_minutes":8}

        formats = constraints.get("output_formats", ["pdf", "html"])
        out_dir = Path(constraints.get("output_dir") or "data/artifacts/study")
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs = {}

        if "html" in formats:
            html = build_report_html(data)
            html_path = str(out_dir / f"report_{slug}_{ts}.html")
            Path(html_path).write_text(html, encoding="utf-8")
            outputs["html_path"] = html_path
            print(f"  ✅ Report HTML → {html_path}")

        if "pdf" in formats:
            pdf_path = str(out_dir / f"report_{slug}_{ts}.pdf")
            try:
                build_report_pdf(data, pdf_path)
                outputs["pdf_path"] = pdf_path
                print(f"  ✅ Report PDF  → {pdf_path}")
            except Exception as e:
                print(f"  ⚠️  PDF error: {e}")
                outputs["pdf_error"] = str(e)

        return {"mode": "report", **outputs, "title": data.get("title", topic)}

    def _fallback_cards(self, topic):
        return {"title": topic, "topic": topic, "categories": [
            {"name": "Core Concepts", "color": "teal", "cards": [
                {"front": f"What is {topic}?", "back": "A foundational concept requiring deeper exploration. Generate with LLM connected.", "difficulty": "easy"},
                {"front": f"Why does {topic} matter?", "back": "This connects to broader principles of understanding and application.", "difficulty": "medium"},
            ]}
        ]}

    def _fallback_quiz(self, topic):
        return {"title": f"{topic} Quiz", "topic": topic, "time_estimate_minutes": 5, "questions": [
            {"id": 1, "type": "true_false", "difficulty": "easy",
             "question": f"{topic} is an important area of study.",
             "correct": True, "explanation": "Connect your LLM to generate real questions."}
        ]}
