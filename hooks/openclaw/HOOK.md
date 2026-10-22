---
name: shared-context-handoff
description: "Inject a concise Goals/Constraints/Verifiers reminder into primary agent bootstrap."
metadata: {"openclaw":{"events":["agent:bootstrap"]}}
---

# Shared Context Handoff Reminder

On `agent:bootstrap`, `handler.ts` injects a virtual, idempotent instruction reminder for the primary agent. It skips sub-agents and respects an existing different file with the same path. This hook neither creates Shared Context nor enforces stage gates by itself. Enable only when bootstrap injection is wanted; the skill otherwise works without hooks.
