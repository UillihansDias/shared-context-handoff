# Examples and edge cases

These examples are invented to demonstrate the protocol; they are not the user's actual project, metrics, or existing verifiers.

## Example A: scoped code change

Incoming signal: “Add a warning banner to the local checkout page without modifying the pricing model.”

Populate `assets/handoff-template.json`:

```json
{
  "current_stage": "SIGNAL",
  "next_stage": "TRIAGE",
  "goal": {"objective": "Show a warning banner on checkout when test fixture flag is true", "target_artifacts": ["web/checkout/banner.tsx"]},
  "constraints": {"negative_scope": ["Do not change pricing model or payments API"], "limits": ["No new dependencies"]},
  "verifiers": {
    "pre_ship": [{"id": "unit", "argv": ["npm", "test", "--", "checkout-banner"], "cwd": ".", "timeout_seconds": 300}],
    "post_ship": [{"id": "banner-health", "observable": "Checkout banner render errors in application logs", "success_condition": "No new banner render errors during the agreed observation window"}]
  }
}
```

Expected: TRIAGE and PLAN return handoffs only; EXECUTE edits the named path; VALIDATE runs the exact npm test; production evidence is collected only after shipping. The sample npm target is illustrative and must be confirmed before use.

## Example B: blocked architecture

A new requirement calls for changing the payments schema, but the handoff's negative scope prohibits schema changes. In EXECUTE, do not change it. Record `BLOCKED` with the schema conflict and transition to PLAN for a revised, authorized contract.

## Example C: pre-ship failure

The configured command exits 1. `run-pre` stores the exit code and raw stdout/stderr. `VALIDATE → SHIP` must fail; `VALIDATE → EXECUTE` remains allowed. Repair only the affected target, then rerun all current checks before shipping.

## Example D: unverifiable production health

Unit checks pass and an artifact is shipped, but the deployment has no accessible health logs. Remain in MONITOR. Do not advance to AUTOMATE or extract a supposedly successful template.

## Do not invoke

| Request | Reason |
| --- | --- |
| “Explain what a YAML file is.” | No staged task or Shared Context handoff |
| “Summarize this paragraph.” | No staged operational lifecycle |
