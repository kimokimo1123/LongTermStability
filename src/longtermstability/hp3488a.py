"""High level helper for the HP 3488A switch/measure unit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .visa_utils import open_instrument


@dataclass
class HP3488A:
    """Wraps a VISA instrument representing the HP 3488A."""

    resource: str
    timeout_ms: int = 5000
    write_termination: str = "\n"
    read_termination: str = "\n"

    def open(self, rm):  # type: ignore[override]
        return open_instrument(
            rm,
            self.resource,
            timeout_ms=self.timeout_ms,
            write_termination=self.write_termination,
            read_termination=self.read_termination,
        )

    def identify(self, rm) -> str:
        with self.open(rm) as inst:
            return inst.query("*IDN?").strip()

    @staticmethod
    def _format_channel(slot: int, channel: int) -> str:
        return f"{slot}{channel:02d}"

    def close_all(self, rm) -> None:
        with self.open(rm) as inst:
            inst.write("CLOSE ALL")

    def open_channel(self, rm, slot: int, channel: int) -> None:
        with self.open(rm) as inst:
            inst.write(f"OPEN {self._format_channel(slot, channel)}")

    def close_channel(self, rm, slot: int, channel: int) -> None:
        with self.open(rm) as inst:
            inst.write(f"CLOSE {self._format_channel(slot, channel)}")

    def select(self, rm, channel_spec: str) -> None:
        with self.open(rm) as inst:
            inst.write(f"CLOSE {channel_spec}")

    def scan(self, rm, channel_specs: Sequence[str]) -> None:
        with self.open(rm) as inst:
            joined = ",".join(channel_specs)
            inst.write(f"SCAN {joined}")

    def read_state(self, rm) -> str:
        with self.open(rm) as inst:
            return inst.query("LIST?").strip()

    def iterate(self, rm, channel_specs: Iterable[str]):
        with self.open(rm) as inst:
            for channel in channel_specs:
                inst.write(f"CLOSE {channel}")
                yield channel
