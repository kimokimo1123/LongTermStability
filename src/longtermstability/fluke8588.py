"""SCPI helper tailored to the Fluke 8588A/8588D series."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .visa_utils import open_instrument


@dataclass
class Fluke8588Dmm:
    resource: str
    timeout_ms: int = 5000
    write_termination: str = "\n"
    read_termination: str = "\n"
    read_function: str = "READ?"
    digits: Optional[int] = None

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

    def measure(self, rm, function: Optional[str] = None) -> float:
        query = function or self.read_function
        if self.digits:
            query = f"{query} {self.digits}"
        with self.open(rm) as inst:
            response = inst.query(query)
        return float(response.strip())
