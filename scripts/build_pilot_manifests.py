#!/usr/bin/env python3
"""Write reproducible media manifests for the two completed pilot videos."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPECS = [
    {
        "id": "V2-191",
        "slug": "walking-opera",
        "title": "歌剧院下班后开始散步",
        "studio_job_id": "260830-204712-5e5e88",
        "seed": 2026083097,
    },
    {
        "id": "V2-193",
        "slug": "tape-escape",
        "title": "午夜录像带从货架集体越狱",
        "studio_job_id": "260830-204712-51bf35",
        "seed": 2026083099,
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels:format=duration,size,bit_rate",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        encoding="utf-8",
    )
    return json.loads(output)


def measure_loudness(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    match = re.search(r'\{\s*"input_i".*?\}', result.stderr, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not parse loudness report for {path}")
    values = json.loads(match.group(0))
    return {
        "integrated_lufs": float(values["input_i"]),
        "true_peak_dbtp": float(values["input_tp"]),
        "loudness_range_lu": float(values["input_lra"]),
    }


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    for spec in SPECS:
        production = ROOT / "production" / f"{spec['id']}-{spec['slug']}"
        deliverable = ROOT / "deliverables" / f"{spec['id']}-{spec['slug']}"
        raw = production / "raw" / f"{spec['id']}_h3_raw.mp4"
        final = deliverable / f"{spec['id']}_final.mp4"
        cover = deliverable / f"{spec['id']}_cover.jpg"
        prompt = deliverable / "prompt.txt"
        captions = deliverable / "captions.ass"
        for path in (raw, final, cover, prompt, captions):
            if not path.is_file():
                raise FileNotFoundError(path)

        manifest = {
            "work_id": spec["id"],
            "title": spec["title"],
            "generation": {
                "engine": "MiniMax H3 local Studio",
                "studio_job_id": spec["studio_job_id"],
                "mode": "t2v",
                "model": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                "turbo_lora": "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
                "seed": spec["seed"],
                "steps": 8,
                "scheduler": "simple",
                "canvas": [480, 832],
                "frames": 243,
                "fps": 24,
                "requested_seconds": 10,
                "actual_seconds": 10.125,
                "prompt": file_record(prompt),
                "raw_media": {
                    **file_record(raw),
                    "probe": probe(raw),
                    "tracked_in_git": False,
                },
            },
            "finishing": {
                "script": "scripts/render_pilot_videos.ps1",
                "canvas": [1080, 1920],
                "video": "H.264 High, CRF 18, slow preset, yuv420p, faststart",
                "audio": "AAC stereo 48 kHz 192 kbps; EBU R128 target -16 LUFS with -2.0 dBTP encode headroom (peak-limited when necessary)",
                "treatment": "Lanczos upscale/crop, restrained contrast and saturation, mild unsharp, deterministic ASS overlays",
                "captions": file_record(captions),
            },
            "deliverables": {
                "video": {
                    **file_record(final),
                    "probe": probe(final),
                    "measured_loudness": measure_loudness(final),
                },
                "cover": file_record(cover),
            },
            "disclosure": "AI生成 / AI辅助制作；本地MiniMax H3生成，FFmpeg确定性后期。",
        }
        (deliverable / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {deliverable / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
