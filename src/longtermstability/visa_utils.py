"""Utility wrappers around pyvisa to keep resource handling consistent."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pyvisa


@contextmanager
def resource_manager(backend: str) -> Iterator[pyvisa.ResourceManager]:
    rm = pyvisa.ResourceManager(backend)
    try:
        yield rm
    finally:
        rm.close()


def open_instrument(
    rm: pyvisa.ResourceManager,
    resource: str,
    *,
    timeout_ms: int,
    write_termination: str,
    read_termination: str,
):
    inst = rm.open_resource(resource)
    inst.timeout = timeout_ms
    inst.write_termination = write_termination
    inst.read_termination = read_termination
    return inst
