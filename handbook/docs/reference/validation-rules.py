# Validation rules reference
#
# Reference implementation absorbed from the Guardis workstream.

"""Composable validation helpers absorbed from the Guardis workstream."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol, TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


class Rule(Protocol):
    def __call__(self, value: Any) -> "ValidationResult": ...


@dataclass(slots=True)
class RuleError:
    field: str
    message: str
    value: Any = None


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[RuleError] = field(default_factory=list)
    value: Any = None

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=[*self.errors, *other.errors],
            value=self.value if self.value is not None else other.value,
        )


def success(value: Any = None) -> ValidationResult:
    return ValidationResult(valid=True, value=value)


def failure(message: str, field: str = "", value: Any = None) -> ValidationResult:
    return ValidationResult(valid=False, errors=[RuleError(field=field, message=message, value=value)], value=value)


def create_error(message: str, field: str = "", value: Any = None) -> RuleError:
    return RuleError(field=field, message=message, value=value)


def _coerce_result(result: Any, value: Any) -> ValidationResult:
    if isinstance(result, ValidationResult):
        return result
    if result:
        return success(value)
    return failure("validation failed", value=value)


def rule(name: str, fn: Callable[[Any], bool], message: str | None = None) -> Rule:
    def _rule(value: Any) -> ValidationResult:
        ok = False
        try:
            ok = bool(fn(value))
        except Exception as exc:  # noqa: BLE001
            return failure(f"{name}: {exc}", value=value)
        return success(value) if ok else failure(message or f"{name} failed", value=value)

    return _rule


def rule_fn(fn: Callable[[Any], Any]) -> Rule:
    def _rule(value: Any) -> ValidationResult:
        return _coerce_result(fn(value), value)

    return _rule


def required() -> Rule:
    return rule("required", lambda value: value is not None and value != "", "value is required")


def not_null() -> Rule:
    return rule("not_null", lambda value: value is not None, "value must not be null")


def not_undefined() -> Rule:
    return not_null()


def not_empty() -> Rule:
    return rule("not_empty", lambda value: value is not None and len(value) > 0, "value must not be empty")


def length_min(limit: int) -> Rule:
    return rule("min_length", lambda value: value is not None and len(value) >= limit, f"length must be >= {limit}")


def length_max(limit: int) -> Rule:
    return rule("max_length", lambda value: value is not None and len(value) <= limit, f"length must be <= {limit}")


def matches(pattern: str | re.Pattern[str]) -> Rule:
    regex = re.compile(pattern) if isinstance(pattern, str) else pattern
    return rule("matches", lambda value: value is not None and bool(regex.search(str(value))), f"value must match {regex.pattern}")


def email() -> Rule:
    return matches(r"^[w.+-]+@[w.-]+.[A-Za-z]{2,}$")


def url() -> Rule:
    def _is_url(value: Any) -> bool:
        if value is None:
            return False
        parsed = urlparse(str(value))
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    return rule("url", _is_url, "value must be a valid URL")


def min(limit: float) -> Rule:
    return rule("min", lambda value: value is not None and value >= limit, f"value must be >= {limit}")


def max(limit: float) -> Rule:
    return rule("max", lambda value: value is not None and value <= limit, f"value must be <= {limit}")


def positive() -> Rule:
    return rule("positive", lambda value: value is not None and value > 0, "value must be positive")


def integer() -> Rule:
    return rule("integer", lambda value: isinstance(value, int) and not isinstance(value, bool), "value must be an integer")


def in_range(start: float, end: float) -> Rule:
    return rule("in_range", lambda value: value is not None and start <= value <= end, f"value must be in range [{start}, {end}]")


def collection_not_empty() -> Rule:
    return not_empty()


def collection_min_length(limit: int) -> Rule:
    return length_min(limit)


def collection_max_length(limit: int) -> Rule:
    return length_max(limit)


def collection_all(predicate: Callable[[Any], bool]) -> Rule:
    return rule("all", lambda value: value is not None and all(predicate(item) for item in value), "all items must pass")


def collection_any(predicate: Callable[[Any], bool]) -> Rule:
    return rule("any", lambda value: value is not None and any(predicate(item) for item in value), "at least one item must pass")


def collection_unique() -> Rule:
    return rule("unique", lambda value: value is not None and len(set(value)) == len(list(value)), "items must be unique")


def and_(*rules: Rule) -> Rule:
    def _rule(value: Any) -> ValidationResult:
        result = success(value)
        for item in rules:
            result = result.merge(item(value))
        return result

    return _rule


def or_(*rules: Rule) -> Rule:
    def _rule(value: Any) -> ValidationResult:
        errors: list[RuleError] = []
        for item in rules:
            result = item(value)
            if result.valid:
                return success(value)
            errors.extend(result.errors)
        return ValidationResult(valid=False, errors=errors, value=value)

    return _rule


def not_(rule_obj: Rule) -> Rule:
    def _rule(value: Any) -> ValidationResult:
        result = rule_obj(value)
        if result.valid:
            return failure("negated rule matched", value=value)
        return success(value)

    return _rule


def all_(predicate: Callable[[Any], bool]) -> Rule:
    return collection_all(predicate)


def any_(predicate: Callable[[Any], bool]) -> Rule:
    return collection_any(predicate)


@dataclass(slots=True)
class Guard:
    value: Any
    fail_fast: bool = False
    errors: list[RuleError] = field(default_factory=list)

    def check(self, rule_obj: Rule, field_name: str | None = None) -> "Guard":
        target = self._select(field_name) if field_name else self.value
        result = rule_obj(target)
        if not result.valid:
            if field_name:
                self.errors.extend(
                    [RuleError(field=field_name, message=err.message, value=target) for err in result.errors]
                )
            else:
                self.errors.extend(result.errors)
        return self

    def validate(self) -> ValidationResult:
        return ValidationResult(valid=not self.errors, errors=list(self.errors), value=self.value)

    def _select(self, field_name: str) -> Any:
        if isinstance(self.value, dict):
            if field_name in self.value:
                return self.value[field_name]
            self.errors.append(RuleError(field=field_name, message="field is missing"))
            return None
        if hasattr(self.value, field_name):
            return getattr(self.value, field_name)
        self.errors.append(RuleError(field=field_name, message="field is missing"))
        return None


def guard(value: Any, fail_fast: bool = False) -> Guard:
    return Guard(value=value, fail_fast=fail_fast)

