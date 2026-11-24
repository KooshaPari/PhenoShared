from pathlib import Path

from scripts.normalize_harbor_trial import normalize


def test_harbor_completed_zero_reward_is_scoreable_baseline():
    job = {"stats": {"n_completed_trials": 1, "n_errored_trials": 0}}
    trial = {
        "trial_name": "headless-terminal__x",
        "config": {
            "task": {"path": "headless-terminal"},
            "agent": {"model_name": "local/lfm25-8b-a1b"},
        },
        "verifier_result": {"rewards": {"reward": 0.0}},
        "exception_info": None,
        "finished_at": "2026-07-16T00:00:00Z",
        "agent_result": {
            "n_input_tokens": 10,
            "n_output_tokens": 20,
            "metadata": {"n_episodes": 2},
        },
    }
    result = normalize(job, trial, job=Path("job"))
    assert result["scoreable"] is True
    assert result["metrics"]["reward"] == 0.0
    assert result["verifier"]["present"] is True


def test_harbor_exception_is_not_scoreable():
    result = normalize(
        {"stats": {"n_completed_trials": 0, "n_errored_trials": 1}},
        {
            "config": {"agent": {"model_name": "local/qwen35-08b"}},
            "exception_info": {"type": "x"},
        },
        job=Path("job"),
    )
    assert result["scoreable"] is False
    assert result["metrics"]["error_count"] == 1


def test_qwen35_harbor_result_requires_desktop_authorization():
    result = normalize(
        {"stats": {"n_completed_trials": 1, "n_errored_trials": 0}},
        {
            "config": {
                "agent": {"model_name": "local/qwen35-08b"},
                "task": {"path": "headless-terminal"},
            },
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
            "started_at": "2026-08-02T23:59:30+00:00",
            "finished_at": "2026-08-03T00:00:00Z",
        },
        job=Path("job"),
    )
    assert result["scoreable"] is False
    assert result["provenance"]["status"] == "blocked"
    assert "authorization" in result["provenance"]["reason"]


def test_qwen35_harbor_result_binds_authorization_manifest():
    authorization = {
        "schema_version": "pheno.desktop-harbor-authorization.v1",
        "window_id": "desktop-test-window",
        "contract_sha256": "a" * 64,
        "canonical_model": "Qwen/Qwen3.5-0.8B",
        "request_model": "local/qwen35-08b",
        "base_url": "http://127.0.0.1:8000",
        "created_at": "2026-08-02T23:59:00+00:00",
    }
    result = normalize(
        {"stats": {"n_completed_trials": 1, "n_errored_trials": 0}},
        {
            "config": {
                "agent": {"model_name": "local/qwen35-08b"},
                "task": {"path": "headless-terminal"},
            },
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
            "started_at": "2026-08-02T23:59:30+00:00",
            "finished_at": "2026-08-03T00:00:00Z",
        },
        authorization=authorization,
        job=Path("job"),
    )
    assert result["scoreable"] is True
    assert result["provenance"]["status"] == "bound"
    assert result["provenance"]["window_id"] == "desktop-test-window"


def test_qwen35_harbor_result_rejects_wrong_authorized_model():
    authorization = {
        "schema_version": "pheno.desktop-harbor-authorization.v1",
        "window_id": "desktop-test-window",
        "contract_sha256": "a" * 64,
        "canonical_model": "Qwen/Qwen2.5-0.5B",
        "request_model": "local/qwen35-08b",
        "base_url": "http://127.0.0.1:8000",
    }
    result = normalize(
        {"stats": {"n_completed_trials": 1, "n_errored_trials": 0}},
        {
            "config": {
                "agent": {"model_name": "local/qwen35-08b"},
                "task": {"path": "headless-terminal"},
            },
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
            "finished_at": "2026-08-03T00:00:00Z",
        },
        authorization=authorization,
        job=Path("job"),
    )
    assert result["scoreable"] is False
    assert result["provenance"]["status"] == "blocked"


def test_qwen35_harbor_result_rejects_stale_authorization_manifest():
    authorization = {
        "schema_version": "pheno.desktop-harbor-authorization.v1",
        "window_id": "desktop-test-window",
        "contract_sha256": "a" * 64,
        "canonical_model": "Qwen/Qwen3.5-0.8B",
        "request_model": "local/qwen35-08b",
        "base_url": "http://127.0.0.1:8000",
        "created_at": "2026-08-03T00:01:00+00:00",
    }
    result = normalize(
        {"stats": {"n_completed_trials": 1, "n_errored_trials": 0}},
        {
            "config": {
                "agent": {"model_name": "local/qwen35-08b"},
                "task": {"path": "headless-terminal"},
            },
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
            "started_at": "2026-08-03T00:00:00+00:00",
            "finished_at": "2026-08-03T00:02:00+00:00",
        },
        authorization=authorization,
        job=Path("job"),
    )
    assert result["scoreable"] is False
    assert result["provenance"]["status"] == "blocked"
    assert "stale" in result["provenance"]["reason"]
