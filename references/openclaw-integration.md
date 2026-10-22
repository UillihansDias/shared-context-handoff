# OpenClaw integration and local CLI

## Skill install

Place the directory `shared-context-handoff/` under the agent workspace's `skills/` folder, or under the user's `~/.openclaw/skills/` folder. OpenClaw should then discover `SKILL.md` on the next skill refresh/session. No publishing or registry dependency is required.

The JSON Schema in `assets/handoff.schema.json` documents the data contract for external adapters. Schema validation alone does not enforce route guards or evidence gates; use the CLI or equivalent orchestration logic.

Runtime source-of-truth: an existing external Shared Context service takes precedence when configured. The included Python CLI is a **local file-backed reference adapter**, not an OpenClaw core subsystem or multi-agent transaction service. All commands below run with Python 3.9+; paths are examples for a single trusted workspace.

## State initialization and commands

1. Copy `assets/handoff-template.json` into a task-owned file; fill every mandatory value with actual task information. For each new stage transition, use the same contract format with the correct `current_stage` and `next_stage`.
2. Select a local state file outside version control, for example `.shared-context/task-001.json`. It contains raw verifier output; restrict access and do not commit it.
3. Initialize with:

```bash
python3 scripts/handoff.py init --state .shared-context/task-001.json --handoff ./task-handoff.json
python3 scripts/handoff.py status --state .shared-context/task-001.json
```

4. After TRIAGE, PLAN, or EXECUTE changes, update the handoff file and transition explicitly:

```bash
python3 scripts/handoff.py transition --state .shared-context/task-001.json --handoff ./task-handoff.json
```

5. At VALIDATE, run the **exact pre-ship commands** supplied by the task. Each verifier is a literal argument array; no shell interpolation or arbitrary ad-hoc replacement occurs:

```bash
python3 scripts/handoff.py run-pre --state .shared-context/task-001.json
python3 scripts/handoff.py status --state .shared-context/task-001.json
```

6. Once live monitoring has actually been performed, save the observed evidence in a local file and attach it by verifier `id`. Recording evidence is a manual, attributable assertion, not automatic monitoring:

```bash
python3 scripts/handoff.py record-post --state .shared-context/task-001.json --id banner-health --passed --source application-logs --evidence-file ./health-observation.txt
```

7. After MONITOR passes, extract the reusable triplet as a separate candidate template:

```bash
python3 scripts/handoff.py extract-template --state .shared-context/task-001.json --output ./verified-template.json
```

Other commands: `validate --state ...` checks stored structure and audit shape; `status --state ...` shows stage, status, and verifier summary.

## Hook: optional bootstrap reminder

The hook is **not automatically installed or enabled** with the skill. To opt into a short per-session reminder, copy the `hooks/openclaw` files into the OpenClaw hooks directory as a named hook and enable it using the host's supported `openclaw hooks` management commands. Check runtime compatibility before enabling; the included TypeScript uses the documented `agent:bootstrap` event and injects a virtual bootstrap file on primary sessions only.

- `hooks/openclaw/HOOK.md`: discovery metadata and behaviour.
- `hooks/openclaw/handler.ts`: bootstrap reminder implementation.

The hook never touches the state file, executes verifiers, records monitor evidence, or ships artifacts. Those operations remain explicit actions of the agent/CLI or external integrated orchestrator. Use it only if a bootstrap reminder is desirable for the OpenClaw agent where it is enabled.

## Operational limitations

- No installation to an actual OpenClaw instance is attempted by this archive.
- Local JSON state is not safe for concurrent independent writers; use a shared transactional state backend where concurrency matters.
- The CLI's pre-ship execution is opt-in and runs task-specified commands with the current user's permissions. Read and approve commands before use.
- Production monitoring is not supplied: provide real telemetry through an existing tool/service and record observations explicitly.
- Do not use the hook as proof of lifecycle enforcement. It is a reminder, not a security boundary or stage gate.
