const pptxgen = require("pptxgenjs");

// ── NotebookLM Palette ─────────────────────────────────────────────────────
const BG_DARK    = "080C1C";
const BG_CARD    = "121A37";
const ACCENT     = "52C4C4";   // teal
const ACCENT2    = "8C64DC";   // soft purple
const GOLD       = "C9A34B";   // warm gold
const WHITE      = "FFFFFF";
const MUTED      = "8CA0D2";
const LABEL      = "6488C8";
const BORDER     = "2D50A0";

const makeShadow = () => ({
  type: "outer", blur: 12, offset: 4, angle: 135,
  color: "000000", opacity: 0.35
});

const glowShadow = () => ({
  type: "outer", blur: 20, offset: 0, angle: 135,
  color: "52C4C4", opacity: 0.25
});

let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author  = "The Porch is Eternal";
pres.title   = "30-Day Sovereign Body Transformation";

// helper: dot-grid overlay (5x5 pattern of faint dots via tiny rectangles)
function addDotGrid(slide) {
  const dotSpacing = 0.45;
  const cols = Math.ceil(10 / dotSpacing);
  const rows = Math.ceil(5.625 / dotSpacing);
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c <= cols; c++) {
      slide.addShape(pres.shapes.OVAL, {
        x: c * dotSpacing - 0.03,
        y: r * dotSpacing - 0.02,
        w: 0.035, h: 0.035,
        fill: { color: "5070B0", transparency: 88 },
        line: { color: "5070B0", transparency: 88 }
      });
    }
  }
}

// helper: glass card
function glassCard(slide, x, y, w, h, opts = {}) {
  const radius = opts.radius || 0.12;
  // Glow layer
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x - 0.04, y: y - 0.04, w: w + 0.08, h: h + 0.08,
    fill: { color: ACCENT, transparency: 96 },
    line: { color: ACCENT, transparency: 96 },
    rectRadius: radius + 0.02,
    shadow: { type: "outer", blur: 18, offset: 0, angle: 0, color: "52C4C4", opacity: 0.15 }
  });
  // Card body
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: BG_CARD, transparency: opts.transparency || 20 },
    line: { color: BORDER, transparency: 55 },
    rectRadius: radius,
    shadow: makeShadow()
  });
  // Top highlight (glass sheen)
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: x + 0.02, y: y + 0.02, w: w - 0.04, h: h * 0.18,
    fill: { color: WHITE, transparency: 93 },
    line: { color: WHITE, transparency: 99 },
    rectRadius: radius,
  });
}

// helper: teal badge number
function badge(slide, x, y, num) {
  slide.addShape(pres.shapes.OVAL, {
    x, y, w: 0.55, h: 0.55,
    fill: { color: ACCENT }, line: { color: ACCENT },
    shadow: { type: "outer", blur: 8, offset: 0, angle: 0, color: "52C4C4", opacity: 0.4 }
  });
  slide.addText(String(num), {
    x, y: y + 0.04, w: 0.55, h: 0.47,
    fontSize: 18, bold: true, color: BG_DARK,
    fontFace: "Georgia", align: "center", valign: "middle"
  });
}

// helper: pill tag
function pillTag(slide, x, y, text, color = ACCENT) {
  const w = text.length * 0.085 + 0.25;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h: 0.28,
    fill: { color: color, transparency: 82 },
    line: { color: color, transparency: 55 },
    rectRadius: 0.14
  });
  slide.addText(text, {
    x: x + 0.05, y: y + 0.02, w: w - 0.1, h: 0.24,
    fontSize: 10, bold: true, color: color,
    fontFace: "Calibri", align: "center", valign: "middle"
  });
  return x + w + 0.1;
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ════════════════════════════════════════════════════════════════════════════
let s1 = pres.addSlide();
s1.background = { color: BG_DARK };
addDotGrid(s1);

// Large teal glow circle (atmospheric)
s1.addShape(pres.shapes.OVAL, {
  x: 2.5, y: -1.2, w: 5, h: 5,
  fill: { color: ACCENT, transparency: 93 },
  line: { color: ACCENT, transparency: 93 }
});
// Purple glow
s1.addShape(pres.shapes.OVAL, {
  x: -1, y: 0, w: 4, h: 4,
  fill: { color: ACCENT2, transparency: 93 },
  line: { color: ACCENT2, transparency: 93 }
});

// Brand label
s1.addText("✦   T H E   P O R C H   I S   E T E R N A L   ✦", {
  x: 0.5, y: 0.38, w: 9, h: 0.35,
  fontSize: 11, color: GOLD, bold: true,
  fontFace: "Calibri", align: "center", charSpacing: 3
});

// Pill tags row
let tx = 1.5;
const tags = [
  ["Crystal Practices", ACCENT],
  ["Chakra Alignment", ACCENT2],
  ["Gene Keys", GOLD],
  ["Rhythm Code", ACCENT],
];
tags.forEach(([t, c]) => { tx = pillTag(s1, tx, 0.85, t, c); });

// Main title
s1.addText("30-Day Sovereign", {
  x: 0.5, y: 1.22, w: 9, h: 1.05,
  fontSize: 58, bold: true, color: WHITE,
  fontFace: "Georgia", align: "center"
});
s1.addText("Body Transformation", {
  x: 0.5, y: 2.18, w: 9, h: 0.9,
  fontSize: 46, bold: true, color: ACCENT,
  fontFace: "Georgia", align: "center"
});

// Tagline
s1.addText("A complete re-patterning of how you relate to your body", {
  x: 1, y: 3.22, w: 8, h: 0.45,
  fontSize: 15, color: MUTED, italic: true,
  fontFace: "Calibri", align: "center"
});

// Bottom teal line
s1.addShape(pres.shapes.LINE, {
  x: 1.0, y: 4.15, w: 8, h: 0,
  line: { color: ACCENT, width: 1, transparency: 55 }
});

// URL
s1.addText("microneesia.gumroad.com", {
  x: 0.5, y: 4.28, w: 9, h: 0.35,
  fontSize: 13, color: MUTED, fontFace: "Calibri", align: "center"
});

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — FOUR PHASES (glass cards)
// ════════════════════════════════════════════════════════════════════════════
let s2 = pres.addSlide();
s2.background = { color: BG_DARK };
addDotGrid(s2);

// Glow
s2.addShape(pres.shapes.OVAL, {
  x: 3, y: -0.5, w: 4, h: 4,
  fill: { color: ACCENT, transparency: 94 }, line: { color: ACCENT, transparency: 94 }
});

// Section label
s2.addText("THE FRAMEWORK", {
  x: 0.5, y: 0.22, w: 3, h: 0.3,
  fontSize: 11, bold: true, color: LABEL,
  fontFace: "Calibri", charSpacing: 2
});
s2.addShape(pres.shapes.OVAL, {
  x: 2.02, y: 0.28, w: 0.09, h: 0.09,
  fill: { color: ACCENT }, line: { color: ACCENT }
});

// Title
s2.addText("Four Sacred Phases", {
  x: 0.5, y: 0.55, w: 9, h: 0.7,
  fontSize: 36, bold: true, color: WHITE,
  fontFace: "Georgia", align: "left"
});

const phases = [
  { num: 1, name: "SEED",   days: "Days 1–9",   tag: "Identity Map",       color: ACCENT,
    desc: "Who are you becoming? Daily crystal + journal work to plant the energetic foundation." },
  { num: 2, name: "BUILD",  days: "Days 10–18", tag: "Cycle Intelligence",  color: "64A0FF",
    desc: "Remove friction. Align with solar, lunar, and nervous system cycles." },
  { num: 3, name: "REVEAL", days: "Days 19–27", tag: "Sacred Refinement",   color: ACCENT2,
    desc: "Gene Keys. Christos Oil. Ancestral wound and gift transformation." },
  { num: 4, name: "SEAL",   days: "Days 28–30", tag: "Lock It In",          color: GOLD,
    desc: "Ceremony. Sovereign vow. Rhythm Code dashboard signed and sealed." },
];

const cardW = 2.05, cardH = 3.6, cardGap = 0.12;
const cardStartX = 0.45, cardY = 1.38;

phases.forEach((ph, i) => {
  const x = cardStartX + i * (cardW + cardGap);
  const col = ph.color;

  glassCard(s2, x, cardY, cardW, cardH);

  // Top color accent line
  s2.addShape(pres.shapes.RECTANGLE, {
    x, y: cardY, w: cardW, h: 0.04,
    fill: { color: col }, line: { color: col }
  });

  // Badge
  badge(s2, x + 0.08, cardY + 0.12, ph.num);

  // Phase name
  s2.addText(ph.name, {
    x: x + 0.08, y: cardY + 0.78, w: cardW - 0.16, h: 0.52,
    fontSize: 24, bold: true, color: col,
    fontFace: "Georgia", align: "left"
  });

  // Tag pill
  pillTag(s2, x + 0.08, cardY + 1.32, ph.tag, col);

  // Days
  s2.addText(ph.days, {
    x: x + 0.08, y: cardY + 1.68, w: cardW - 0.16, h: 0.3,
    fontSize: 12, bold: true, color: MUTED, fontFace: "Calibri"
  });

  // Divider line
  s2.addShape(pres.shapes.LINE, {
    x: x + 0.08, y: cardY + 2.02, w: cardW - 0.25, h: 0,
    line: { color: col, width: 1, transparency: 70 }
  });

  // Desc
  s2.addText(ph.desc, {
    x: x + 0.08, y: cardY + 2.12, w: cardW - 0.16, h: 1.2,
    fontSize: 11, color: MUTED, fontFace: "Calibri", valign: "top"
  });

  // Watermark number
  s2.addText(String(ph.num).padStart(2,"0"), {
    x: x + cardW - 0.7, y: cardY + 0.1, w: 0.7, h: 0.7,
    fontSize: 52, bold: true, color: col,
    fontFace: "Georgia", align: "right",
    transparency: 88
  });
});

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — DAILY PRACTICE SYSTEM
// ════════════════════════════════════════════════════════════════════════════
let s3 = pres.addSlide();
s3.background = { color: BG_DARK };
addDotGrid(s3);

s3.addShape(pres.shapes.OVAL, {
  x: 1, y: -1, w: 5, h: 5,
  fill: { color: ACCENT2, transparency: 94 }, line: { color: ACCENT2, transparency: 94 }
});

s3.addText("DAILY PRACTICE", {
  x: 0.5, y: 0.22, w: 4, h: 0.3,
  fontSize: 11, bold: true, color: LABEL, fontFace: "Calibri", charSpacing: 2
});
s3.addText("Five Components. Every Day.", {
  x: 0.5, y: 0.55, w: 9, h: 0.65,
  fontSize: 34, bold: true, color: WHITE, fontFace: "Georgia"
});
s3.addText("Each day contains all five practices woven into a single coherent experience.", {
  x: 0.5, y: 1.22, w: 9, h: 0.38,
  fontSize: 14, color: MUTED, italic: true, fontFace: "Calibri"
});

const practices = [
  { icon: "🔮", name: "Crystal",   color: ACCENT,  desc: "Specific stone pairings with daily intentions. Morning placements, body layouts, altar work." },
  { icon: "✨", name: "Chakra",    color: ACCENT2, desc: "Targeted affirmations for each energy center. Speak them hand on heart." },
  { icon: "🌀", name: "Coherence", color: GOLD,    desc: "Spoken vows aligning thought, word, and action at key transition points." },
  { icon: "📖", name: "Journal",   color: "64A0FF",desc: "4-5 deep prompts per day — Gene Keys, ancestral work, nervous system, desire." },
  { icon: "🎵", name: "Sound",     color: MUTED,   desc: "Solfeggio pairings: 528Hz transformation · 396Hz liberation · 963Hz divine." },
];

const pW = 1.75, pH = 3.0, pGap = 0.15, pStartX = 0.35, pY = 1.75;

practices.forEach((p, i) => {
  const x = pStartX + i * (pW + pGap);
  glassCard(s3, x, pY, pW, pH);

  // Icon circle
  s3.addShape(pres.shapes.OVAL, {
    x: x + pW/2 - 0.38, y: pY + 0.2, w: 0.76, h: 0.76,
    fill: { color: BG_CARD }, line: { color: p.color, transparency: 50 }
  });
  s3.addText(p.icon, {
    x: x + pW/2 - 0.3, y: pY + 0.25, w: 0.6, h: 0.6,
    fontSize: 24, align: "center", valign: "middle"
  });

  // Color top bar
  s3.addShape(pres.shapes.RECTANGLE, {
    x, y: pY, w: pW, h: 0.03, fill: { color: p.color }, line: { color: p.color }
  });

  // Name
  s3.addText(p.name, {
    x: x + 0.08, y: pY + 1.06, w: pW - 0.16, h: 0.42,
    fontSize: 16, bold: true, color: p.color,
    fontFace: "Georgia", align: "center"
  });

  // Desc
  s3.addText(p.desc, {
    x: x + 0.1, y: pY + 1.52, w: pW - 0.2, h: 1.35,
    fontSize: 11, color: MUTED, fontFace: "Calibri", align: "center", valign: "top"
  });
});

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — CHAKRA + CRYSTAL reference (two-column)
// ════════════════════════════════════════════════════════════════════════════
let s4 = pres.addSlide();
s4.background = { color: BG_DARK };
addDotGrid(s4);

s4.addShape(pres.shapes.OVAL, {
  x: 6, y: 2, w: 5, h: 5,
  fill: { color: ACCENT, transparency: 94 }, line: { color: ACCENT, transparency: 94 }
});

s4.addText("ALIGNMENT REFERENCE", {
  x: 0.5, y: 0.22, w: 5, h: 0.3,
  fontSize: 11, bold: true, color: LABEL, fontFace: "Calibri", charSpacing: 2
});
s4.addText("7 Chakras · 7 Crystals", {
  x: 0.5, y: 0.55, w: 9, h: 0.65,
  fontSize: 34, bold: true, color: WHITE, fontFace: "Georgia"
});

// Left column — Chakras
glassCard(s4, 0.4, 1.32, 4.5, 4.0);
s4.addShape(pres.shapes.RECTANGLE, {
  x: 0.4, y: 1.32, w: 4.5, h: 0.03, fill: { color: ACCENT2 }, line: { color: ACCENT2 }
});
s4.addText("CHAKRA SYSTEM", {
  x: 0.55, y: 1.4, w: 4.2, h: 0.38,
  fontSize: 13, bold: true, color: ACCENT2, fontFace: "Calibri", charSpacing: 1
});

const chakras = [
  { name: "Crown",      color: "9B59B6", note: "Divine wisdom & connection" },
  { name: "Third Eye",  color: "5D2D6E", note: "Intuition & inner knowing" },
  { name: "Throat",     color: "1A5276", note: "Authentic expression" },
  { name: "Heart",      color: "1E7A46", note: "Compassion & love" },
  { name: "Solar",      color: "B7950B", note: "Personal power & will" },
  { name: "Sacral",     color: "BA4A00", note: "Creativity & desire" },
  { name: "Root",       color: "922B21", note: "Grounding & safety" },
];

chakras.forEach((ch, i) => {
  const cy = 1.84 + i * 0.47;
  s4.addShape(pres.shapes.OVAL, {
    x: 0.55, y: cy + 0.06, w: 0.3, h: 0.3,
    fill: { color: ch.color }, line: { color: ch.color }
  });
  s4.addText(ch.name, {
    x: 0.95, y: cy, w: 1.4, h: 0.38,
    fontSize: 13, bold: true, color: WHITE, fontFace: "Calibri"
  });
  s4.addText(ch.note, {
    x: 2.38, y: cy + 0.02, w: 2.3, h: 0.36,
    fontSize: 11, color: MUTED, fontFace: "Calibri", italic: true
  });
});

// Right column — Crystals
glassCard(s4, 5.1, 1.32, 4.5, 4.0);
s4.addShape(pres.shapes.RECTANGLE, {
  x: 5.1, y: 1.32, w: 4.5, h: 0.03, fill: { color: ACCENT }, line: { color: ACCENT }
});
s4.addText("CRYSTAL PAIRINGS", {
  x: 5.25, y: 1.4, w: 4.2, h: 0.38,
  fontSize: 13, bold: true, color: ACCENT, fontFace: "Calibri", charSpacing: 1
});

const crystals = [
  { name: "Clear Quartz",    color: "C8E6FF", use: "Amplify intentions, Day 1" },
  { name: "Citrine",         color: "FFD966", use: "Solar abundance, Days 8–10" },
  { name: "Rose Quartz",     color: "F4A7B9", use: "Heart healing, Days 5, 20" },
  { name: "Amethyst",        color: "9B59B6", use: "Intuition, Gene Keys Day 21" },
  { name: "Black Tourmaline",color: "555555", use: "Protection, shadow work" },
  { name: "Selenite",        color: "E8E8FF", use: "Ceremony & clearing" },
  { name: "Carnelian",       color: "E8693A", use: "Vitality & desire work" },
];

crystals.forEach((cr, i) => {
  const cy = 1.84 + i * 0.47;
  // Diamond icon
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 5.27, y: cy + 0.04, w: 0.28, h: 0.28,
    fill: { color: cr.color, transparency: 20 },
    line: { color: cr.color, transparency: 40 },
    rotate: 45
  });
  s4.addText(cr.name, {
    x: 5.66, y: cy, w: 1.8, h: 0.38,
    fontSize: 12, bold: true, color: WHITE, fontFace: "Calibri"
  });
  s4.addText(cr.use, {
    x: 7.5, y: cy + 0.02, w: 1.9, h: 0.36,
    fontSize: 10, color: MUTED, fontFace: "Calibri", italic: true
  });
});

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — CTA
// ════════════════════════════════════════════════════════════════════════════
let s5 = pres.addSlide();
s5.background = { color: BG_DARK };
addDotGrid(s5);

// Large glow
s5.addShape(pres.shapes.OVAL, {
  x: 1.5, y: 0.3, w: 7, h: 7,
  fill: { color: ACCENT, transparency: 95 }, line: { color: ACCENT, transparency: 95 }
});
s5.addShape(pres.shapes.OVAL, {
  x: -0.5, y: 1, w: 5, h: 5,
  fill: { color: ACCENT2, transparency: 95 }, line: { color: ACCENT2, transparency: 95 }
});

// Central glass card
glassCard(s5, 1.5, 0.8, 7, 4.0, { transparency: 15 });
s5.addShape(pres.shapes.RECTANGLE, {
  x: 1.5, y: 0.8, w: 7, h: 0.04,
  fill: { color: ACCENT }, line: { color: ACCENT }
});

s5.addText("✦", {
  x: 1.5, y: 0.95, w: 7, h: 0.9,
  fontSize: 52, color: ACCENT, align: "center",
  shadow: { type: "outer", blur: 15, offset: 0, angle: 0, color: "52C4C4", opacity: 0.5 }
});

s5.addText("Your body has been waiting.", {
  x: 1.5, y: 1.85, w: 7, h: 0.72,
  fontSize: 34, bold: true, color: WHITE,
  fontFace: "Georgia", align: "center"
});

s5.addText("30 days. 4 phases. One sovereign you.", {
  x: 2, y: 2.6, w: 6, h: 0.45,
  fontSize: 16, color: MUTED, italic: true,
  fontFace: "Calibri", align: "center"
});

// CTA button
s5.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 3.2, y: 3.2, w: 3.6, h: 0.72,
  fill: { color: ACCENT }, line: { color: ACCENT },
  rectRadius: 0.1,
  shadow: { type: "outer", blur: 16, offset: 0, angle: 0, color: "52C4C4", opacity: 0.45 }
});
s5.addText("Get the Journal — $27", {
  x: 3.2, y: 3.2, w: 3.6, h: 0.72,
  fontSize: 18, bold: true, color: BG_DARK,
  fontFace: "Georgia", align: "center", valign: "middle"
});

s5.addText("microneesia.gumroad.com", {
  x: 1.5, y: 4.08, w: 7, h: 0.4,
  fontSize: 15, color: ACCENT, fontFace: "Calibri", align: "center"
});

s5.addText("The Porch is Eternal  ·  PHI369 Labs", {
  x: 1.5, y: 4.62, w: 7, h: 0.35,
  fontSize: 12, color: MUTED, fontFace: "Calibri", align: "center"
});

pres.writeFile({ fileName: "/mnt/user-data/outputs/SovereignBody_NBL_Presentation.pptx" })
  .then(() => console.log("DONE — NBL Presentation created!"));
