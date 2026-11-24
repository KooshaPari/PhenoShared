"""Secondary harness CLI commands kept outside the evidence runner."""

from __future__ import annotations

from pathlib import Path


def cmd_teammates_list(agents_dir: str) -> None:
    from harness import TeammateRegistry

    registry = TeammateRegistry(agents_dir=Path(agents_dir))
    teammates = registry.discover()
    if not teammates:
        print("No teammates found")
        return
    print(f"Found {len(teammates)} teammates:\n")
    for teammate in teammates.values():
        print(f"  {teammate.id}: {teammate.name} ({teammate.role})")
        print(f"    {teammate.description[:60]}...")


def cmd_teammates_delegate(teammate_id: str, task: str, timeout: int, profile: str) -> None:
    import asyncio

    from harness import (
        CodexExecutor,
        DelegationProtocol,
        DelegationRequest,
        Priority,
        TeammateRegistry,
    )

    async def run() -> None:
        registry = TeammateRegistry()
        registry.discover()
        teammate = registry.get(teammate_id)
        if not teammate:
            print(f"Teammate not found: {teammate_id}")
            return
        request = DelegationRequest(
            teammate_id=teammate_id,
            task_description=task,
            priority=Priority.NORMAL,
            timeout_seconds=timeout,
        )
        result = await DelegationProtocol().delegate(request, CodexExecutor(profile=profile))
        print(f"Delegation: {result.delegation_id}")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_ms}ms")
        if result.result:
            print(f"Result: {result.result[:200]}...")
        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(run())


def cmd_teammates_status(delegation_id: str) -> None:
    from harness import DelegationProtocol

    result = DelegationProtocol().get_status(delegation_id)
    if result:
        print(f"Delegation: {result.delegation_id}")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_ms}ms")
    else:
        print(f"Delegation not found: {delegation_id}")


def cmd_scaling_status() -> None:
    from harness import DynamicLimitController, ResourceSampler

    snapshot = ResourceSampler().sample()
    controller = DynamicLimitController()
    print("Resource Status:")
    print(f"  CPU: {snapshot.cpu_percent:.1f}%")
    print(
        f"  Memory: {snapshot.memory_percent:.1f}% ({snapshot.memory_available_mb:.0f}MB available)"
    )
    print(f"  FDs: {snapshot.fd_count}/{snapshot.fd_limit}")
    print(f"  Load: {snapshot.load_avg:.2f}")
    print(f"\nDynamic Limit: {controller.current_limit}")
    print(f"State: {controller._state}")


def cmd_cache_stats() -> None:
    from harness import L1Cache

    stats = L1Cache().stats
    print("L1 Cache Stats:")
    print(f"  Hits: {stats.hits}")
    print(f"  Misses: {stats.misses}")
    print(f"  Hit Rate: {stats.hit_rate:.1%}")


def cmd_cache_clear() -> None:
    from harness import L1Cache, L2Cache

    L1Cache().clear()
    print("L1 cache cleared")
    L2Cache().clear()
    print("L2 cache cleared")
