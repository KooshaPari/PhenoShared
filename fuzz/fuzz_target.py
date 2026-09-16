#!/usr/bin/env python3
import sys

import atheris


def TestOneInput(data):
    try:
        text = data.decode("utf-8", errors="ignore")
        _ = text.strip().split()
    except Exception:
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
