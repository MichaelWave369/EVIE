"""
EVIE ElevenLabs Audio Generator Module
Turns podcast scripts into real two-voice MP3 audio using ElevenLabs TTS.

Drop into: D:/EVIEv4.0/app/modules_v2/audio_generator.py

Also add to your .env file:
  EV_ELEVENLABS_API_KEY=your-key-here
  EV_VOICE_HOST_A=your-voice-id-for-host-a
  EV_VOICE_HOST_B=your-voice-id-for-host-b

Get your API key: https://elevenlabs.io
Free tier: 10,000 characters/month (~15 min audio)
Starter tier ($5/mo): 30,000 characters
Creator tier ($22/mo): 100,000 characters + voice cloning

To clone your own voice:
  1. Go to elevenlabs.io → Voices → Add Voice → Instant Voice Clone
  2. Upload 1-5 minutes of clean audio (no music, no background noise)
  3. Copy the Voice ID it generates
  4. Paste into EV_VOICE_HOST_A in your .env
"""

import os, re, json, time
import shutil
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.modules.base import BaseModule
from .base import ModuleResult


# ── Default voice IDs (ElevenLabs built-in voices) ───────────────────────────
# These are free to use on any plan. Swap for your cloned voice IDs.

DEFAULT_VOICES = {
    # Warm, conversational male voices
    "adam":    "pNInz6obpgDQGcFmaJgB",   # Adam — deep, authoritative
    "antoni":  "ErXwobaYiN019PkySvjV",   # Antoni — well-rounded, warm
    "josh":    "TxGEqnHWrfWFTfGW9XjX",   # Josh — young, energetic
    "arnold":  "VR6AewLTigWG4xSOukaG",   # Arnold — crisp, confident
    # Warm, conversational female voices
    "rachel":  "21m00Tcm4TlvDq8ikWAM",   # Rachel — calm, professional
    "domi":    "AZnzlk1XvdvUeBnXmlld",   # Domi — strong, conversational
    "bella":   "EXAVITQu4vr4xnSDxMaL",   # Bella — soft, warm
    "elli":    "MF3mGyEYCl7XYWbV9V6O",   # Elli — emotional, relatable
    "sarah":   "EXAVITQu4vr4xnSDxMaL",   # Sarah — natural
}

# ── Voice settings for natural conversation ───────────────────────────────────

VOICE_SETTINGS = {
    "stability": 0.45,          # Lower = more expressive/varied
    "similarity_boost": 0.85,   # Higher = closer to voice clone
    "style": 0.35,              # Style exaggeration (0-1)
    "use_speaker_boost": True,  # Enhance clarity
}

STAGE_DIRECTIONS = [
    r'\[PAUSE\]', r'\[LAUGH\]', r'\[LAUGHS\]', r'\[MUSIC STING\]',
    r'\[OUTRO MUSIC.*?\]', r'\[MUSIC.*?\]', r'\*\[.*?\]\*', r'\[.*?\]'
]


class AudioGenerator(BaseModule):
    """
    Converts podcast script markdown into real two-voice MP3 audio.
    
    Supports:
    - Two distinct voices (HOST_A and HOST_B)
    - Your own cloned voice via ElevenLabs Instant Voice Clone
    - Automatic script parsing from podcast_script_generator output
    - Line-by-line generation with natural pauses between speakers
    - Final merged MP3 output
    
    Constraint examples:
    {
        "script_path": "data/artifacts/podcast_scripts/podcast_xyz.md",
        "voice_a": "adam",          // voice name or ElevenLabs voice ID
        "voice_b": "rachel",        // voice name or ElevenLabs voice ID  
        "host_a_name": "MIKEY",     // must match label in script
        "host_b_name": "LARRINA",   // must match label in script
        "model": "eleven_turbo_v2", // eleven_turbo_v2 (fast) | eleven_multilingual_v2 (best)
        "output_format": "mp3_44100_128",
        "pause_between_speakers": 0.4,  // seconds of silence between turns
        "max_chars": 50000          // safety limit for API usage
    }
    """

    name = "audio_generator"
    description = "Convert podcast scripts into real two-voice MP3 audio via ElevenLabs"

    ELEVENLABS_API = "https://api.elevenlabs.io/v1"

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

        missing = []
        if shutil.which("ffmpeg") is None:
            missing.append("ffmpeg")
        if importlib.util.find_spec("pydub") is None:
            missing.append("pydub")
        if importlib.util.find_spec("requests") is None:
            missing.append("requests")
        if missing:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": f"audio_generator requires missing dependencies: {', '.join(missing)}.",
                    "missing_dependencies": missing,
                },
            )

        if not self._get_api_key():
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": "audio_generator requires EV_ELEVENLABS_API_KEY (or configured elevenlabs_api_key).",
                    "missing_dependency": "elevenlabs_api_key",
                },
            )

        script_path = str(merged.get("script_path") or "").strip()
        if script_path and not Path(script_path).exists():
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={
                    "ok": False,
                    "error": f"audio_generator script_path not found: {script_path}",
                    "missing_input": "script_path",
                },
            )

        context = str(merged.get("context") or "")
        try:
            out = self.run(topic=topic, constraints=merged, context=context)
            if out.get("error"):
                return ModuleResult(name=self.name, artifacts=[], summary={"ok": False, **out})
            artifacts = [v for k, v in out.items() if k.endswith("_path") and isinstance(v, str)]
            return ModuleResult(name=self.name, artifacts=artifacts, summary=out)
        except Exception as exc:
            return ModuleResult(
                name=self.name,
                artifacts=[],
                summary={"ok": False, "error": f"audio_generator failed: {exc}"},
            )

    def run(self, topic: str, constraints: dict, context: str = "") -> dict:
        import requests

        api_key = self._get_api_key()
        if not api_key:
            return {"error": "EV_ELEVENLABS_API_KEY not set in .env — add it to use audio generation"}

        # Get voice IDs
        voice_a_id = self._resolve_voice(
            constraints.get("voice_a", os.getenv("EV_VOICE_HOST_A", "adam")),
            api_key
        )
        voice_b_id = self._resolve_voice(
            constraints.get("voice_b", os.getenv("EV_VOICE_HOST_B", "rachel")),
            api_key
        )

        host_a_name = constraints.get("host_a_name", "MIKEY").upper()
        host_b_name = constraints.get("host_b_name", "LARRINA").upper()
        model       = constraints.get("model", "eleven_turbo_v2")
        pause_secs  = constraints.get("pause_between_speakers", 0.4)
        max_chars   = constraints.get("max_chars", 50000)
        out_fmt     = constraints.get("output_format", "mp3_44100_128")

        # Load script
        script_path = constraints.get("script_path", "")
        if script_path and Path(script_path).exists():
            raw_script = Path(script_path).read_text(encoding="utf-8")
        elif context:
            raw_script = context
        else:
            return {"error": "Provide script_path or paste script content in the context field"}

        # Parse into turns
        turns = self._parse_script(raw_script, host_a_name, host_b_name)
        if not turns:
            return {"error": "No dialogue found in script. Make sure lines start with HOST_A: or HOST_B: format"}

        # Check character count
        total_chars = sum(len(t["text"]) for t in turns)
        if total_chars > max_chars:
            return {
                "error": f"Script is {total_chars} characters — exceeds limit of {max_chars}. "
                         f"Reduce max_chars limit or trim the script. "
                         f"At 10k chars/min this would use ~{total_chars//150:.0f} min of quota."
            }

        # Generate audio for each turn
        audio_chunks = []
        silence_chunk = self._generate_silence(pause_secs)
        
        print(f"Generating {len(turns)} dialogue turns ({total_chars} characters)...")
        
        for i, turn in enumerate(turns):
            voice_id = voice_a_id if turn["host"] == "A" else voice_b_id
            print(f"  Turn {i+1}/{len(turns)}: {turn['host']} — {turn['text'][:50]}...")
            
            audio = self._synthesize(turn["text"], voice_id, model, out_fmt, api_key)
            if audio:
                audio_chunks.append(audio)
                if i < len(turns) - 1:
                    audio_chunks.append(silence_chunk)
            
            # Rate limit: ElevenLabs allows ~2 req/sec on free tier
            time.sleep(0.5)

        if not audio_chunks:
            return {"error": "No audio was generated — check your API key and voice IDs"}

        # Merge all chunks into single MP3
        merged = self._merge_audio(audio_chunks)
        out_path = self._get_output_path(topic, constraints)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(merged)

        # Also save a metadata file
        meta_path = out_path.replace(".mp3", "_info.json")
        meta = {
            "topic": topic,
            "turns": len(turns),
            "total_characters": total_chars,
            "estimated_minutes": total_chars / 800,
            "voices": {"host_a": voice_a_id, "host_b": voice_b_id},
            "model": model,
            "generated": datetime.now().isoformat(),
        }
        Path(meta_path).write_text(json.dumps(meta, indent=2))

        return {
            "artifact_path": out_path,
            "turns_generated": len(turns),
            "total_characters": total_chars,
            "estimated_minutes": round(total_chars / 800, 1),
            "voices": {"host_a": voice_a_id, "host_b": voice_b_id},
        }

    def _get_api_key(self) -> Optional[str]:
        # Check .env via settings first
        try:
            from app.settings import settings
            key = getattr(settings, "elevenlabs_api_key", None)
            if key:
                return key
        except Exception:
            pass
        return os.getenv("EV_ELEVENLABS_API_KEY", "")

    def _resolve_voice(self, voice_ref: str, api_key: str) -> str:
        """Resolve voice name or ID to an actual ElevenLabs voice ID."""
        # Already a voice ID (long alphanumeric string)
        if len(voice_ref) > 15 and re.match(r'^[a-zA-Z0-9]+$', voice_ref):
            return voice_ref
        # Named default voice
        if voice_ref.lower() in DEFAULT_VOICES:
            return DEFAULT_VOICES[voice_ref.lower()]
        # Try to find by name in user's voice library
        try:
            import requests
            resp = requests.get(
                f"{self.ELEVENLABS_API}/voices",
                headers={"xi-api-key": api_key},
                timeout=10
            )
            if resp.status_code == 200:
                voices = resp.json().get("voices", [])
                for v in voices:
                    if v["name"].lower() == voice_ref.lower():
                        return v["voice_id"]
        except Exception:
            pass
        # Fallback to adam
        return DEFAULT_VOICES["adam"]

    def _parse_script(self, script: str, host_a: str, host_b: str) -> list:
        """Parse markdown script into dialogue turns."""
        turns = []
        # Remove stage directions, headers, tables
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip markdown headers, tables, blockquotes
            if line.startswith(('#', '|', '>', '---', '*[', '![')):
                continue

            # Match HOST_A or HOST_B lines
            # Formats: "MIKEY: text", "**MIKEY:** text", "HOST_A: text"
            for host_label, host_key in [(host_a, "A"), (host_b, "B"), ("HOST_A", "A"), ("HOST_B", "B")]:
                patterns = [
                    rf'^\*?\*?{re.escape(host_label)}\*?\*?:\s*(.+)$',
                    rf'^{re.escape(host_label)}:\s*(.+)$',
                ]
                for pat in patterns:
                    m = re.match(pat, line, re.IGNORECASE)
                    if m:
                        text = m.group(1).strip()
                        # Clean stage directions and markdown
                        for sd in STAGE_DIRECTIONS:
                            text = re.sub(sd, '', text, flags=re.IGNORECASE)
                        text = re.sub(r'\*+', '', text)  # Remove bold/italic markers
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        if len(text) > 3:  # Skip empty or near-empty lines
                            # Merge with previous turn if same host (natural flow)
                            if turns and turns[-1]["host"] == host_key and len(turns[-1]["text"]) < 200:
                                turns[-1]["text"] += " " + text
                            else:
                                turns.append({"host": host_key, "text": text})
                        break

        return turns

    def _synthesize(self, text: str, voice_id: str, model: str, 
                    output_format: str, api_key: str) -> Optional[bytes]:
        """Call ElevenLabs TTS API for a single text chunk."""
        import requests
        
        url = f"{self.ELEVENLABS_API}/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": VOICE_SETTINGS,
            "output_format": output_format,
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    return resp.content
                elif resp.status_code == 429:
                    # Rate limited — wait and retry
                    wait = 2 ** attempt
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                elif resp.status_code == 401:
                    print("    Invalid API key")
                    return None
                else:
                    print(f"    API error {resp.status_code}: {resp.text[:200]}")
                    return None
            except Exception as e:
                print(f"    Request error: {e}")
                if attempt < 2:
                    time.sleep(1)

        return None

    def _generate_silence(self, seconds: float) -> bytes:
        """Generate silent MP3 bytes for pauses between speakers."""
        # Minimal valid MP3 silence frame
        # 44100 Hz, 128 kbps silence
        # We'll use a simple approach: generate PCM silence and encode
        # For simplicity, return a minimal MP3 frame repeated
        # A proper implementation would use pydub or ffmpeg
        
        # Minimal MP3 frame (valid but silent)
        # Each frame at 128kbps is ~417 bytes, 26ms
        frames_needed = max(1, int(seconds / 0.026))
        
        # Minimal MP3 header for silence
        # ID3 + silent MPEG frame
        silent_frame = bytes([
            0xFF, 0xFB, 0x90, 0x00,  # MPEG1 Layer3 128kbps 44100Hz
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        ] + [0x00] * 369)  # 369 for PHI369 ;)
        
        return silent_frame * frames_needed

    def _merge_audio(self, chunks: list) -> bytes:
        """Concatenate MP3 chunks into single file."""
        # Simple concatenation works for MP3
        # For production, use pydub for proper ID3 tagging
        merged = b"".join(chunks)
        
        # Try pydub for cleaner merge if available
        try:
            from pydub import AudioSegment
            import io
            
            segments = []
            for chunk in chunks:
                try:
                    seg = AudioSegment.from_mp3(io.BytesIO(chunk))
                    segments.append(seg)
                except Exception:
                    pass
            
            if segments:
                combined = segments[0]
                for seg in segments[1:]:
                    combined += seg
                
                out_buffer = io.BytesIO()
                combined.export(out_buffer, format="mp3", bitrate="128k")
                return out_buffer.getvalue()
        except ImportError:
            pass
        
        return merged

    def _get_output_path(self, topic: str, constraints: dict | None = None) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', topic.lower())[:40]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path((constraints or {}).get("output_dir") or "data/artifacts/audio")
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / f"podcast_{slug}__{ts}.mp3")


# ── Standalone voice browser helper ──────────────────────────────────────────

def list_available_voices(api_key: str) -> list:
    """
    Call this from the EVIE console to see all voices in your ElevenLabs library.
    
    Usage in Python:
        from app.modules_v2.audio_generator import list_available_voices
        voices = list_available_voices("your-api-key")
        for v in voices:
            print(v['name'], v['voice_id'])
    """
    import requests
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=10
    )
    if resp.status_code == 200:
        return [
            {"name": v["name"], "voice_id": v["voice_id"], "category": v.get("category", "?")}
            for v in resp.json().get("voices", [])
        ]
    return []


def check_quota(api_key: str) -> dict:
    """
    Check your remaining ElevenLabs character quota.
    
    Usage:
        from app.modules_v2.audio_generator import check_quota
        print(check_quota("your-api-key"))
    """
    import requests
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": api_key},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        sub = data.get("subscription", {})
        used = sub.get("character_count", 0)
        limit = sub.get("character_limit", 0)
        remaining = limit - used
        return {
            "plan": sub.get("tier", "unknown"),
            "characters_used": used,
            "characters_limit": limit,
            "characters_remaining": remaining,
            "estimated_minutes_remaining": round(remaining / 800, 1),
            "reset_date": sub.get("next_character_count_reset_unix", "unknown"),
        }
    return {"error": f"API returned {resp.status_code}"}
