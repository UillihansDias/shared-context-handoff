# Stage playbook

This reference expands the source handoff protocol. `SKILL.md` is the runtime orchestrator; this file is for stage or failure decisions, not for bootstrap loading.

## Contract

| Required field | Meaning | Rejection example |
| --- | --- | --- |
| `current_stage`, `next_stage` | Explicit handoff route | Missing source stage |
| `goal.objective` | Specific measurable outcome | “Improve the system” |
| `goal.target_artifacts[]` | Exact scoped paths/endpoints/resources | “Whatever needs changing” |
| `constraints.negative_scope[]` | What not to touch | Blank when boundaries unresolved |
| `constraints.limits[]` | Architecture, performance, dependencies | Unbounded refactor authority |
| `verifiers.pre_ship[]` | Stable commands/tests/assertions | “Looks good” |
| `verifiers.post_ship[]` | Observable runtime signals + pass criteria | “Monitor everything” |

A verifier object may have an executable `argv` array, `cwd`, and `timeout_seconds`. The local CLI currently supports only executable `argv` pre-ship tests. If a test is a deterministic non-command assertion, use an approved verifier runner that produces authentic evidence; do not misrepresent an unsupported assertion as an executed check. Post-ship checks require `id`, `observable`, and `success_condition` and *observed evidence*, not predictions.

## Valid routes

| From | To | Guard |
| --- | --- | --- |
| SIGNAL | TRIAGE | Complete incoming contract |
| TRIAGE | PLAN | Concrete goal, constraints, and verifiers |
| PLAN | EXECUTE | Scope accepted; no unresolved material ambiguity |
| EXECUTE | VALIDATE | Declared implementation finished within bounds |
| EXECUTE | PLAN | `BLOCKED`; hard constraint prevents execution |
| VALIDATE | SHIP | Every current pre-ship verifier passed, explicit authorization for side effects |
| VALIDATE | EXECUTE | Failed checks require correction |
| VALIDATE | PLAN | Failed checks reveal architecture/contract issue |
| SHIP | MONITOR | Actual shipping action completed with approvals |
| MONITOR | AUTOMATE | Every current post-ship verifier observed as passing |
| AUTOMATE | SIGNAL | Reuse previous triplet only as a new template, not as unexamined facts |

## Operational stage matrix

**TRIAGE and PLAN:** Read Shared Context, produce only the completed handoff contract. Do not implement. If a required component is ambiguous, stop and request clarification. A blocked state stays blocked until a new contract resolves it.

**EXECUTE:** Scope is a hard boundary. Do not perform opportunistic code cleanup, schema changes, new dependencies, or adjacent edits. If a conflict prevents delivery, capture the conflict, record `BLOCKED`, and route to PLAN.

**VALIDATE:** Test exactly what was committed in pre-ship verifiers. Log exit code and raw command output with provenance. A nonzero exit code rejects SHIP. Return to EXECUTE for implementation fixes or PLAN for contract/architecture fixes. A modified Goal, Constraints, or Pre-Ship verifier list invalidates earlier pre-ship evidence.

**SHIP:** State advancement is not a deployment engine. Only advance when shipping itself has been performed or explicitly authorized to be performed separately. Avoid interpreting a passed unit test as proof of a production release.

**MONITOR and AUTOMATE:** Require actual, attributable live evidence for all declared post-ship conditions before advancing. Extract the triplet only after success. Extraction creates a candidate template; recheck suitability for the next signal.

## Evidence and storage

The local CLI records transitions and verifier outcomes in one workspace-controlled JSON state file. Prefer an access-restricted location outside source control; protect against sensitive stdout/stderr. The history is an audit aid, not a tamper-proof record. If your environment already provides a transactional Shared Context service, adapt the same fields and transition logic to that service rather than maintaining divergent independent stores.

## Failure handling

- **Missing fields:** Do not guess. Keep the current stage and request the precise missing input.
- **Pre-ship command failure:** Preserve raw error output in Shared Context and route to EXECUTE; route to PLAN for architecture faults.
- **Post-ship signal missing:** Remain in MONITOR, and report that production success cannot be established.
- **State unavailable:** Do not claim to have persisted a handoff; halt the stage transition.
- **Concurrent writes:** The local CLI uses atomic replacement, not distributed locking. Coordinate writers externally or use a transactional shared store.
