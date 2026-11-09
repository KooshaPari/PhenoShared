from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterator

import click

_MARKUP_RE = re.compile(r"\[/?[^\]]+\]")


def _strip_markup(message: str) -> str:
    return _MARKUP_RE.sub("", message)


class Console:
    def print(self, message: object = "", *, nl: bool = True) -> None:
        click.echo(_strip_markup(str(message)), nl=nl)

    @contextmanager
    def status(self, message: str) -> Iterator[None]:
        click.echo(_strip_markup(message))
        yield


console = Console()
