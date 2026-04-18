#!/usr/bin/env python3
"""Minimal command-driven pilot interface for a prototype Blender scene.

This is intentionally small and disposable. The purpose is to let the user
issue named commands against a working .blend file while we learn what the
scene needs before building the real generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import sys


@dataclass
class PilotState:
    blend_file: Path | None = None
    commands: list[dict[str, Any]] = field(default_factory=list)


def load_state(blend_file: str | None) -> PilotState:
    state = PilotState()
    if blend_file:
        state.blend_file = Path(blend_file)
    return state


def apply_command(state: PilotState, command: dict[str, Any]) -> None:
    state.commands.append(command)
    kind = command.get("type")
    if kind == "set_slider":
        return
    if kind == "set_camera":
        return
    if kind == "set_hdri":
        return
    if kind == "set_asset":
        return
    if kind == "render":
        return
    raise ValueError(f"unknown command type: {kind!r}")


def main(argv: list[str] | None = None) -> int:
    raw = argv or sys.argv[1:]
    if "--" in raw:
        raw = raw[raw.index("--") + 1 :]
    if not raw:
        print("usage: pilot.py -- <commands.json>", file=sys.stderr)
        return 2

    command_file = Path(raw[0])
    data = json.loads(command_file.read_text())
    state = load_state(data.get("blend_file"))
    for command in data.get("commands", []):
        apply_command(state, command)

    print(json.dumps({"blend_file": str(state.blend_file) if state.blend_file else None, "commands": state.commands}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

