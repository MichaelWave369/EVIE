# EVIE R14 · Nine Hook Content Workshop (one supervised local content module)

## What R14 actually revives
EVIE adds an 11th configured workflow, `local_content_hooks_review`, containing exactly one existing registered module: `hooks_generator`. The supervised CLI invokes the **real** `app.modules_v2.hooks_generator.HooksGenerator.generate` implementation, bypassing the general-purpose adapter's implicit output location in favor of a disposable temp directory. This is template-based content generation, not an LLM; no model provider is contacted.

## Run it on your own Windows, Linux or macOS machine
Create a UTF-8 file named `draft.txt` containing 20–8192 bytes of your own notes or script, then run from a **trusted** local EVIE repository clone:

    python -m tools.evie_supervised_hooks local_content_hooks_review --script-file ./draft.txt --topic "EVIE Creator Loop" --stage-dir ../evie-hooks-review-001 --confirm-local-execution

Use a new stage directory each time, outside your public Git checkout. Topic is limited to 1–80 alphanumeric / space / underscore / dash characters; a local script filename must refer to a regular non-symlink file. The module extracts bounded lines and composes 9 editable draft hooks split into **educational, controversial/provocative and curiosity** groups. These are NOT fact-checked advertising claims.

## Controls
- Exact allowlist: only the one-step `local_content_hooks_review` source workflow, pointing at `hooks_generator`; workflow spec drift refuses the run.
- CLI requires an explicit `--confirm-local-execution`. No GUI or agent remotely triggers execution.
- The child receives script bytes by stdin, not an argument. It has a 20-second timeout, a disposable working folder, minimal environment and no forwarded provider credentials. It uses Python -I. This **is not OS or network sandboxing**.
- The child uses the original HooksGenerator but sets `output_dir` to a temporary folder. The parent independently checks SHA-256 of the actual JSON, matching script digest, 9 hook strings and 3 exact category slices before staging.
- Before and after the subprocess, the launcher compares workflow, wrapper, generator and worker source SHA-256. It rejects source drift.
- 32 KB content artifact bound, 100 KB review bundle bound. An existing stage directory is never overwritten; staging failures clean up only the new directory.
- No LLM, publisher, database, legacy runner, network dispatch, hosted API, or arbitrary module execution is invoked by the runner. It does not authenticate the operator or approve content.

## Output files
Four local files are staged only after success:
- `nine-hooks.json`: actual original HooksGenerator output, containing nine strings and grouped categories.
- `nine-hooks-review.md`: text-format review sheet derived from verified JSON and escaped as Markdown.
- `workflow-preflight.json`: R12 source-only plan, still correctly marked executed=false; it is not runtime evidence.
- `review-receipt.json`: unsigned local execution observation `evie.supervised-hooks-review/1` containing source hashes, script/content/review hashes and explicit default-deny governance.

## Public React inspection
Go to Mission Control → Workflow Studio → Local Content Hooks Review → Nine-Hook Content Workshop. This static page only gives a copyable CLI example and lets you select the staged receipt and JSON (plus original script optionally). The browser checks exact content SHA-256, the published source revision and output shape, and optionally the input SHA-256. Nothing is uploaded or published. A matching **unsigned** file pair is not independent proof that the source really executed.

## Boundaries and next step
Unlike the configured `youtube_flywheel` and other pipelines, this is **one real existing content module**, not a restored end-to-end AI content production system. We deliberately did not infer safe execution from the other modules' registry entries. Editing, substantiation and human permission are required before distribution. Future milestones should inspect a second deterministic content module or add stronger, authenticated execution receipts with OS isolation before attempting multi-step workflows.

## Tests
`pytest -q tests/test_supervised_hooks.py` and `cd web && npm test && npm run build`. Both belong to EVIE's existing Python release gate and React Pages workflows.
