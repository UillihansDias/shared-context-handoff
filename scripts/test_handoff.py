#!/usr/bin/env python3
"""Regression suite for the local Shared Context file adapter."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import handoff as h


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.state = self.base / "state.json"
        self.handoff_file = self.base / "handoff.json"
        self.contract = {
            "current_stage": "SIGNAL", "next_stage": "TRIAGE",
            "goal": {"objective": "Create example output", "target_artifacts": ["out.txt"]},
            "constraints": {"negative_scope": ["Do not touch unrelated files"], "limits": ["Standard library only"]},
            "verifiers": {
                "pre_ship": [{"id": "test", "argv": ["python3", "-c", "print('ok')"], "timeout_seconds": 30}],
                "post_ship": [{"id": "health", "observable": "Application error logs", "success_condition": "Zero errors"}],
            },
        }
        self.write_contract()

    def write_contract(self):
        self.handoff_file.write_text(json.dumps(self.contract), encoding="utf-8")

    def run_cli(self, *args):
        return h.main(list(args))

    def advance(self, new, *args):
        prev = self.contract["next_stage"]
        self.contract["current_stage"] = prev
        self.contract["next_stage"] = new
        self.write_contract()
        return self.run_cli("transition", "--state", str(self.state), "--handoff", str(self.handoff_file), *args)

    def enter_validate(self):
        self.assertEqual(0, self.run_cli("init", "--state", str(self.state), "--handoff", str(self.handoff_file)))
        for stage in ("PLAN", "EXECUTE", "VALIDATE"):
            self.assertEqual(0, self.advance(stage))

    def test_missing_required_triplet_stops(self):
        bad = copy.deepcopy(self.contract)
        bad["constraints"]["negative_scope"] = []
        with self.assertRaises(h.ContractError):
            h.validate_contract(bad)
        bad = copy.deepcopy(self.contract)
        bad["verifiers"]["post_ship"] = []
        with self.assertRaises(h.ContractError):
            h.validate_contract(bad)

    def test_validation_gate_and_monitor_gate(self):
        self.enter_validate()
        self.assertEqual(2, self.advance("SHIP"))
        self.contract["next_stage"] = "VALIDATE"  # failed transition did not advance
        self.write_contract()
        self.assertEqual(0, self.run_cli("run-pre", "--state", str(self.state)))
        self.assertEqual(0, self.advance("SHIP"))
        evidence = self.base / "ship.txt"
        evidence.write_text("Release identifier: example-1", encoding="utf-8")
        self.assertEqual(0, self.advance("MONITOR", "--ship-evidence-file", str(evidence)))
        self.assertEqual(2, self.advance("AUTOMATE"))
        self.contract["next_stage"] = "MONITOR"
        self.write_contract()
        monitor = self.base / "health.txt"
        monitor.write_text("Observed zero errors in example monitor", encoding="utf-8")
        self.assertEqual(0, self.run_cli("record-post", "--state", str(self.state), "--id", "health", "--passed",
                                          "--source", "example monitor", "--evidence-file", str(monitor)))
        self.assertEqual(0, self.advance("AUTOMATE"))
        self.assertEqual(0, self.run_cli("extract-template", "--state", str(self.state), "--output", str(self.base / "candidate.json")))
        self.assertIn("goal", json.loads((self.base / "candidate.json").read_text()))

    def test_raw_error_captured_and_ship_denied(self):
        self.contract["verifiers"]["pre_ship"][0]["argv"] = ["python3", "-c", "import sys; sys.stderr.write('FAIL-RAW\\n'); sys.exit(3)"]
        self.write_contract()
        self.enter_validate()
        self.assertEqual(2, self.run_cli("run-pre", "--state", str(self.state)))
        state = h.load_state(self.state)
        self.assertEqual(3, state["pre_results"][0]["exit_code"])
        self.assertIn("FAIL-RAW", state["pre_results"][0]["stderr"])
        self.assertEqual(2, self.advance("SHIP"))
        self.contract["next_stage"] = "VALIDATE"
        self.assertEqual(0, self.advance("EXECUTE"))

    def test_execute_blocked_requires_reason(self):
        self.assertEqual(0, self.run_cli("init", "--state", str(self.state), "--handoff", str(self.handoff_file)))
        self.assertEqual(0, self.advance("PLAN"))
        self.assertEqual(0, self.advance("EXECUTE"))
        self.assertEqual(2, self.advance("PLAN"))
        self.contract["next_stage"] = "EXECUTE"
        self.assertEqual(0, self.advance("PLAN", "--blocked-reason", "Schema change forbidden"))
        self.assertEqual("BLOCKED", h.load_state(self.state)["status"])
        self.assertEqual(0, self.advance("EXECUTE"))
        self.assertEqual("ACTIVE", h.load_state(self.state)["status"])

    def test_change_after_plan_rejected(self):
        self.enter_validate()
        self.contract["goal"]["objective"] = "Unauthorized new target"
        self.assertEqual(2, self.advance("SHIP"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
