#!/usr/bin/env python3
"""File-backed Shared Context handoff adapter; Python 3.9+ standard library."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

STAGES = ("SIGNAL", "TRIAGE", "PLAN", "EXECUTE", "VALIDATE", "SHIP", "MONITOR", "AUTOMATE")
ROUTES = {
    "SIGNAL": {"TRIAGE"},
    "TRIAGE": {"PLAN"},
    "PLAN": {"EXECUTE"},
    "EXECUTE": {"VALIDATE", "PLAN"},
    "VALIDATE": {"SHIP", "EXECUTE", "PLAN"},
    "SHIP": {"MONITOR"},
    "MONITOR": {"AUTOMATE"},
    "AUTOMATE": {"SIGNAL"},
}


class ContractError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fail(message):
    raise ContractError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(items, field):
    if not isinstance(items, list) or not items or not all(nonempty(x) for x in items):
        fail(f"{field} must be a nonempty list of nonblank strings")


def require_mapping(value, name):
    if not isinstance(value, dict):
        fail(f"{name} must be an object")
    return value


def contract_digest(contract):
    material = {k: contract[k] for k in ("goal", "constraints", "verifiers")}
    raw = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_contract(contract):
    c = require_mapping(contract, "handoff")
    old = c.get("current_stage")
    new = c.get("next_stage")
    if old not in STAGES or new not in STAGES:
        fail("current_stage and next_stage must be named lifecycle stages")
    if new not in ROUTES[old]:
        fail(f"disallowed transition: {old} -> {new}")
    goal = require_mapping(c.get("goal"), "goal")
    if not nonempty(goal.get("objective")):
        fail("goal.objective must be specific and nonblank")
    string_list(goal.get("target_artifacts"), "goal.target_artifacts")
    constraints = require_mapping(c.get("constraints"), "constraints")
    string_list(constraints.get("negative_scope"), "constraints.negative_scope")
    string_list(constraints.get("limits"), "constraints.limits")
    verifiers = require_mapping(c.get("verifiers"), "verifiers")
    pre = verifiers.get("pre_ship")
    post = verifiers.get("post_ship")
    if not isinstance(pre, list) or not pre:
        fail("verifiers.pre_ship requires at least one actual check")
    if not isinstance(post, list) or not post:
        fail("verifiers.post_ship requires at least one observable check")
    for name, items in (("pre_ship", pre), ("post_ship", post)):
        ids = []
        for item in items:
            require_mapping(item, f"verifiers.{name} entry")
            if not nonempty(item.get("id")):
                fail(f"verifiers.{name} entry needs a nonblank id")
            ids.append(item["id"])
        if len(ids) != len(set(ids)):
            fail(f"verifiers.{name} ids must be unique")
    for check in pre:
        argv = check.get("argv")
        if not isinstance(argv, list) or not argv or not all(nonempty(arg) for arg in argv):
            fail(f"pre_ship {check['id']}: argv must contain literal, nonblank arguments")
        if "cwd" in check and (not isinstance(check["cwd"], str) or not check["cwd"].strip()):
            fail(f"pre_ship {check['id']}: cwd must be a nonblank directory if supplied")
        timeout = check.get("timeout_seconds", 300)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not (0 < timeout <= 3600):
            fail(f"pre_ship {check['id']}: timeout_seconds must be in (0, 3600]")
    for check in post:
        if not nonempty(check.get("observable")) or not nonempty(check.get("success_condition")):
            fail(f"post_ship {check['id']}: observable and success_condition required")
    return c


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"unable to read JSON {path}: {exc}")


def load_state(path):
    data = require_mapping(load_json(path), "state")
    if data.get("format_version") != 1 or data.get("stage") not in STAGES:
        fail("state format/version/stage invalid")
    if data.get("status") not in ("ACTIVE", "BLOCKED"):
        fail("state status invalid")
    if not isinstance(data.get("history"), list):
        fail("state history missing")
    for key in ("pre_results", "post_results"):
        if not isinstance(data.get(key), list):
            fail(f"state {key} missing")
    validate_contract(data.get("handoff"))
    if data.get("stage") != data["handoff"]["next_stage"]:
        fail("state stage does not match most recent handoff destination")
    return data


def atomic_json(path, obj, exclusive=False):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and target.exists():
        fail(f"state already exists: {target}")
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".handoff-", suffix=".tmp")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive and target.exists():
            fail(f"state already exists: {target}")
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def evidence_matches(state, kind):
    entries = state["handoff"]["verifiers"][kind]
    results = state["pre_results" if kind == "pre_ship" else "post_results"]
    digest = contract_digest(state["handoff"])
    current = {}
    for result in results:
        if result.get("contract_digest") == digest:
            current[result.get("id")] = result
    return all(current.get(entry["id"], {}).get("passed") is True for entry in entries)


def command_init(args):
    handoff = validate_contract(load_json(args.handoff))
    if (handoff["current_stage"], handoff["next_stage"]) != ("SIGNAL", "TRIAGE"):
        fail("init requires SIGNAL -> TRIAGE")
    state = {
        "format_version": 1,
        "stage": "TRIAGE",
        "status": "ACTIVE",
        "blocked_reason": None,
        "handoff": handoff,
        "pre_results": [],
        "post_results": [],
        "ship_evidence": None,
        "history": [{"at": now(), "event": "init", "from": "SIGNAL", "to": "TRIAGE", "handoff": copy.deepcopy(handoff)}],
    }
    atomic_json(args.state, state, exclusive=True)
    print("INITIALIZED SIGNAL -> TRIAGE")


def command_transition(args):
    state = load_state(args.state)
    handoff = validate_contract(load_json(args.handoff))
    old, new = handoff["current_stage"], handoff["next_stage"]
    if old != state["stage"]:
        fail(f"expected current_stage {state['stage']}, got {old}")
    if state["status"] == "BLOCKED" and old != "PLAN":
        fail("blocked state can only resume from PLAN")
    if old == "EXECUTE" and new == "PLAN" and not nonempty(args.blocked_reason):
        fail("EXECUTE -> PLAN requires --blocked-reason")
    if args.blocked_reason and (old, new) != ("EXECUTE", "PLAN"):
        fail("--blocked-reason only applies to EXECUTE -> PLAN")
    if old not in ("TRIAGE", "PLAN", "AUTOMATE") and contract_digest(handoff) != contract_digest(state["handoff"]):
        fail("triplet changed outside TRIAGE/PLAN; return to PLAN before revising it")
    if old == "VALIDATE" and new == "SHIP" and not evidence_matches(state, "pre_ship"):
        fail("VALIDATE -> SHIP denied: not all current pre-ship verifiers passed")
    if old == "MONITOR" and new == "AUTOMATE" and not evidence_matches(state, "post_ship"):
        fail("MONITOR -> AUTOMATE denied: missing/failed post-ship evidence")
    if old == "SHIP" and new == "MONITOR":
        if not args.ship_evidence_file:
            fail("SHIP -> MONITOR requires --ship-evidence-file proving completed shipping")
        ship_proof = Path(args.ship_evidence_file).read_text(encoding="utf-8")
        if not ship_proof.strip():
            fail("ship evidence cannot be blank")
        state["ship_evidence"] = {"at": now(), "source_file": str(args.ship_evidence_file), "content": ship_proof}
    elif args.ship_evidence_file:
        fail("--ship-evidence-file only valid for SHIP -> MONITOR")
    prior = contract_digest(state["handoff"])
    current = contract_digest(handoff)
    if prior != current or new == "SIGNAL":
        state["pre_results"] = []
        state["post_results"] = []
        state["ship_evidence"] = None
    state["handoff"] = handoff
    state["stage"] = new
    state["status"] = "BLOCKED" if args.blocked_reason else "ACTIVE"
    state["blocked_reason"] = args.blocked_reason or None
    state["history"].append({"at": now(), "event": "transition", "from": old, "to": new,
                             "status": state["status"], "reason": args.blocked_reason, "handoff": copy.deepcopy(handoff)})
    atomic_json(args.state, state)
    print(f"{old} -> {new} [{state['status']}]")


def command_run_pre(args):
    state = load_state(args.state)
    if state["stage"] != "VALIDATE" or state["status"] != "ACTIVE":
        fail("run-pre requires active VALIDATE stage")
    digest = contract_digest(state["handoff"])
    state["pre_results"] = [r for r in state["pre_results"] if r.get("contract_digest") != digest]
    all_pass = True
    for item in state["handoff"]["verifiers"]["pre_ship"]:
        argv = item["argv"]
        cwd = item.get("cwd") or None
        try:
            run = subprocess.run(argv, cwd=cwd, shell=False, capture_output=True, text=True,
                                 errors="replace", timeout=item.get("timeout_seconds", 300), check=False)
            returncode, stdout, stderr = run.returncode, run.stdout, run.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            returncode, stdout, stderr = -1, "", str(exc)
            if isinstance(exc, subprocess.TimeoutExpired):
                raw_out, raw_err = exc.stdout, exc.stderr
                stdout = raw_out.decode(errors="replace") if isinstance(raw_out, bytes) else (raw_out or "")
                stderr = (raw_err.decode(errors="replace") if isinstance(raw_err, bytes) else (raw_err or "")) + "\n" + str(exc)
        passed = returncode == 0
        all_pass = all_pass and passed
        result = {"at": now(), "id": item["id"], "passed": passed, "argv": argv, "cwd": cwd,
                  "exit_code": returncode, "stdout": stdout, "stderr": stderr, "contract_digest": digest}
        state["pre_results"].append(result)
        state["history"].append({"at": result["at"], "event": "pre_verifier", "id": item["id"],
                                 "passed": passed, "exit_code": returncode,
                                 "raw_stdout": stdout, "raw_stderr": stderr})
        print(f"{item['id']}: {'PASS' if passed else 'FAIL'} (exit {returncode})")
    atomic_json(args.state, state)
    if not all_pass:
        fail("one or more pre-ship verifiers failed; do not ship; route back to EXECUTE or PLAN")


def command_record_post(args):
    state = load_state(args.state)
    if state["stage"] != "MONITOR" or state["status"] != "ACTIVE":
        fail("record-post requires active MONITOR stage")
    if args.id not in {v["id"] for v in state["handoff"]["verifiers"]["post_ship"]}:
        fail(f"unknown post-ship verifier id: {args.id}")
    if not nonempty(args.source):
        fail("an attributable --source for live observation is required")
    evidence = Path(args.evidence_file).read_text(encoding="utf-8")
    if not evidence.strip():
        fail("post-ship observation evidence cannot be blank")
    passed = args.passed
    entry = {"at": now(), "id": args.id, "passed": passed, "source": args.source,
             "evidence_file": str(args.evidence_file), "evidence": evidence,
             "attestation": "operator-supplied observation (not independently checked by CLI)",
             "contract_digest": contract_digest(state["handoff"])}
    state["post_results"].append(entry)
    state["history"].append({"at": entry["at"], "event": "post_verifier", "id": args.id,
                             "passed": passed, "source": args.source, "evidence": evidence})
    atomic_json(args.state, state)
    print(f"{args.id}: {'PASS' if passed else 'FAIL'} (operator-attested)")


def command_extract(args):
    state = load_state(args.state)
    if state["stage"] != "AUTOMATE" or not evidence_matches(state, "post_ship"):
        fail("template extraction requires successful MONITOR -> AUTOMATE")
    template = {k: copy.deepcopy(state["handoff"][k]) for k in ("goal", "constraints", "verifiers")}
    output = Path(args.output)
    if output.resolve() == Path(args.state).resolve():
        fail("output cannot overwrite Shared Context state")
    atomic_json(output, template, exclusive=True)
    print(f"CANDIDATE TEMPLATE {output}")


def command_status(args):
    state = load_state(args.state)
    report = {"stage": state["stage"], "status": state["status"], "blocked_reason": state["blocked_reason"],
              "last_transition": {"from": state["handoff"]["current_stage"], "to": state["handoff"]["next_stage"]},
              "pre_ship_all_passed": evidence_matches(state, "pre_ship"),
              "post_ship_all_passed": evidence_matches(state, "post_ship"),
              "history_events": len(state["history"])}
    print(json.dumps(report, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    def make(name, purpose):
        item = sub.add_parser(name, help=purpose)
        item.add_argument("--state", required=True, help="local Shared Context JSON file")
        return item
    p = make("init", "create state from SIGNAL -> TRIAGE")
    p.add_argument("--handoff", required=True)
    p.set_defaults(func=command_init)
    p = make("transition", "validate and persist one allowed transition")
    p.add_argument("--handoff", required=True)
    p.add_argument("--blocked-reason")
    p.add_argument("--ship-evidence-file")
    p.set_defaults(func=command_transition)
    make("run-pre", "execute all declared pre-ship verifiers").set_defaults(func=command_run_pre)
    p = make("record-post", "record attributable post-ship observation")
    p.add_argument("--id", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--passed", action="store_true")
    group.add_argument("--failed", action="store_true")
    p.add_argument("--source", required=True)
    p.add_argument("--evidence-file", required=True)
    p.set_defaults(func=command_record_post)
    p = make("extract-template", "write reusable triplet after verified monitoring")
    p.add_argument("--output", required=True)
    p.set_defaults(func=command_extract)
    make("validate", "validate stored state").set_defaults(func=lambda a: (load_state(a.state), print("STATE VALID")))
    make("status", "display concise state without raw logs").set_defaults(func=command_status)
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
