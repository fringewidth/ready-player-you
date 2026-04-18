#!/usr/bin/env python3
"""Headless Blender sweep runner.

This script is intended to be executed inside Blender's Python runtime.
It currently defines the skeleton for loading a scene, sampling parameter
combinations, and rendering labeled outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import random
import sys
from typing import Iterable


@dataclass(frozen=True)
class RenderSample:
    index: int
    skin_tone: float
    camera_yaw: float
    camera_pitch: float
    camera_distance: float


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _sample_grid(seed: int, count: int) -> Iterable[RenderSample]:
    rng = random.Random(seed)
    for index in range(count):
        yield RenderSample(
            index=index,
            skin_tone=rng.uniform(0.0, 1.0),
            camera_yaw=rng.uniform(-45.0, 45.0),
            camera_pitch=rng.uniform(-15.0, 20.0),
            camera_distance=rng.uniform(1.2, 2.0),
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args((argv or sys.argv[sys.argv.index("--") + 1 :]) if "--" in sys.argv else [])
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    samples = list(_sample_grid(seed=1337, count=10))
    for sample in samples:
        print(sample)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

