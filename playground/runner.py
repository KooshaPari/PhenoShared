"""RLVR playground experiment runner — combinatorial matrix with verifier integration."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from pheno.paths import CONFIG_DIR, PHENO_ROOT, TRAINING_DIR
from verifier.harness import VerifierHarness
from verifier.rewards import compute_rewards


def expand_env(value: str) -> str:
    if not value:
        return value
    out = os.path.expandvars(
        value.replace("${PHENO_ROOT}", str(PHENO_ROOT)).replace(
            "${HOME}", str(Path.home())
        )
    )
    if out.startswith("${") and ":-}" in out:
        key, default = out[2:].split(":-", 1)
        default = default.rstrip("}")
        return os.environ.get(key, default)
    return out


def _meta_lookup(section: dict[str, Any], key: str) -> dict[str, Any]:
    return dict(section.get(key, {}))


@dataclass
class ExperimentSpec:
    harness_type: str
    model_net: str
    routing_policy: str
    decode_experiment: str
    train_mode: str
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def experiment_id(self) -> str:
        raw = (
            f"{self.harness_type}|{self.model_net}|{self.routing_policy}|"
            f"{self.decode_experiment}|{self.train_mode}"
        )
        digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
        return (
            f"{self.harness_type}__{self.model_net}__{self.routing_policy[:8]}__"
            f"{self.decode_experiment[:12]}__{self.train_mode}__{digest}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "harness_type": self.harness_type,
            "model_net": self.model_net,
            "routing_policy": self.routing_policy,
            "decode_experiment": self.decode_experiment,
            "train_mode": self.train_mode,
            "experiment_id": self.experiment_id,
            "meta": self.meta,
        }


class PlaygroundRunner:
    """Generate filtered Cartesian product and write experiment manifests."""

    def __init__(self, matrix_path: Path | None = None):
        self.matrix_path = matrix_path or (CONFIG_DIR / "playground_matrix.yaml")
        self.matrix = self._load_matrix()
        out_cfg = self.matrix.get("output", {})
        exp_dir = expand_env(
            out_cfg.get("experiments_dir", str(PHENO_ROOT / "eval" / "experiments"))
        )
        self.experiments_dir = Path(exp_dir)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        rlvr_path = expand_env(
            out_cfg.get(
                "rlvr_config", str(PHENO_ROOT / "training" / "rlvr_config.yaml")
            )
        )
        self.harness = VerifierHarness(config_path=Path(rlvr_path))
        self.pass_threshold = float(out_cfg.get("pass_threshold", 0.75))
        self.trace_glob = out_cfg.get("trace_glob", "traces_*.jsonl")

    def _load_matrix(self) -> dict[str, Any]:
        raw = yaml.safe_load(self.matrix_path.read_text(encoding="utf-8"))
        return raw or {}

    def _matches_rule(self, spec: ExperimentSpec, rule: dict[str, Any]) -> bool:
        """Return True when every key in rule['when'] matches the spec (AND logic)."""
        when = rule.get("when", {})
        if not when:
            return False
        field_map = {
            "harness_type": spec.harness_type,
            "model_net": spec.model_net,
            "routing_policy": spec.routing_policy,
            "decode_experiment": spec.decode_experiment,
            "train_mode": spec.train_mode,
        }
        for dim, expected in when.items():
            actual = field_map.get(dim)
            if actual is None:
                return False
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def _is_filtered_out(self, spec: ExperimentSpec) -> str | None:
        filters = self.matrix.get("filters", {})
        cloud_nets = set(filters.get("cloud_model_nets", []))
        local_train = set(filters.get("local_gpu_train_modes", []))

        if filters.get("skip_cloud_gpu_variants") and spec.train_mode in local_train:
            if spec.model_net in cloud_nets:
                return "cloud model_net with local GPU train_mode"

        for rule in filters.get("incompatible", []):
            if self._matches_rule(spec, rule):
                reason = rule.get("reason", "incompatible rule")
                return str(reason) if reason is not None else None

        return None

    def _enrich_meta(self, spec: ExperimentSpec) -> dict[str, Any]:
        return {
            "harness": _meta_lookup(
                self.matrix.get("harness_types_meta", {}), spec.harness_type
            ),
            "model_net": _meta_lookup(
                self.matrix.get("model_nets_meta", {}), spec.model_net
            ),
            "routing_policy": _meta_lookup(
                self.matrix.get("routing_policies_meta", {}), spec.routing_policy
            ),
            "decode_experiment": _meta_lookup(
                self.matrix.get("decode_experiments_meta", {}), spec.decode_experiment
            ),
            "train_mode": _meta_lookup(
                self.matrix.get("train_modes_meta", {}), spec.train_mode
            ),
            "hardware": self.matrix.get("hardware", {}),
        }

    def iter_experiments(
        self,
        *,
        harness_types: list[str] | None = None,
        model_nets: list[str] | None = None,
        routing_policies: list[str] | None = None,
        decode_experiments: list[str] | None = None,
        train_modes: list[str] | None = None,
    ) -> Iterator[ExperimentSpec]:
        dims = self.matrix.get("dimensions", {})
        ht = harness_types or dims.get("harness_types", [])
        mn = model_nets or dims.get("model_nets", [])
        rp = routing_policies or dims.get("routing_policies", [])
        de = decode_experiments or dims.get("decode_experiments", [])
        tm = train_modes or dims.get("train_modes", [])

        for combo in product(ht, mn, rp, de, tm):
            spec = ExperimentSpec(
                harness_type=combo[0],
                model_net=combo[1],
                routing_policy=combo[2],
                decode_experiment=combo[3],
                train_mode=combo[4],
            )
            reason = self._is_filtered_out(spec)
            if reason:
                continue
            spec.meta = self._enrich_meta(spec)
            yield spec

    def count_experiments(self, **subset: Any) -> int:
        return sum(1 for _ in self.iter_experiments(**subset))

    def _resolve_training_config(self, spec: ExperimentSpec) -> str | None:
        tm_meta = spec.meta.get("train_mode", {})
        cfg = tm_meta.get("training_config")
        if not cfg:
            return None
        return expand_env(str(cfg))

    def _verify_traces(self, limit: int = 50) -> dict[str, Any]:
        """Run verifier + rewards on available trace JSONL (scaffold eval)."""
        traces: list[dict[str, Any]] = []
        for path in sorted(TRAINING_DIR.glob(self.trace_glob)):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    traces.append(json.loads(line))
                    if len(traces) >= limit:
                        break
            if len(traces) >= limit:
                break

        if not traces:
            return {
                "trace_count": 0,
                "verifier_pass_rate": None,
                "mean_reward": None,
                "samples": [],
            }

        results = []
        rewards = []
        for trace in traces:
            vr = self.harness.verify_trace(trace)
            rb = compute_rewards(vr, pass_threshold=self.pass_threshold)
            results.append(
                {"trace_id": vr.trace_id, "passed": rb.passed, "total": rb.total}
            )
            rewards.append(rb.total)

        passed = sum(1 for r in results if r["passed"])
        return {
            "trace_count": len(traces),
            "verifier_pass_rate": round(passed / len(traces), 4),
            "mean_reward": round(sum(rewards) / len(rewards), 4),
            "samples": results[:5],
        }

    def build_manifest(
        self,
        spec: ExperimentSpec,
        *,
        run_verify: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        train_cfg = self._resolve_training_config(spec)
        manifest: dict[str, Any] = {
            "schema": "pheno.playground.manifest/v1",
            "created_at": datetime.now(UTC).isoformat(),
            "experiment_id": spec.experiment_id,
            "dimensions": spec.to_dict(),
            "hardware": self.matrix.get("hardware", {}),
            "training_config": train_cfg,
            "rlvr_config": expand_env(
                self.matrix.get("output", {}).get(
                    "rlvr_config", str(PHENO_ROOT / "training" / "rlvr_config.yaml")
                )
            ),
            "pass_threshold": self.pass_threshold,
            "dry_run": dry_run,
            "status": "planned" if dry_run else "manifest_written",
        }

        if run_verify and not dry_run:
            manifest["rlvr_eval"] = self._verify_traces()
            manifest["status"] = "verified"

        return manifest

    def write_manifest(self, manifest: dict[str, Any]) -> Path:
        exp_id = manifest["experiment_id"]
        out_path = self.experiments_dir / f"{exp_id}.json"
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return out_path

    def run(
        self,
        *,
        limit: int | None = None,
        run_verify: bool = False,
        dry_run: bool = False,
        **subset: Any,
    ) -> list[Path]:
        written: list[Path] = []
        for i, spec in enumerate(self.iter_experiments(**subset)):
            if limit is not None and i >= limit:
                break
            manifest = self.build_manifest(spec, run_verify=run_verify, dry_run=dry_run)
            if dry_run:
                manifest["status"] = "dry_run"
            written.append(self.write_manifest(manifest))
        return written
