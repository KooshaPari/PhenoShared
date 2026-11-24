from perf.heterogeneous import run_heterogeneous


def test_round_robin_preserves_worker_accounting():
    workers = [{"id": "3090", "base_url": "a"}, {"id": "1080", "base_url": "b"}]

    def caller(worker, task):
        return {
            "elapsed_ms": 10.0,
            "completion_tokens": 5,
            "worker_seen": worker["id"],
            "task": task["id"],
        }

    result = run_heterogeneous(workers, [{"id": str(i)} for i in range(5)], 3, caller)
    assert result["success_count"] == 5
    assert result["worker_assignments"] == {"3090": 3, "1080": 2}
    assert result["by_worker"]["3090"]["tokens"] == 15
    assert result["by_worker"]["1080"]["tokens"] == 10
