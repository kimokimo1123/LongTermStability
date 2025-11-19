"""CLI entrypoint for the LongTermStability helper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from .config import ProjectConfig
from .fluke8588 import Fluke8588Dmm
from .hp3488a import HP3488A
from .visa_utils import resource_manager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("id", help="Frage die *IDN? beider Geräte ab")

    select = sub.add_parser("select", help="Schaltet einen einzelnen Slot/Kanal durch")
    select.add_argument("--slot", type=int, required=True)
    select.add_argument("--channel", type=int, required=True)

    scan = sub.add_parser("scan", help="Programmiert eine SCAN-Liste nach Karten-Namen")
    scan.add_argument("card", help="Name wie in config.yaml unter multiplexer.cards[].name")

    measure = sub.add_parser("measure", help="Schaltet alle Kanäle einer Karte und liest das DMM aus")
    measure.add_argument("card", help="Kartenname")
    measure.add_argument("--samples", type=int, default=1)

    return parser


def _load_config(path: Path) -> ProjectConfig:
    if not path.exists():
        raise SystemExit(f"Config file {path} not found. Start from config.example.yaml")
    return ProjectConfig.from_file(path)


def _hp_from_config(cfg: ProjectConfig) -> HP3488A:
    return HP3488A(
        resource=cfg.ics.resource_string(),
        timeout_ms=cfg.timeout_ms,
        write_termination=cfg.write_termination,
        read_termination=cfg.read_termination,
    )


def _dmm_from_config(cfg: ProjectConfig) -> Fluke8588Dmm:
    dmm = cfg.ensure_dmm()
    return Fluke8588Dmm(
        resource=dmm.resource,
        timeout_ms=cfg.timeout_ms,
        write_termination=cfg.write_termination,
        read_termination=cfg.read_termination,
        read_function=dmm.read_function,
        digits=dmm.digits,
    )


def _cmd_id(cfg: ProjectConfig) -> None:
    hp = _hp_from_config(cfg)
    rm_backend = cfg.resource_manager
    with resource_manager(rm_backend) as rm:
        hp_id = hp.identify(rm)
        output = {"hp3488a": hp_id}
        if cfg.dmm:
            dmm = _dmm_from_config(cfg)
            output["fluke8588"] = dmm.identify(rm)
        print(json.dumps(output, indent=2))


def _cmd_select(cfg: ProjectConfig, slot: int, channel: int) -> None:
    hp = _hp_from_config(cfg)
    with resource_manager(cfg.resource_manager) as rm:
        hp.close_all(rm)
        hp.open_channel(rm, slot, channel)
        print(f"Selected slot={slot} channel={channel}")


def _cmd_scan(cfg: ProjectConfig, card_name: str) -> None:
    hp = _hp_from_config(cfg)
    channel_specs = list(cfg.iter_channels(card_name))
    with resource_manager(cfg.resource_manager) as rm:
        hp.scan(rm, channel_specs)
        print(f"SCAN programmed: {', '.join(channel_specs)}")


def _cmd_measure(cfg: ProjectConfig, card_name: str, samples: int) -> None:
    hp = _hp_from_config(cfg)
    dmm = _dmm_from_config(cfg)
    channel_specs = list(cfg.iter_channels(card_name))

    rows = []
    with resource_manager(cfg.resource_manager) as rm:
        for channel in channel_specs:
            hp.select(rm, channel)
            for idx in range(samples):
                value = dmm.measure(rm)
                rows.append({"channel": channel, "sample": idx, "value": value})
                print(f"{channel} sample={idx}: {value}")
    print("\nJSON summary:")
    print(json.dumps(rows, indent=2))


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    cfg = _load_config(args.config)
    match args.command:
        case "id":
            _cmd_id(cfg)
        case "select":
            _cmd_select(cfg, args.slot, args.channel)
        case "scan":
            _cmd_scan(cfg, args.card)
        case "measure":
            _cmd_measure(cfg, args.card, args.samples)
        case _:
            parser.error(f"Unsupported command {args.command}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
