"""Tests for TaskStatus enum identity and coercion (P25/P26/R1).

Covers:
- P25: TaskStatus aliases are the SAME enum members (identity + equality)
- P26: TaskStatus coercion + ValueError on invalid wire values
- R1: StrEnum PASS is OK requirement
"""

from __future__ import annotations

import pytest

from bench.types import TaskStatus


class TestTaskStatusAliasesIdentity:
    """P25: Aliases (PASS/FAIL/SKIP) are references, not siblings."""

    def test_pass_is_ok_identity(self) -> None:
        """PASS is the same object as OK (not just equal)."""
        assert TaskStatus.PASS is TaskStatus.OK

    def test_fail_is_wrong_identity(self) -> None:
        """FAIL is the same object as WRONG."""
        assert TaskStatus.FAIL is TaskStatus.WRONG

    def test_skip_is_skipped_identity(self) -> None:
        """SKIP is the same object as SKIPPED."""
        assert TaskStatus.SKIP is TaskStatus.SKIPPED

    def test_pass_eq_ok_equality(self) -> None:
        """PASS == OK (value equality also holds)."""
        assert TaskStatus.PASS == TaskStatus.OK

    def test_fail_eq_wrong_equality(self) -> None:
        """FAIL == WRONG."""
        assert TaskStatus.FAIL == TaskStatus.WRONG

    def test_skip_eq_skipped_equality(self) -> None:
        """SKIP == SKIPPED."""
        assert TaskStatus.SKIP == TaskStatus.SKIPPED

    def test_pass_wire_value(self) -> None:
        """PASS serializes to 'ok' on the wire."""
        assert TaskStatus.PASS == "ok"
        assert str(TaskStatus.PASS) == "ok"

    def test_fail_wire_value(self) -> None:
        """FAIL serializes to 'wrong'."""
        assert TaskStatus.FAIL == "wrong"

    def test_all_canonical_members(self) -> None:
        """Canonical members: OK, WRONG, ERROR, SKIPPED, TIMEOUT."""
        canonical = {TaskStatus.OK, TaskStatus.WRONG, TaskStatus.ERROR,
                     TaskStatus.SKIPPED, TaskStatus.TIMEOUT}
        assert len(canonical) == 5

    def test_aliases_dont_expand_member_count(self) -> None:
        """Aliases don't add new members — count stays at 5."""
        members = list(TaskStatus)
        assert len(members) == 5


class TestTaskStatusCoercion:
    """P26: TaskStatus coercion from wire values."""

    def test_coerce_ok_string(self) -> None:
        """'ok' coerces to OK."""
        assert TaskStatus("ok") == TaskStatus.OK

    def test_pass_alias_maps_to_ok_wire(self) -> None:
        """PASS alias has wire value 'ok' (not 'pass')."""
        assert TaskStatus.PASS.value == "ok"

    def test_fail_alias_maps_to_wrong_wire(self) -> None:
        """FAIL alias has wire value 'wrong' (not 'fail')."""
        assert TaskStatus.FAIL.value == "wrong"

    def test_coerce_wrong_string(self) -> None:
        """'wrong' coerces to WRONG."""
        assert TaskStatus("wrong") == TaskStatus.WRONG

    def test_coerce_error_string(self) -> None:
        """'error' coerces to ERROR."""
        assert TaskStatus("error") == TaskStatus.ERROR

    def test_coerce_skipped_string(self) -> None:
        """'skipped' coerces to SKIPPED."""
        assert TaskStatus("skipped") == TaskStatus.SKIPPED

    def test_coerce_timeout_string(self) -> None:
        """'timeout' coerces to TIMEOUT."""
        assert TaskStatus("timeout") == TaskStatus.TIMEOUT

    def test_coerce_invalid_raises(self) -> None:
        """Invalid wire value 'done' raises ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("done")

    def test_coerce_invalid_empty_raises(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("")

    def test_coerce_invalid_random_raises(self) -> None:
        """Random string raises ValueError."""
        with pytest.raises(ValueError):
            TaskStatus("random_status")
