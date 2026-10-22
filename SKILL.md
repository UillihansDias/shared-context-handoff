---
name: shared-context-handoff
description: "Enforce Goals/Constraints/Verifiers handoffs in a staged Signal-to-Automate workflow. Use for task intake, stage transitions, execution boundaries, validation gates, blocked returns, monitoring and reusable runbooks. Not for unrelated one-off answers."
---

# Shared Context Handoff

## Objective

Coordinate `SIGNAL → TRIAGE → PLAN → EXECUTE → VALIDATE → SHIP → MONITOR → AUTOMATE → SIGNAL` through an explicit, persisted Shared Context. A handoff always supplies `CURRENT_STAGE → NEXT_STAGE`, `GOAL`, `CONSTRAINTS`, and `VERIFIERS`. Never pass free-form prose as a substitute for a transition payload.

This skill enforces agent behaviour; its optional local CLI additionally validates and stores state. It does not automatically enable tools, deploy work, acquire monitoring data, or run itself in the background.

## Inputs and hard boundaries

- On task receipt and before a transition, **read** current Shared Context. The host may provide an external store; otherwise use the local state CLI after explicit workspace selection.
- Every handoff must specify a measurable `goal.objective`, exact `goal.target_artifacts`, `constraints.negative_scope`, `constraints.limits`, executable or deterministic `verifiers.pre_ship` and observable `verifiers.post_ship`. Empty or ambiguous triplets must not advance.
- Do not invent targets, restrictions, commands, monitoring thresholds, or evidence. If a required value is genuinely unknown in TRIAGE or PLAN, halt and ask for that missing part.
- During TRIAGE and PLAN output only the completed handoff; do not implement or modify target code.
- During EXECUTE change only named target artifacts within constraints. If impossible, record `BLOCKED`, the conflict, and route to PLAN.
- Before destructive, remote, production, publishing, or irreversible effects, obtain authorization required by the host and task. A passing verifier is not authorization to ship.
- Do not store tokens, credentials, or confidential output in logs. The CLI preserves raw verifier stdout/stderr on failure to honour the source contract: review verifier commands and output paths before running them.

## Runtime workflow

1. **Receive:** Read the existing Shared Context (if any). Create a contract using `assets/handoff-template.json`; determine the current and next stage. On a fresh task, start `SIGNAL → TRIAGE`.
2. **Triage / Plan:** Resolve objective, target artifacts, negative scope, architecture/dependency limits, exact pre-ship checks, and real post-ship indicators. Stop for material gaps. Output the structured handoff only.
3. **Persist:** Write the completed handoff to Shared Context *before* transition. If using the local CLI, use `init` for the initial contract and `transition` for every later handoff. See `references/openclaw-integration.md` for commands and integration boundaries.
4. **Execute:** Perform only authorized work. If blocked, set `BLOCKED` and return to PLAN without changing adjacent artifacts. Do not mark completed work based on intention.
5. **Validate:** Run precisely the pre-ship verifiers specified in the contract. With local CLI use `run-pre`; it executes literal argument arrays without a shell and retains exit codes/raw output. On any failure, reject SHIP and return to EXECUTE, or PLAN for architectural failure. A successful `VALIDATE → SHIP` transition requires all matching checks to pass.
6. **Ship:** Advance only after all pre-ship checks pass and required shipping authorization is in place. Record the artifact/version or deployment reference in the surrounding handoff notes only when actually known.
7. **Monitor / Automate:** Observe production health via the declared post-ship verifiers; record authentic runtime evidence using `record-post`. Only then advance `MONITOR → AUTOMATE`, and extract the verified triplet for future signals. The local CLI does not fetch live telemetry automatically.
8. **Loop:** For a new independent signal, start a fresh state file or explicitly begin the next SIGNAL cycle; do not silently carry stale verifier evidence to new goals.

The stage-specific decision table, failure cases, and exact transition rules are in `references/stage-playbook.md`; read it when moving across stages, resolving a block, or handling a verification failure.

## Supporting resources

- `assets/handoff.schema.json` — use when validating handoffs in external orchestration adapters with a JSON Schema validator; the local CLI enforces equivalent checks plus stage-transition rules.
- `assets/handoff-template.json` — copy as the starting machine-readable handoff; replace empty values with actual scoped inputs before `init` or `transition`.
- `assets/handoff-template.md` — use when a human-readable Markdown handoff is needed instead of the machine-readable JSON contract.
- `references/stage-playbook.md` — read for stage permissions, valid transitions, failure routing, and audit requirements.
- `references/examples.md` — read when learning the contract, testing edge cases, or producing example handoffs; examples are illustrative, not asserted user tasks.
- `references/openclaw-integration.md` — read when setting up persistent local state, using CLI commands, or enabling the optional OpenClaw hook.
- `scripts/handoff.py` — use for local state initialization, contract validation, stage transitions, controlled pre-ship verifier execution, recording real post-ship evidence, and extracting successful templates. Requires Python 3.9+ (stdlib only).
- `scripts/test_handoff.py` — run when installing or modifying this skill to regression-test gates, raw failure logging, and template extraction.
- `hooks/openclaw/HOOK.md` and `hooks/openclaw/handler.ts` — optional bootstrap reminder: install and enable only if agent-wide bootstrap enforcement is desired. The hook does not implement state transitions; it only injects a small prompt reminder.

## Verification and output

Before returning a stage handoff, ensure all required fields are non-empty, stage names form an allowed route, no constraint is violated, and current storage reflects the transition. Before SHIP require 100% pre-ship verifier passes; before AUTOMATE require observed post-ship evidence for every declared monitor. Never claim runtime success from absence of errors.

Return a structured `CURRENT_STAGE → NEXT_STAGE` handoff with `GOAL`, `CONSTRAINTS`, and `VERIFIERS` (and `STATUS: BLOCKED` plus the concrete reason when applicable). For a validated transition, include supporting evidence identifiers and the persisted state location, without exposing secret-bearing log contents in chat. When state is inaccessible, explicitly mark the handoff as unpersisted and block transition rather than implying durability.
