"""Run Harbor after the repository launcher has validated Podman.

Harbor 0.18 hard-codes a 10-second host ``docker info`` preflight. The
Podman-machine Docker API on this Windows host can take longer to wake, so the
PowerShell launcher performs the bounded check first and this shim bypasses
only Harbor's duplicate preflight. Container creation and all later Docker API
calls remain unchanged.
"""

from __future__ import annotations

from harbor.cli.main import app
from harbor.environments.docker.docker import DockerEnvironment


def _validated_by_launcher(cls: type[DockerEnvironment]) -> None:
    """The parent launcher already performed the longer Podman gate."""


DockerEnvironment.preflight = classmethod(_validated_by_launcher)

_run_compose_command = DockerEnvironment._run_docker_compose_command


async def _podman_compose_compat(self, command, *args, **kwargs):
    """Avoid Compose ``--wait`` hangs on Podman services without healthchecks."""

    if command[:3] == ["up", "--detach", "--wait"]:
        command = ["up", "--detach", *command[3:]]
    return await _run_compose_command(self, command, *args, **kwargs)


DockerEnvironment._run_docker_compose_command = _podman_compose_compat


if __name__ == "__main__":
    app()
