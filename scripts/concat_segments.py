#!/usr/bin/env python3
"""Concatenate H3 segments into a normalized vertical MP4.

Requires ffmpeg and ffprobe in PATH. Inputs may be listed explicitly or discovered
from a directory with --dir. The script re-encodes to a consistent 24 fps H.264/AAC
stream, so segments with small codec/container differences can still be joined.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--dir", type=Path, help="Discover *.mp4 in this directory")
    parser.add_argument("--glob", default="*.mp4", help="Pattern used with --dir")
    parser.add_argument("-o", "--output", type=Path, default=Path("final_60s.mp4"))
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=1366)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--audio", action="store_true", help="Keep and normalize audio; omit for video-only concat")
    args = parser.parse_args()

    inputs = list(args.inputs)
    if args.dir:
        inputs.extend(sorted(args.dir.glob(args.glob)))
    seen: set[Path] = set()
    inputs = [p.resolve() for p in inputs if not (p.resolve() in seen or seen.add(p.resolve()))]
    if len(inputs) < 2:
        parser.error("Provide at least two input segments")
    missing = [str(p) for p in inputs if not p.is_file()]
    if missing:
        parser.error("Missing input files: " + ", ".join(missing))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="h3_concat_") as tmp:
        tmpdir = Path(tmp)
        normalized: list[Path] = []
        vf = (
            f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
            f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuv420p"
        )
        for idx, src in enumerate(inputs, 1):
            dst = tmpdir / f"segment_{idx:02d}.mp4"
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf),
                "-movflags", "+faststart",
            ]
            if args.audio:
                cmd += ["-af", "loudnorm=I=-16:LRA=11:TP=-1.5", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
            else:
                cmd += ["-an"]
            cmd += [str(dst)]
            run(cmd)
            normalized.append(dst)

        concat_file = tmpdir / "concat.txt"
        concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in normalized), encoding="utf-8")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-movflags", "+faststart", str(args.output),
        ])

    print(f"Final video written: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
