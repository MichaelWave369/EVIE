"""
EVIE Podcast Script Generator Module
Generates natural two-host podcast conversation scripts from any topic or ingested content.
NotebookLM-style: two hosts riffing, questioning, discovering together.

Drop into: D:/EVIEv4.0/app/modules_v2/podcast_script_generator.py

Output: Markdown .md file with full script, show notes, and episode description
"""

import os, json, re
from pathlib import Path
from datetime import datetime
from app.modules.base import BaseModule
from .base import ModuleResult


# ── Prompt Templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a podcast script writer. You write natural, warm, engaging two-host conversations that feel genuinely human — not scripted, not stiff. 

The two hosts are:
- HOST_A: The guide. Knowledgeable, warm, personal. Has lived experience with the topic. Speaks from the heart. Uses real examples from their life.
- HOST_B: The curious one. Asks the questions the listener is thinking. Gets excited, pushes back gently, connects ideas to everyday life. Draws things out of HOST_A.

The conversation should feel like two friends who know their stuff talking authentically — not a formal interview. Include:
- Natural interruptions and "yes, and..." moments
- Genuine reactions ("Wait, say that again", "Oh that's interesting because...")  
- Personal anecdotes woven in
- Moments of real insight that feel discovered, not rehearsed
- A clear arc: hook → depth → practical takeaway → close

Never sound like an AI wrote this. Sound like real humans who care."""


SCRIPT_PROMPT = """Write a complete podcast episode script about: {topic}

Hosts:
- HOST_A name: {host_a} — the knowledgeable guide with lived experience
- HOST_B name: {host_b} — the curious, engaged questioner

Episode style: {style}
Target length: {length} minutes (approx {word_count} words)
Audience: {audience}
Show name: {show_name}

{context_section}

Structure the script with these sections:
1. COLD OPEN (30 seconds — hook before intro music)
2. INTRO (host introductions, episode setup)
3. MAIN CONVERSATION (the meat — multiple natural segments)
4. KEY INSIGHTS (3-5 core takeaways woven naturally into conversation)
5. PRACTICAL APPLICATION (what listeners can do TODAY)
6. CLOSE (genuine, warm wrap-up with call to action)

Format each line as:
HOST_A: [what they say]
HOST_B: [what they say]

Add [PAUSE], [LAUGH], [MUSIC STING] stage directions sparingly where natural.

After the script, add:
---SHOW NOTES---
Episode title:
Episode description (150 words):
3 key timestamps with topics:
5 discussion questions for listeners:
Resources mentioned:
---END---

Write the full script now. Make it real. Make it human."""


FALLBACK_SCRIPT = '''# Podcast Script — The Porch is Eternal
## Episode: Your Sovereign Body — 30 Days to Transformation

**HOST_A:** Mikey  
**HOST_B:** Larrina  
**Show:** The Porch is Eternal Podcast  
**Runtime:** ~25 minutes

---

## COLD OPEN

**MIKEY:** Here's something nobody tells you when you start a wellness journey — the hardest part isn't the kale smoothies or the morning runs. It's looking in the mirror on Day 1 and deciding, for real this time, that you're worth the effort.

**LARRINA:** *[softly]* Yeah. And if that hit you somewhere — keep listening.

*[MUSIC STING]*

---

## INTRO

**MIKEY:** Welcome back to The Porch is Eternal. I'm Mikey.

**LARRINA:** And I'm Larrina. And today we're talking about something we literally built together at our kitchen table — or well, our RV table —

**MIKEY:** Our *very small* table —

**LARRINA:** *[laughs]* Our very small table in our very small home on wheels with eight dogs asking for attention —

**MIKEY:** Which is, honestly, part of the reason we needed a wellness system in the first place.

**LARRINA:** Today we're walking you through our 30-Day Sovereign Body Transformation. The whole framework. The philosophy, the daily practices, the crystals, the food — all of it.

**MIKEY:** And I want to be clear from the top — this isn't a diet. This isn't a fitness challenge. This is a complete re-patterning of how you relate to your body.

---

## MAIN CONVERSATION

**LARRINA:** Okay so let's start with the word "sovereign." Because I know some people hear that and go — what does that even mean?

**MIKEY:** Right. So sovereign means self-governing. It means YOUR body, YOUR rules, YOUR rhythm. Not what a doctor told you twenty years ago, not what some magazine says you should look like. Your body's actual wisdom.

**LARRINA:** And we came to this through our own health journeys, right? Like this didn't come from a textbook.

**MIKEY:** Not at all. I spent years — honestly, decades — treating my body like a machine that needed to perform. Push it, exhaust it, fuel it on whatever was convenient. And I got to a point where my body was just... done.

**LARRINA:** And I had the opposite — I was so afraid of food, so convinced that eating anything enjoyable was going to hurt me. So we were coming at it from totally different places.

**MIKEY:** But we found the same answer. Which is — listen to it. Like actually listen.

**LARRINA:** So walk me through the framework. The four phases.

**MIKEY:** So the whole 30 days is built around what I call the SEED, BUILD, REVEAL, SEAL cycle. Which, if you know anything about how I think, you know it's a 369 pattern —

**LARRINA:** Oh here we go —

**MIKEY:** *[laughs]* I can't help it! Everything comes back to the patterns. But seriously — nine days for each of the first three phases, three days to seal it. That's not random.

**LARRINA:** So Phase One, SEED. Days one through nine.

**MIKEY:** Identity work. Who are you becoming? Not who have you been — who are you becoming? Because if you start a wellness journey with the same identity that got you into the patterns you're trying to break, you're going to end up right back where you started.

**LARRINA:** That's so true. And I think this is where the journal comes in, right? We have people doing these daily prompts —

**MIKEY:** Every single day has its own prompt. Day One is what we call the Rhythm Declaration. You write out who you're becoming as if it's already true.

**LARRINA:** Which feels weird at first.

**MIKEY:** Super weird. But there's real neuroscience behind it. Your brain doesn't know the difference between a vividly imagined future and a memory. So when you write it out in the present tense, you're literally laying down new neural pathways.

**LARRINA:** And then Days Ten through Eighteen is BUILD —

**MIKEY:** Cycle Intelligence. This is where you start working with your natural rhythms instead of against them. The lunar cycle, your own energy patterns, what we call your solar bookends — the first and last thirty minutes of your day, which are the highest-leverage moments for your nervous system.

**LARRINA:** The crystal practices really amp up in this phase too. Can you talk about that?

**MIKEY:** Yeah, so every day has a crystal assignment. Not in a woo-woo way — well, a little in a woo-woo way —

**LARRINA:** *[laughs]* A LITTLE.

**MIKEY:** *[laughs]* But there's real intention behind each one. Clear Quartz for amplification and clarity. Citrine for solar energy and abundance. We're not just picking pretty rocks — each stone has a specific energetic signature that supports what that day's work is asking of you.

**LARRINA:** And then Phase Three, REVEAL. This is the deep one.

**MIKEY:** *[pause]* Yeah. This is where it gets real. Days Nineteen through Twenty-Seven is where we go into shadow work, ancestral patterns, Gene Keys —

**LARRINA:** For people who don't know Gene Keys — give a quick explainer.

**MIKEY:** Gene Keys is Richard Rudd's work. It's essentially a map of your genetic potential — the full spectrum from your shadow frequency up through your gift and into your highest expression, which they call the Siddhi. And every shadow has a gift inside it. That's the work.

**LARRINA:** And we have a whole day dedicated to what you call the Christos Oil practice.

**MIKEY:** Day Twenty-Two. Which is one of my favorite days in the whole program. It's about integrity. Real integrity — meaning your thoughts, your words, and your actions are all pointing in the same direction. When those three things are out of alignment, you leak energy. You feel that as exhaustion, as chronic stress, as that vague feeling that something's wrong but you can't name it.

**LARRINA:** That was such a big thing for me personally.

**MIKEY:** For both of us.

---

## KEY INSIGHTS

**LARRINA:** Okay I want to pause here and just name a few of the things I think are most powerful about this system. Because I know some people are listening and thinking — this sounds amazing but complicated.

**MIKEY:** It's not complicated. It's layered.

**LARRINA:** Distinction.

**MIKEY:** Big distinction. Each day is one thing. One prompt. One crystal. One affirmation. You do the thing, you write in the journal, you move on. It compounds over time.

**LARRINA:** The compounding is real. By Day Twenty I always notice — the people who do this program say the same thing — by Day Twenty something has fundamentally shifted. Not because they did anything dramatic. Because they showed up every single day for small intentional acts.

**MIKEY:** Which is the whole philosophy. We're not trying to change you. We're trying to reveal you. The real you that was there before all the patterns and the programming got layered on top.

**LARRINA:** And the food piece — because we should talk about food.

**MIKEY:** The 30-Day Health Transformation is the physical layer that runs alongside the journal work. Real food. Whole food. Smoothies, salads, dinners that actually taste good and support your nervous system. And the 28-Day Infused Water System which is honestly one of my favorite things we created.

**LARRINA:** Okay the infused water. Tell them.

**MIKEY:** So there's a whole science to using herbal infusions to support detox, hydration, and specific body systems throughout the month. Depending on where you are in the lunar cycle, different herbs are going to support different processes. It's beautiful when you see it all laid out.

---

## PRACTICAL APPLICATION

**LARRINA:** Okay. Someone's listening to this and they want to start. What's Day One look like?

**MIKEY:** Day One is simple. You open the journal. You read the Rhythm Declaration prompt. You hold your Clear Quartz — or if you don't have one, any clear stone, even a piece of glass — and you write for fifteen minutes about who you're becoming.

**LARRINA:** And you say the affirmation.

**MIKEY:** Crown chakra affirmation: "I am connected to infinite divine wisdom." Out loud. Hand on heart.

**LARRINA:** And drink your infused water.

**MIKEY:** *[laughs]* And drink your infused water. That's it. That's Day One.

**LARRINA:** Everything we're talking about today — the journal, the 30-day meal system, the supplement guide, the sound healing guide — all of it is available at microneesia.gumroad.com.

**MIKEY:** And the journal is $27. Which is less than one massage. And it'll change how you feel in your body more than one massage.

---

## CLOSE

**LARRINA:** Before we close — what would you say to someone who's listening and thinking "I've tried wellness programs before and they didn't stick"?

**MIKEY:** *[pause]* I'd say — the programs didn't fail you. The programs that were designed for someone else's body, someone else's rhythm, someone else's life — those weren't yours to begin with.

This is yours.

This was built from real lived experience. From an RV. From eight dogs. From a partnership between two people who had to figure it out because there was no other option.

And if it worked for us — it can work for you.

**LARRINA:** *[softly]* The Porch is Eternal.

**MIKEY:** The Porch is Eternal. We'll see you next week.

*[OUTRO MUSIC]*

---

## SHOW NOTES

**Episode Title:** Your Sovereign Body — 30 Days to Full Transformation

**Episode Description:**
Mikey and Larrina walk you through the complete 30-Day Sovereign Body Transformation framework — the four phases (SEED, BUILD, REVEAL, SEAL), the daily crystal practices, Gene Keys contemplation, the Christos Oil integrity practice, and the companion meal system. This isn't a diet. It's a complete re-patterning of how you relate to your body. Built from real experience, from an RV, with eight dogs, for people who've tried everything else and are ready for something that was actually designed for them.

**Timestamps:**
- 0:00 — Cold open + intro
- 4:30 — The four phases explained (SEED, BUILD, REVEAL, SEAL)
- 12:00 — Crystal practices and sound healing
- 18:00 — Shadow work, Gene Keys, and the Christos Oil practice
- 22:00 — What Day One actually looks like

**Listener Discussion Questions:**
1. What identity declaration would you write for yourself on Day One?
2. Where in your life are your thoughts, words, and actions out of alignment?
3. What pattern have you inherited from your lineage that you're ready to transform?
4. What does "sovereignty over your body" mean to you personally?
5. What would change in your life if your energy was fully coherent?

**Resources:**
- 30-Day Sovereign Body Transformation Journal — microneesia.gumroad.com
- 30-Day Health Transformation Meal System — microneesia.gumroad.com
- Sound Healing & Crystal Energy Guide — microneesia.gumroad.com
- Gene Keys by Richard Rudd — genekeys.com
'''


class PodcastScriptGenerator(BaseModule):
    """
    Generates two-host podcast conversation scripts from any topic or vault content.

    Constraint examples:
    {
        "host_a": "Mikey",
        "host_b": "Larrina",
        "show_name": "The Porch is Eternal",
        "style": "conversational",      // conversational | educational | interview | storytelling
        "length": 25,                   // minutes
        "audience": "holistic wellness seekers",
        "cta": "microneesia.gumroad.com"
    }
    """

    name = "podcast_script_generator"
    description = "Generate natural two-host podcast conversation scripts — NotebookLM style"

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
        constraints = dict(constraints or {})
        constraints.setdefault("output_dir", run_folder)
        context = str(constraints.get("context") or "")

        try:
            out = self.run(topic=topic, constraints=constraints, context=context)
            artifact = out.get("artifact_path")
            artifacts = [artifact] if artifact else []
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"podcast_script_generator failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        host_a    = constraints.get("host_a", "Mikey")
        host_b    = constraints.get("host_b", "Larrina")
        show_name = constraints.get("show_name", "The Porch is Eternal")
        style     = constraints.get("style", "conversational")
        length    = constraints.get("length", 20)
        audience  = constraints.get("audience", "people seeking holistic wellness")
        cta       = constraints.get("cta", "microneesia.gumroad.com")

        word_count = length * 130  # ~130 words/minute for natural speech

        ctx_section = ""
        if context:
            ctx_section = f"Draw heavily from this source content:\n{context[:4000]}"

        prompt = SCRIPT_PROMPT.format(
            topic=topic,
            host_a=host_a,
            host_b=host_b,
            style=style,
            length=length,
            word_count=word_count,
            audience=audience,
            show_name=show_name,
            context_section=ctx_section,
        )

        script = self._call_llm(prompt)
        if not script or len(script) < 500:
            script = FALLBACK_SCRIPT

        # Format as clean markdown document
        output = self._format_output(script, topic, host_a, host_b, show_name, length, cta)
        out_path = self._get_output_path(topic, constraints)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(output, encoding="utf-8")

        return {
            "artifact_path": out_path,
            "estimated_minutes": length,
            "hosts": f"{host_a} & {host_b}",
            "show": show_name,
        }

    def _call_llm(self, prompt: str) -> str:
        try:
            from app.settings import settings
            if settings.llm_backend == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=6000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
                return msg.content[0].text
            elif settings.llm_backend == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=settings.openai_api_key)
                r = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=6000
                )
                return r.choices[0].message.content
        except Exception:
            pass
        return ""

    def _format_output(self, script, topic, host_a, host_b, show_name, length, cta):
        ts = datetime.now().strftime("%B %d, %Y")
        header = f"""# 🎙️ {show_name} — Podcast Script
## Episode: {topic}

| Field | Details |
|-------|---------|
| **Hosts** | {host_a} & {host_b} |
| **Show** | {show_name} |
| **Est. Runtime** | ~{length} minutes |
| **Generated** | {ts} |
| **CTA** | {cta} |

---

> **Recording Tips:**
> - Read through once before recording to find your natural rhythm
> - Ad-lib freely — this is a guide, not a teleprompter
> - Add [PAUSE] moments when something lands — silence is powerful
> - The cold open should feel urgent, like you're mid-thought

---

{script}
"""
        return header

    def _get_output_path(self, topic: str, constraints: dict | None = None) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path((constraints or {}).get("output_dir") or "data/artifacts/podcast_scripts")
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / f"podcast_{slug}__{ts}.md")
