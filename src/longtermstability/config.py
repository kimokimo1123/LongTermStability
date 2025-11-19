"""Configuration helpers for the LongTermStability toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Expected top-level mapping in config file")
    return data


@dataclass(slots=True)
class CardConfig:
    """Configuration block for a single 44470A (oder kompatible) Karte."""

    name: str
    slot: int
    channels: List[int] = field(default_factory=list)


@dataclass(slots=True)
class IcsConfig:
    host: str
    gpib_board: int = 0
    gpib_address: int = 26

    def resource_string(self) -> str:
        return f"TCPIP::{self.host}::gpib{self.gpib_board},{self.gpib_address}::INSTR"


@dataclass(slots=True)
class MultiplexerConfig:
    cards: List[CardConfig] = field(default_factory=list)

    def card_by_name(self, name: str) -> CardConfig:
        for card in self.cards:
            if card.name == name:
                return card
        raise KeyError(f"Unknown card '{name}' in configuration")


@dataclass(slots=True)
class DmmConfig:
    resource: str
    read_function: str = "READ?"
    digits: Optional[int] = None


@dataclass(slots=True)
class ProjectConfig:
    """Aggregated configuration for CLI commands."""

    resource_manager: str = "@py"
    timeout_ms: int = 5000
    write_termination: str = "\n"
    read_termination: str = "\n"
    ics: IcsConfig = field(default_factory=lambda: IcsConfig(host="172.16.8.107"))
    multiplexer: MultiplexerConfig = field(default_factory=MultiplexerConfig)
    dmm: Optional[DmmConfig] = None

    @classmethod
    def from_file(cls, path: Path | str) -> "ProjectConfig":
        raw = _read_yaml(Path(path))
        cards = [CardConfig(**entry) for entry in raw.get("multiplexer", {}).get("cards", [])]
        multiplexer = MultiplexerConfig(cards=cards)
        ics = IcsConfig(**raw.get("ics", {}))
        dmm_block = raw.get("dmm")
        dmm = DmmConfig(**dmm_block) if dmm_block else None
        return cls(
            resource_manager=raw.get("resource_manager", "@py"),
            timeout_ms=int(raw.get("timeout_ms", 5000)),
            write_termination=raw.get("write_termination", "\n"),
            read_termination=raw.get("read_termination", "\n"),
            ics=ics,
            multiplexer=multiplexer,
            dmm=dmm,
        )

    def ensure_dmm(self) -> DmmConfig:
        if not self.dmm:
            raise RuntimeError("DMM block missing in configuration")
        return self.dmm

    def iter_channels(self, card_name: str) -> Iterable[str]:
        card = self.multiplexer.card_by_name(card_name)
        for channel in card.channels:
            yield f"{card.slot:1d}{channel:02d}"
