#!/usr/bin/env python3
"""Hilfsskript zum Durchtesten aller konfigurierten Multiplexer-Kanäle."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from longtermstability.config import ProjectConfig
from longtermstability.fluke8588 import Fluke8588Dmm
from longtermstability.hp3488a import HP3488A
from longtermstability.visa_utils import resource_manager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument(
        "--card",
        dest="cards",
        action="append",
        help="Name der Karte aus config.multiplexer.cards[].name (mehrfach möglich)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Anzahl Messwerte pro Kanal (Standard: 1)",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=0,
        help="Wartezeit nach dem Schalten eines Kanals bevor gemessen wird",
    )
    parser.add_argument(
        "--no-measure",
        action="store_true",
        help="Nur schalten, keine Messung am DMM durchführen",
    )
    parser.add_argument(
        "--test-name",
        default="channel_sweep",
        help="Name des Tests (wird in der CSV gespeichert)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Desktop",
        help="Ablagepfad für die CSV-Datei (Standard: ~/Desktop)",
    )
    return parser


def _load_config(path: Path) -> ProjectConfig:
    if not path.exists():
        raise SystemExit(f"Konfiguration {path} nicht gefunden. Kopiere config.example.yaml.")
    return ProjectConfig.from_file(path)


def _hp_from_config(cfg: ProjectConfig) -> HP3488A:
    return HP3488A(
        resource=cfg.ics.resource_string(),
        timeout_ms=cfg.timeout_ms,
        write_termination=cfg.write_termination,
        read_termination=cfg.read_termination,
    )


def _dmm_from_config(cfg: ProjectConfig) -> Fluke8588Dmm:
    if not cfg.dmm:
        raise RuntimeError("Keine DMM-Konfiguration vorhanden. Verwende --no-measure.")
    dmm = cfg.dmm
    return Fluke8588Dmm(
        resource=dmm.resource,
        timeout_ms=cfg.timeout_ms,
        write_termination=cfg.write_termination,
        read_termination=cfg.read_termination,
        read_function=dmm.read_function,
        digits=dmm.digits,
    )


def _determine_cards(cfg: ProjectConfig, requested: Optional[List[str]]) -> List[str]:
    if requested:
        return requested
    default_cards = []
    existing = {card.name for card in cfg.multiplexer.cards}
    for candidate in ["voltage_output", "thermistors"]:
        if candidate in existing:
            default_cards.append(candidate)
    if not default_cards:
        raise SystemExit(
            "Keine Karten gefunden. Definiere multiplexer.cards in config.yaml oder nutze --card."
        )
    return default_cards


def _iterate_channels(cfg: ProjectConfig, card_name: str) -> Iterable[str]:
    try:
        return list(cfg.iter_channels(card_name))
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc


def _run_card(
    cfg: ProjectConfig,
    hp: HP3488A,
    dmm: Optional[Fluke8588Dmm],
    card_name: str,
    samples: int,
    settle_ms: int,
) -> list[dict]:
    channel_specs = _iterate_channels(cfg, card_name)
    rows: list[dict] = []
    settle_s = settle_ms / 1000 if settle_ms else 0

    with resource_manager(cfg.resource_manager) as rm:
        for channel in channel_specs:
            hp.select(rm, channel)
            if settle_s:
                time.sleep(settle_s)
            for sample in range(samples):
                recorded_at = datetime.now()
                if dmm:
                    value = dmm.measure(rm)
                    rows.append(
                        {
                            "card": card_name,
                            "channel": channel,
                            "sample": sample,
                            "value": value,
                            "recorded_at": recorded_at,
                        }
                    )
                    print(f"{card_name}:{channel} sample={sample} -> {value}")
                else:
                    rows.append(
                        {
                            "card": card_name,
                            "channel": channel,
                            "sample": sample,
                            "recorded_at": recorded_at,
                        }
                    )
                    print(f"{card_name}:{channel} sample={sample} geschaltet")
    return rows


def _write_csv(rows: list[dict], test_name: str, output_dir: Path) -> Path:
    if not rows:
        raise SystemExit("Keine Daten vorhanden – CSV wird nicht erzeugt.")

    timestamp = datetime.now()
    filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{test_name}.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / filename

    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Datum", "Uhrzeit", "Testname", "Karte", "Kanal", "Sample", "Wert"])
        for row in rows:
            recorded_at: datetime = row.get("recorded_at", datetime.now())
            writer.writerow(
                [
                    recorded_at.strftime("%Y-%m-%d"),
                    recorded_at.strftime("%H:%M:%S"),
                    test_name,
                    row.get("card", ""),
                    row.get("channel", ""),
                    row.get("sample", ""),
                    row.get("value", ""),
                ]
            )

    print(f"CSV gespeichert: {dest}")
    return dest


def main() -> int:
    args = _build_parser().parse_args()
    cfg = _load_config(args.config)
    hp = _hp_from_config(cfg)
    dmm: Optional[Fluke8588Dmm] = None
    if not args.no_measure:
        try:
            dmm = _dmm_from_config(cfg)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc

    cards = _determine_cards(cfg, args.cards)
    results: list[dict] = []
    for card in cards:
        results.extend(_run_card(cfg, hp, dmm, card, args.samples, args.settle_ms))

    _write_csv(results, args.test_name, args.output_dir)
    print("\nJSON summary:")
    print(json.dumps(results, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
