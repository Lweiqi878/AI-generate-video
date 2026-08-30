#!/usr/bin/env python3
"""Extract a stable last frame from an H3 segment for use as R4.

Requires ffmpeg in PATH. The default seeks 0.08 seconds before the encoded end to
avoid selecting a duplicated black/end frame introduced by some containers.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Input H3 segment")
    parser.add_argument("output", nargs="?", type=Path, help="Output PNG; defaults beside input")
    parser.add_argument("--offset", type=float, default=0.08, help="Seconds before file end")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input does not exist: {args.input}")
    output = args.output or args.input.with_name(args.input.stem + "_R4.png")
    output.parent.mkdir(parents=True, exist_ok=True)

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-sseof", f"-{max(args.offset, 0.01):.3f}", "-i", str(args.input),
        "-frames:v", "1", "-vf", "format=rgb24", str(output),
    ])
    print(f"R4 written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
