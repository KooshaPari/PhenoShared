"""DAG-32: behavioral validation of the Desktop NVIDIA dual-GPU lane configs.

DAG-69's ``tests/test_desktop_lane_schema.py`` enforces the *strict*
JSON-Schema contract of the upstream ``desktop_nvidia_qwen35_lane.yaml``.
This file pins the *behavioral invariants* the rest of the desktop lane
machinery depends on. The two are intentionally complementary: the
schema linter catches type/structure drift; this file asserts the
*consumer-facing* promises (canonical model, dual-GPU baseline, gating
lists, boolean policy flags, device field triples).

Every consumer that touches the lane YAML was surveyed:

* ``scripts/provision_desktop_worktree.py`` reads ``REPO_ROOT`` (a Path
  constant) and writes ``evidence/dual_gpu/worktrees.json``. It does
  not open the lane YAML itself, so this test is the *only* gate that
  the YAML contract still describes a usable dual-GPU baseline when
  the provisioner runs.
* ``scripts/run_desktop_lane_eval.py`` reads
  ``config/desktop_nvidia_qwen35_lane.yaml`` (sibling-resolved via
  ``ROOT``), SHA-256s it for the eval envelope, and pins
  ``local/qwen35-08b`` as the model alias. The plan's
  ``contract_sha256`` field breaks loudly if the file is dropped or
  moved, but it does *not* check that ``scope.canonical_model`` is
  still ``Qwen/Qwen3.5-0.8B`` — this test pins that.
* ``evidence/dual_gpu/check.sh`` parses ``nvidia-smi`` CSV and writes
  ``heartbeat.json`` with a ``live_verified`` evidence label. The
  heartbeat cross-references ``host_manifest.yaml``, which is keyed on
  the *count* of GPUs the script observed. This test pins
  ``hardware.devices`` to enumerate >= 2 GPUs so a single-GPU host
  cannot silently pass the lane as a "dual-GPU" baseline (per AGENTS.md
  section 2.3).

Divergences between the upstream and Fedora 44 yaml that this test
file does *not* try to police (they are downstream of the schema
linter's scope):

* The Fedora 44 derivative (``v2.fedora44``) does **not** expose a
  ``derived_from.upstream_file`` field — the parent link lives only in
  the YAML header comment and in the ``schema_version`` variant suffix.
  Test 3 below accepts either the explicit ``derived_from`` field *or*
  the variant suffix as evidence of derivation; the explicit field is
  preferred, the suffix is the documented fallback.
* The Fedora 44 yaml also drifts structurally from the upstream on
  ``pytorch_device`` / ``llama_cpp_isolated_device`` for the helper
  GPU (``cuda:1`` / ``CUDA1`` vs the upstream's ``cuda:0`` / ``CUDA0``)
  and on the shape of ``provenance_requirements`` (the Fedora 44
  variant collapses the upstream's per-field requirement names into
  per-field ID lists). Both are real divergences; neither is in scope
  for a *behavioral* invariant test, so they are not asserted here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# Skip the entire module if PyYAML is unavailable; everything below
# assumes yaml.safe_load works.
pytestmark = pytest.mark.skipif(
    yaml is None, reason="PyYAML is required for desktop lane config tests"
)


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_CONFIG = ROOT / "config" / "desktop_nvidia_qwen35_lane.yaml"
FEDORA44_CONFIG = ROOT / "config" / "desktop_nvidia_dual_gpu_fedora44.yaml"

#: Canonical HuggingFace-style model identifier pinned across both lane
#: contracts and by ``scripts/run_desktop_lane_eval.py::_is_qwen35_model``.
EXPECTED_CANONICAL_MODEL = "Qwen/Qwen3.5-0.8B"

#: AGENTS.md section 2.3 declares a dual-GPU baseline (3090 Ti + 1080 Ti);
#: ``evidence/dual_gpu/check.sh``'s ``host_manifest.yaml`` rolling tail
#: counts the GPUs the script observed, so the contract must enumerate
#: at least two.
EXPECTED_MIN_DEVICES = 2

#: Top-level keys the downstream consumers reach into. Mirrors (but does
#: not duplicate) the JSON-Schema's ``required`` array from
#: ``tests/test_desktop_lane_schema.py``.
REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "schema_version",
    "status",
    "effective_date",
    "scope",
    "execution_policy",
    "hardware",
    "runtime_policy",
    "provenance_requirements",
    "promotion_gates",
    "external_backend_references",
)


# ---------------------------------------------------------------------------
# Helpers + fixtures
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a lane YAML, fail loudly on parse errors or non-mapping roots."""
    if not path.exists():
        pytest.skip(f"lane config not found at {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        pytest.fail(f"{path.name} failed to parse: {exc}")
    assert isinstance(loaded, dict), f"{path.name} must decode to a mapping"
    assert loaded, f"{path.name} decoded to an empty mapping"
    return loaded


@pytest.fixture(scope="module")
def upstream_config() -> dict[str, Any]:
    """Load the upstream ``desktop_nvidia_qwen35_lane.yaml`` exactly once."""
    return _load_yaml(UPSTREAM_CONFIG)


@pytest.fixture(scope="module")
def fedora44_config() -> dict[str, Any]:
    """Load the Fedora 44 derivative ``desktop_nvidia_dual_gpu_fedora44.yaml``."""
    return _load_yaml(FEDORA44_CONFIG)


@pytest.fixture(scope="module")
def lane_configs(
    upstream_config: dict[str, Any],
    fedora44_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bundle both configs so the dual-config tests can iterate over them."""
    return {"upstream": upstream_config, "fedora44": fedora44_config}


# ---------------------------------------------------------------------------
# 1. Upstream config parses + has the structural shape every consumer needs.
# ---------------------------------------------------------------------------


def test_upstream_lane_config_loads_and_validates(
    upstream_config: dict[str, Any],
) -> None:
    """Upstream config parses and exposes every consumer-facing top-level key."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in upstream_config, (
            f"upstream lane config missing required top-level key {key!r}"
        )
    # The contract is planning-only by default; only an explicit execution
    # window can flip it to ``active``. A regression here would let the
    # provisioner / runner think they have authorization they don't.
    assert upstream_config["status"] == "planning_only"
    # The schema_version pattern is also asserted by the JSON-Schema
    # linter; we duplicate it here only as a cheap belt-and-suspenders
    # check so a parse that bypasses jsonschema still trips it.
    version = upstream_config["schema_version"]
    assert isinstance(version, str) and version.startswith(
        "pheno.desktop-nvidia.qwen35-lane."
    ), f"unexpected upstream schema_version: {version!r}"


# ---------------------------------------------------------------------------
# 2. Fedora 44 derivative parses + has the same structural shape.
# ---------------------------------------------------------------------------


def test_fedora44_lane_config_loads_and_validates(
    fedora44_config: dict[str, Any],
) -> None:
    """Fedora 44 derivative parses and carries every consumer-facing key."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in fedora44_config, (
            f"fedora44 lane config missing required top-level key {key!r}"
        )
    # The Fedora 44 variant must also be planning-only — no execution
    # without an explicit window, even on the remote host.
    assert fedora44_config["status"] == "planning_only"
    # And it must carry the schema_version family prefix so it round-trips
    # through ``scripts/run_desktop_lane_eval.py``'s contract_sha256 path
    # alongside the upstream.
    version = fedora44_config["schema_version"]
    assert isinstance(version, str) and version.startswith(
        "pheno.desktop-nvidia.qwen35-lane."
    ), f"unexpected fedora44 schema_version: {version!r}"


# ---------------------------------------------------------------------------
# 3. Fedora 44 derivative maintains a "derives from" link to the upstream.
# ---------------------------------------------------------------------------


def test_fedora44_derivative_points_to_existing_upstream(
    fedora44_config: dict[str, Any],
) -> None:
    """Fedora 44 derivative must reference the upstream config file.

    Preferred link: ``derived_from.upstream_file`` whose value resolves
    to an existing path that points at ``desktop_nvidia_qwen35_lane.yaml``.

    Fallback: the ``schema_version`` must carry a variant suffix (e.g.
    ``v2.fedora44``) that identifies the file as a derivative of the
    upstream ``v1`` contract. This is the documented behavior of the
    current Fedora 44 yaml — the parent link lives only in the header
    comment + schema_version, not in a structural ``derived_from``
    field. A future migration that adds the explicit field would make
    this test prefer it (see the early-return branch below).
    """
    derived_from = fedora44_config.get("derived_from")
    if isinstance(derived_from, dict) and "upstream_file" in derived_from:
        upstream_rel = derived_from["upstream_file"]
        assert isinstance(upstream_rel, str) and upstream_rel, (
            "derived_from.upstream_file must be a non-empty string"
        )
        candidate = (FEDORA44_CONFIG.parent / upstream_rel).resolve()
        assert candidate.exists(), (
            f"derived_from.upstream_file={upstream_rel!r} does not exist "
            f"(resolved to {candidate})"
        )
        assert candidate.name == UPSTREAM_CONFIG.name, (
            f"derived_from.upstream_file points to {candidate.name}, "
            f"expected the upstream contract {UPSTREAM_CONFIG.name!r}"
        )
        return

    # Fallback: schema_version must show a derivation suffix beyond the
    # upstream's plain ``v1``. Acceptable forms include ``v2.fedora44``,
    # ``v3.ubuntu2404``, ``v2.wsl2``, etc. — anything where the post-v
    # token is non-empty AND the schema_version as a whole retains the
    # ``pheno.desktop-nvidia.qwen35-lane.`` prefix.
    schema_version = fedora44_config.get("schema_version", "")
    assert isinstance(schema_version, str) and schema_version, (
        "fedora44 schema_version must be a non-empty string"
    )
    assert schema_version.startswith("pheno.desktop-nvidia.qwen35-lane.v"), (
        f"unexpected fedora44 schema_version prefix: {schema_version!r}"
    )
    # Strip the shared prefix + the literal ``v``; the remainder should
    # contain a ``.`` (variant suffix) OR end in a known derivative name.
    tail = schema_version[len("pheno.desktop-nvidia.qwen35-lane.v") :]
    assert tail and tail[0].isdigit(), (
        f"fedora44 schema_version must begin with a digit after the v: "
        f"got {schema_version!r}"
    )
    suffix = tail.split(".", 1)[1] if "." in tail else ""
    assert suffix or schema_version.endswith(("fedora44", "fedora-44", "wsl2")), (
        "fedora44 lane config lacks both a derived_from.upstream_file "
        "field and a schema_version variant suffix identifying it as a "
        f"derivative of the upstream contract; got {schema_version!r}"
    )


# ---------------------------------------------------------------------------
# 4. Both configs enumerate >= 2 GPUs (dual-GPU baseline per AGENTS.md 2.3).
# ---------------------------------------------------------------------------


def test_lane_config_has_dual_gpu_devices(
    lane_configs: dict[str, dict[str, Any]],
) -> None:
    """``hardware.devices`` must carry >= 2 GPUs in both configs."""
    for name, cfg in lane_configs.items():
        devices = cfg["hardware"]["devices"]
        assert isinstance(devices, dict), (
            f"{name}: hardware.devices must be an object map"
        )
        assert len(devices) >= EXPECTED_MIN_DEVICES, (
            f"{name}: hardware.devices has {len(devices)} entry/ies; "
            f"dual-GPU baseline requires >= {EXPECTED_MIN_DEVICES} "
            f"(AGENTS.md section 2.3)"
        )


# ---------------------------------------------------------------------------
# 5. Canonical model is the exact Qwen3.5-0.8B HF id in both configs.
# ---------------------------------------------------------------------------


def test_lane_config_canonical_model_is_qwen35(
    lane_configs: dict[str, dict[str, Any]],
) -> None:
    """``scope.canonical_model`` is exactly ``Qwen/Qwen3.5-0.8B``."""
    for name, cfg in lane_configs.items():
        canonical = cfg["scope"]["canonical_model"]
        assert isinstance(canonical, str), (
            f"{name}: scope.canonical_model must be a string"
        )
        assert canonical == EXPECTED_CANONICAL_MODEL, (
            f"{name}: scope.canonical_model={canonical!r}; expected "
            f"{EXPECTED_CANONICAL_MODEL!r}"
        )


# ---------------------------------------------------------------------------
# 6. ``promotion_gates`` is a non-empty list of gating names.
# ---------------------------------------------------------------------------


def test_lane_config_promotion_gates_non_empty(
    lane_configs: dict[str, dict[str, Any]],
) -> None:
    """``promotion_gates`` is a non-empty list of non-empty strings."""
    for name, cfg in lane_configs.items():
        gates = cfg["promotion_gates"]
        assert isinstance(gates, list), (
            f"{name}: promotion_gates must be a list; got {type(gates).__name__}"
        )
        assert gates, f"{name}: promotion_gates must be non-empty"
        for gate in gates:
            assert isinstance(gate, str) and gate, (
                f"{name}: promotion_gates entries must be non-empty strings; "
                f"got {gate!r}"
            )


# ---------------------------------------------------------------------------
# 7. ``execution_policy.allow_*`` flags are all real booleans.
# ---------------------------------------------------------------------------


def test_lane_config_execution_policy_flags_are_well_typed(
    lane_configs: dict[str, dict[str, Any]],
) -> None:
    """Every ``execution_policy.allow_*`` flag is a real ``bool`` (not str/int)."""
    allow_keys = (
        "allow_model_download",
        "allow_install",
        "allow_server_launch",
        "allow_model_inference",
        "allow_benchmark_execution",
        "allow_harbor",
        "require_explicit_window",
    )
    for name, cfg in lane_configs.items():
        policy = cfg["execution_policy"]
        for key in allow_keys:
            assert isinstance(policy[key], bool), (
                f"{name}: execution_policy.{key} must be a boolean; "
                f"got {type(policy[key]).__name__}={policy[key]!r}"
            )


# ---------------------------------------------------------------------------
# 8. Each device carries the structural triple ``role / vram_mib / nvidia_smi_index``.
# ---------------------------------------------------------------------------


def test_lane_config_hardware_devices_have_required_fields(
    lane_configs: dict[str, dict[str, Any]],
) -> None:
    """Each device entry has ``role``, ``vram_mib``, ``nvidia_smi_index``."""
    for name, cfg in lane_configs.items():
        devices = cfg["hardware"]["devices"]
        assert devices, f"{name}: hardware.devices must not be empty"
        for dev_id, dev_def in devices.items():
            assert isinstance(dev_def, dict), (
                f"{name}: device {dev_id!r} must be an object"
            )
            # role: non-empty string.
            assert "role" in dev_def, f"{name}: device {dev_id!r} missing 'role'"
            assert isinstance(dev_def["role"], str) and dev_def["role"], (
                f"{name}: device {dev_id!r}.role must be a non-empty string"
            )
            # vram_mib: real int (not bool — bool is a subclass of int in
            # Python so we have to disambiguate explicitly).
            assert "vram_mib" in dev_def, (
                f"{name}: device {dev_id!r} missing 'vram_mib'"
            )
            assert isinstance(dev_def["vram_mib"], int) and not isinstance(
                dev_def["vram_mib"], bool
            ), (
                f"{name}: device {dev_id!r}.vram_mib must be an integer; "
                f"got {type(dev_def['vram_mib']).__name__}"
            )
            # nvidia_smi_index: real int >= 0.
            assert "nvidia_smi_index" in dev_def, (
                f"{name}: device {dev_id!r} missing 'nvidia_smi_index'"
            )
            nsmi = dev_def["nvidia_smi_index"]
            assert isinstance(nsmi, int) and not isinstance(nsmi, bool), (
                f"{name}: device {dev_id!r}.nvidia_smi_index must be an integer; "
                f"got {type(nsmi).__name__}"
            )
            assert nsmi >= 0, (
                f"{name}: device {dev_id!r}.nvidia_smi_index must be >= 0; got {nsmi}"
            )
