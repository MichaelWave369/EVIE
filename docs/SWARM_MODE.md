# EVIE Swarm Mode (TIEKAT-style)

Swarm Mode adds a lightweight **director layer** on top of EVIE.
It is built to **plan → run → audit** using the same run history and safety guardrails
as the regular module engine.

## What Swarm Mode adds

### 1) Director planning
`POST /v1/swarm/plan`

Input:
```json
{"goal":"Build a YouTube flywheel","topic":"Career Sanctuary","constraints":{}}
```

Output:
- `plan_id` (stored as a run of type `swarm_plan`)
- `session_id` (optional, for agent memory + evidence)
- a `plan` object (workflow name + confidence)

Director backends:
- **heuristic** (default): deterministic keyword routing
- **ollama**: uses your local Ollama chat model to select a workflow (best-effort; falls back to heuristic)

Configure via `.env`:
```
EV_SWARM_DIRECTOR_BACKEND=heuristic
# or:
EV_SWARM_DIRECTOR_BACKEND=ollama
EV_LLM_BACKEND=ollama
EV_OLLAMA_CHAT_MODEL=llama3.1
```

### 2) Plan execution
`POST /v1/swarm/run`

If you provide a `plan_id`, Swarm Mode loads the stored plan and executes its workflow.

```json
{"plan_id": 123}
```

It returns a normal EVIE `run_id` with step-by-step logs.

### 3) Audit
`POST /v1/swarm/audit`

```json
{"run_id": 456}
```

Audit summarizes:
- step success/failure
- artifact validation status
- code gate status (best-effort sandbox scan)

### 4) Agent memory (local-only)
Each session can store minimal notes/state per agent:
- `GET /v1/swarm/sessions/{session_id}/agents/{agent}`
- `POST /v1/swarm/sessions/{session_id}/agents/{agent}/note`

Memory lives at: `data/agent_memory/<session_id>/<agent>.json`

## Suggested workflow recipes
Update `configs/workflows.json` to add your own multi-module recipes.

Example: add a “YouTube + Newsletter + Offer” workflow that runs in a single click.
