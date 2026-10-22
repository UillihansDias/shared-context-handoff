# shared-context-handoff

Enforce Goals, Constraints, and Verifiers handoffs across a disciplined, staged Signal-to-Automate lifecycle:

```text
SIGNAL → TRIAGE → PLAN → EXECUTE → VALIDATE → SHIP → MONITOR → AUTOMATE → SIGNAL
```

`shared-context-handoff` eliminates vague, unvalidated agent handoffs by requiring structured contracts (`CURRENT_STAGE → NEXT_STAGE`, `GOAL`, `CONSTRAINTS`, `VERIFIERS`) before transitions can occur. Free-form prose is never accepted as a substitute for an executable handoff contract.

## Main File

- `SKILL.md`

## Structure

```text
.
├── SKILL.md                         # Canonical skill specification and lifecycle invariants
├── README.md                        # Package documentation and CLI reference
├── assets/
│   ├── handoff-template.json        # Machine-readable JSON contract template
│   ├── handoff-template.md          # Human-readable Markdown handoff template
│   └── handoff.schema.json          # JSON Schema for external orchestration adapters
├── hooks/
│   └── openclaw/
│       ├── HOOK.md                  # Bootstrap hook metadata
│       └── handler.ts               # Optional OpenClaw bootstrap reminder handler
├── references/
│   ├── examples.md                  # Worked handoff examples and edge cases
│   ├── openclaw-integration.md      # Setup guide for OpenClaw workspace and CLI workflow
│   └── stage-playbook.md            # Stage-by-stage permissions, transitions, and rules
└── scripts/
    ├── handoff.py                   # Reference CLI for state management and verifier execution
    └── test_handoff.py              # Regression tests for stage gates and verification
```

## Core Invariants

1. **The Required Triplet**: Every transition must provide measurable `goal.objective` and `goal.target_artifacts`, explicit `constraints.negative_scope` and `constraints.limits`, executable `verifiers.pre_ship`, and observable `verifiers.post_ship`.
2. **Phase Separation**:
   - `TRIAGE` and `PLAN`: Focus exclusively on specifying and scoping the contract; no target code changes permitted.
   - `EXECUTE`: Modify only declared target artifacts within constraints. If blocked, log `BLOCKED` with an explicit reason and transition back to `PLAN`.
   - `VALIDATE`: Run literal pre-ship verifiers. All must pass with exit code `0` before advancing to `SHIP`.
   - `SHIP`: Advance only with passing pre-ship checks and appropriate operational authority.
   - `MONITOR`: Verify post-ship indicators with authentic runtime evidence before advancing to `AUTOMATE`.
3. **No Silent Cascades**: Never carry stale verification evidence forward to a new goal or signal.

## CLI Usage

The repository includes a Python reference CLI (`scripts/handoff.py`, requiring Python 3.9+) to manage state transitions and gate enforcement locally.

### 1. Initialize State

Copy `assets/handoff-template.json` to your task workspace, populate the initial values, and initialize:

```bash
python3 scripts/handoff.py init --state .shared-context/task-001.json --handoff ./task-handoff.json
python3 scripts/handoff.py status --state .shared-context/task-001.json
```

### 2. Transition Across Stages

When transitioning (e.g., `TRIAGE → PLAN` or `PLAN → EXECUTE`), update the handoff payload and advance:

```bash
python3 scripts/handoff.py transition --state .shared-context/task-001.json --handoff ./task-handoff.json
```

If execution is blocked, transition back to `PLAN` with a reason:

```bash
python3 scripts/handoff.py transition --state .shared-context/task-001.json --handoff ./task-handoff.json --blocked-reason "Dependency XYZ unavailable in sandbox"
```

### 3. Run Pre-Ship Verifiers

At `VALIDATE`, execute the pre-ship verification array:

```bash
python3 scripts/handoff.py run-pre --state .shared-context/task-001.json
```

### 4. Record Post-Ship Health & Automate

Record observed telemetry and runtime evidence for post-ship verifiers:

```bash
python3 scripts/handoff.py record-post \
  --state .shared-context/task-001.json \
  --id banner-health \
  --passed \
  --source application-logs \
  --evidence-file ./health-observation.txt
```

Extract the verified triplet into a reusable candidate template:

```bash
python3 scripts/handoff.py extract-template \
  --state .shared-context/task-001.json \
  --output ./verified-template.json
```

## Running Tests

Run the test suite to verify state gates, transition validation, and raw error capturing:

```bash
python3 scripts/test_handoff.py
```

## Installation in OpenClaw

Place the directory under your agent workspace's `skills/` directory or `~/.openclaw/skills/`:

```bash
openclaw skills install ./shared-context-handoff --as shared-context-handoff
```
