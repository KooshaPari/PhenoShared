"""Metadata-only research evidence and benchmark contracts.

The package is deliberately independent from model loading and serving.  Its
network adapters may retrieve API metadata, but the core store accepts only
bounded metadata snapshots and cannot download model artifacts.
"""

from .aggregate_contracts import (
    AGGREGATE_SCHEMA_VERSION,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    MEMORY_SCOPE,
    RUN_PROVENANCE_SCHEMA_VERSION,
    TRUE_DECODE_FORMULA,
    aggregate_sha256,
    aggregate_trials,
    validate_aggregate_against_inputs,
    validate_aggregate_record,
)
from .atif import (
    ATIF_SCHEMA_VERSION,
    AtifIntegritySummary,
    validate_atif_integrity,
)
from .benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    derive_efficiency,
    promotion_reasons,
    scoreability_reasons,
    validate_benchmark_record,
)
from .contracts import (
    EVIDENCE_SCHEMA_VERSION,
    ContractError,
    make_record_id,
    validate_evidence_record,
)
from .eval_contracts import (
    SUITE_LOCK_SCHEMA_VERSION,
    suite_lock_scoreability_reasons,
    suite_lock_sha256,
    validate_suite_lock,
)
from .performance_blocks import (
    BOOTSTRAP_RESAMPLES as PERFORMANCE_BLOCK_BOOTSTRAP_RESAMPLES,
)
from .performance_blocks import (
    MINIMUM_BLOCK_COUNT,
    PERFORMANCE_BLOCK_SCHEMA_VERSION,
    build_performance_block_record,
    performance_block_id,
    performance_block_sha256,
    validate_performance_block_record,
)
from .replay_stability import (
    MAX_REPLICATES as MAX_REPLAY_REPLICATES,
)
from .replay_stability import (
    MIN_GREEDY_REPLICATES_PER_TASK,
    MIN_SAMPLED_REPLICATES_PER_TASK,
    REPLAY_STABILITY_SCHEMA_VERSION,
    build_replay_stability_record,
    replay_replicate_id,
    replay_stability_sha256,
    validate_replay_stability_record,
)
from .replay_stability import (
    THRESHOLDS as REPLAY_STABILITY_THRESHOLDS,
)
from .store import RegistryStore
from .telemetry import (
    MAX_TELEMETRY_BUNDLE_BYTES,
    MAX_TELEMETRY_SAMPLES,
    MAXIMUM_OVERHEAD_FRACTION,
    MAXIMUM_OVERHEAD_PAIRS,
    MINIMUM_OVERHEAD_PAIRS,
    TELEMETRY_SCHEMA_VERSION,
    build_telemetry_bundle,
    telemetry_bundle_sha256,
    validate_telemetry_bundle,
)
from .telemetry import (
    MEMORY_SCOPE as TELEMETRY_MEMORY_SCOPE,
)
from .telemetry import (
    METRIC_NAMES as TELEMETRY_METRIC_NAMES,
)
from .telemetry import (
    MINIMUM_COVERAGE_FRACTION as TELEMETRY_MINIMUM_COVERAGE_FRACTION,
)
from .telemetry import (
    PROFILE_NOT_APPLICABLE_METRICS as TELEMETRY_NOT_APPLICABLE_METRICS,
)
from .telemetry import (
    PROFILE_REQUIRED_METRICS as TELEMETRY_REQUIRED_METRICS,
)
from .tournament import (
    TOURNAMENT_SCHEMA_VERSION,
    build_candidate_review,
    validate_tournament,
)
from .trial_contracts import (
    ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION,
    MAX_ARTIFACT_BUNDLE_BYTES,
    TRIAL_SCHEMA_VERSION,
    trial_scoreability_reasons,
    trial_sha256,
    validate_trial_artifact_bundle,
    validate_trial_record,
)

__all__ = [
    "AGGREGATE_SCHEMA_VERSION",
    "ARTIFACT_BUNDLE_SUMMARY_SCHEMA_VERSION",
    "ATIF_SCHEMA_VERSION",
    "AtifIntegritySummary",
    "ContractError",
    "BENCHMARK_SCHEMA_VERSION",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "EVIDENCE_SCHEMA_VERSION",
    "MAX_ARTIFACT_BUNDLE_BYTES",
    "MAX_REPLAY_REPLICATES",
    "MAXIMUM_OVERHEAD_FRACTION",
    "MAXIMUM_OVERHEAD_PAIRS",
    "MAX_TELEMETRY_BUNDLE_BYTES",
    "MAX_TELEMETRY_SAMPLES",
    "MEMORY_SCOPE",
    "MINIMUM_BLOCK_COUNT",
    "MINIMUM_OVERHEAD_PAIRS",
    "MIN_GREEDY_REPLICATES_PER_TASK",
    "MIN_SAMPLED_REPLICATES_PER_TASK",
    "PERFORMANCE_BLOCK_BOOTSTRAP_RESAMPLES",
    "PERFORMANCE_BLOCK_SCHEMA_VERSION",
    "RegistryStore",
    "RUN_PROVENANCE_SCHEMA_VERSION",
    "REPLAY_STABILITY_SCHEMA_VERSION",
    "REPLAY_STABILITY_THRESHOLDS",
    "SUITE_LOCK_SCHEMA_VERSION",
    "TOURNAMENT_SCHEMA_VERSION",
    "TELEMETRY_METRIC_NAMES",
    "TELEMETRY_MEMORY_SCOPE",
    "TELEMETRY_MINIMUM_COVERAGE_FRACTION",
    "TELEMETRY_NOT_APPLICABLE_METRICS",
    "TELEMETRY_REQUIRED_METRICS",
    "TELEMETRY_SCHEMA_VERSION",
    "TRIAL_SCHEMA_VERSION",
    "TRUE_DECODE_FORMULA",
    "aggregate_sha256",
    "aggregate_trials",
    "build_candidate_review",
    "build_performance_block_record",
    "build_replay_stability_record",
    "build_telemetry_bundle",
    "derive_efficiency",
    "make_record_id",
    "promotion_reasons",
    "replay_replicate_id",
    "replay_stability_sha256",
    "performance_block_id",
    "performance_block_sha256",
    "scoreability_reasons",
    "suite_lock_scoreability_reasons",
    "suite_lock_sha256",
    "trial_scoreability_reasons",
    "trial_sha256",
    "telemetry_bundle_sha256",
    "validate_aggregate_against_inputs",
    "validate_aggregate_record",
    "validate_atif_integrity",
    "validate_benchmark_record",
    "validate_performance_block_record",
    "validate_replay_stability_record",
    "validate_telemetry_bundle",
    "validate_trial_artifact_bundle",
    "validate_trial_record",
    "validate_suite_lock",
    "validate_tournament",
    "validate_evidence_record",
]
