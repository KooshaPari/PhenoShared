"""cr_roster: static catalog of code-review providers (SP1)."""
from cr_roster.loader import RosterError, load_providers

__all__ = ["load_providers", "RosterError"]
