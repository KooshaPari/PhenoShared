from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from pheno.evidence.atif import ATIF_SCHEMA_VERSION, validate_atif_integrity
from pheno.evidence.contracts import ContractError

try:
    from harbor.models.trajectories import Trajectory as HarborTrajectory
    from pydantic import ValidationError
except ImportError:  # pragma: no cover - the overlay itself has no Harbor dependency
    HarborTrajectory = None
    ValidationError = ValueError


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "eval_contracts"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class AtifIntegrityContractTests(unittest.TestCase):
    def test_nested_fixture_is_closed_and_fully_correlated(self) -> None:
        payload = load_fixture("atif_valid_nested.json")
        summary = validate_atif_integrity(payload)
        self.assertEqual(summary.root_trajectory_id, "parent-001")
        self.assertEqual(summary.trajectory_count, 2)
        self.assertEqual(summary.step_count, 5)
        self.assertEqual(summary.tool_call_count, 2)
        self.assertEqual(summary.correlated_tool_call_count, 2)
        self.assertEqual(summary.tool_observation_correlation, 1.0)
        self.assertEqual(summary.embedded_subagent_count, 1)
        self.assertEqual(summary.embedded_subagent_reference_count, 1)
        self.assertEqual(summary.external_trajectory_reference_count, 0)
        # ATIF-v1.7 session identity is run-scoped and may be shared.
        self.assertEqual(
            payload["session_id"], payload["subagent_trajectories"][0]["session_id"]
        )

    def test_invalid_offline_fixtures_are_rejected(self) -> None:
        cases = {
            "atif_invalid_orphan_tool_call.json": "no correlated observation result",
            "atif_invalid_duplicate_observation.json": "multiple results",
            "atif_invalid_duplicate_tool_call_id.json": "duplicates",
            "atif_invalid_dangling_subagent.json": "no direct child",
            "atif_invalid_duplicate_embedded_id.json": "duplicates",
            "atif_invalid_session_only_subagent_ref.json": (
                "session_id is informational only"
            ),
            "atif_invalid_missing_root_id.json": "trajectory_id must be",
        }
        for filename, message in cases.items():
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ContractError, message):
                    validate_atif_integrity(load_fixture(filename))

    def test_schema_version_must_be_explicitly_v17(self) -> None:
        payload = load_fixture("atif_valid_nested.json")
        payload["schema_version"] = "ATIF-v1.6"
        with self.assertRaisesRegex(ContractError, ATIF_SCHEMA_VERSION):
            validate_atif_integrity(payload)

    def test_tool_call_ids_are_unique_across_a_trajectory(self) -> None:
        payload = load_fixture("atif_valid_nested.json")
        second = copy.deepcopy(payload["steps"][1])
        second["step_id"] = 3
        second["observation"]["results"][0].pop("subagent_trajectory_ref")
        payload["steps"].append(second)
        with self.assertRaisesRegex(ContractError, "not unique within the trajectory"):
            validate_atif_integrity(payload)

    def test_uncorrelated_non_tool_observation_is_allowed(self) -> None:
        payload = {
            "schema_version": ATIF_SCHEMA_VERSION,
            "trajectory_id": "system-event-001",
            "agent": {"name": "pheno-test", "version": "0.1"},
            "steps": [
                {
                    "step_id": 1,
                    "source": "system",
                    "message": "Environment reset.",
                    "observation": {"results": [{"content": "reset complete"}]},
                }
            ],
        }
        summary = validate_atif_integrity(payload)
        self.assertEqual(summary.tool_call_count, 0)
        self.assertEqual(summary.tool_observation_correlation, 1.0)

    def test_external_references_require_an_explicit_non_closed_mode(self) -> None:
        payload = {
            "schema_version": ATIF_SCHEMA_VERSION,
            "trajectory_id": "external-parent-001",
            "agent": {"name": "pheno-test", "version": "0.1"},
            "steps": [
                {
                    "step_id": 1,
                    "source": "system",
                    "message": "Delegation completed.",
                    "observation": {
                        "results": [
                            {
                                "subagent_trajectory_ref": [
                                    {"trajectory_path": "subagents/child.json"}
                                ]
                            }
                        ]
                    },
                }
            ],
        }
        with self.assertRaisesRegex(ContractError, "closed offline artifact"):
            validate_atif_integrity(payload)
        summary = validate_atif_integrity(payload, allow_external_references=True)
        self.assertEqual(summary.external_trajectory_reference_count, 1)

    @unittest.skipIf(HarborTrajectory is None, "Harbor is not installed")
    def test_harbor_remains_the_canonical_schema_validator(self) -> None:
        payload = load_fixture("atif_valid_nested.json")
        validated = HarborTrajectory.model_validate(payload)
        self.assertEqual(validated.schema_version, ATIF_SCHEMA_VERSION)
        validate_atif_integrity(validated.to_json_dict())

    @unittest.skipIf(HarborTrajectory is None, "Harbor is not installed")
    def test_overlay_covers_integrity_gaps_not_enforced_by_harbor(self) -> None:
        # These are schema-valid in Harbor 0.6.1 / ATIF-v1.7.  They are not
        # evidence-complete because Harbor intentionally validates references,
        # not a call/result or embedded-child bijection.
        filenames = (
            "atif_invalid_orphan_tool_call.json",
            "atif_invalid_duplicate_observation.json",
            "atif_invalid_duplicate_tool_call_id.json",
            "atif_invalid_dangling_subagent.json",
            "atif_invalid_missing_root_id.json",
        )
        for filename in filenames:
            with self.subTest(filename=filename):
                HarborTrajectory.model_validate(load_fixture(filename))
                with self.assertRaises(ContractError):
                    validate_atif_integrity(load_fixture(filename))

    @unittest.skipIf(HarborTrajectory is None, "Harbor is not installed")
    def test_overlay_does_not_replace_harbor_validation(self) -> None:
        filenames = (
            "atif_invalid_session_only_subagent_ref.json",
            "atif_invalid_duplicate_embedded_id.json",
        )
        for filename in filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(ValidationError):
                    HarborTrajectory.model_validate(load_fixture(filename))


if __name__ == "__main__":
    unittest.main()
