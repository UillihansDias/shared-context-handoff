# Shared Context Handoff

- **Transition:** `<CURRENT_STAGE -> NEXT_STAGE>`
- **Status:** `<READY | BLOCKED | FAILED | SHIPPED | VERIFIED>`

## Goal

- **Objective:** `<specific measurable outcome>`
- **Target artefacts:**
  - `<exact file, endpoint, service, resource, or deliverable>`

## Constraints

- **Must not change:** `<negative scope and protected areas, or None>`
- **Limits:** `<architecture, dependencies, performance, security, operations, or other hard limits, or None>`

## Verifiers

### Pre-ship

- **Check:** `<exact command, test, or assertion; if unknown, state Missing and block validation>`
  - **Expected:** `<observable passing result>`
  - **Result:** `<PASS | FAIL | BLOCKED | SKIPPED | NOT RUN — evidence or reason>`

### Post-ship

- **Check:** `<metric, log query, probe, health check, or Not applicable — reason>`
  - **Expected:** `<threshold or observable healthy state>`
  - **Result:** `<PASS | FAIL | BLOCKED | SKIPPED | NOT RUN — evidence or reason>`

## Evidence and Routing

- **Evidence:** `<source-backed facts, artefact state, and concise relevant failure output, or None>`
- **Assumptions:** `<bounded assumptions, or None>`
- **Blocker:** `<conflict or missing decision, or None>`
- **Next owner/stage:** `<responsible role or lifecycle stage>`
- **Next action:** `<single concrete action>`
