#!/usr/bin/env python3
"""Build deterministic provenance manifests for publish-ready releases."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "releases.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    output = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=index,codec_name,codec_type,width,height,pix_fmt,r_frame_rate,sample_rate,channels:format=duration,size,bit_rate",
            "-of", "json", str(path),
        ],
        text=True,
        encoding="utf-8",
    )
    return json.loads(output)


def measure_loudness(path: Path) -> dict[str, float]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json",
            "-f", "null", os.devnull,
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
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for release in config["releases"]:
        folder = ROOT / "publishing" / "ready" / release["folder"]
        provenance = folder / "provenance"
        final = folder / f"{release['file_title']}.mp4"
        cover = folder / f"{release['file_title']}_封面.jpg"
        card = folder / f"{release['file_title']}_投稿卡.txt"
        captions = provenance / "captions.ass"
        segments = [ROOT / item for item in release["source_segments"]]
        prompts = [ROOT / item for item in release["prompt_files"]]
        required = [final, cover, card, captions, *segments, *prompts]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError("Missing release files:\n" + "\n".join(missing))

        jobs = release.get("generation_jobs", [])
        segment_records = []
        for index, segment in enumerate(segments):
            job = jobs[index] if index < len(jobs) else {"segment": index + 1}
            segment_records.append({**job, "media": {**file_record(segment), "probe": probe(segment)}})

        manifest = {
            "release_id": release["id"],
            "work_id": release["work_id"],
            "game": release["game"],
            "incentive_plan": release["incentive_plan"],
            "eligibility": release["eligibility"],
            "campaign_tag_allowed": release["campaign_tag_allowed"],
            "title": release["display_title"],
            "folder": release["folder"],
            "generation": {
                "engine": "MiniMax H3 local Studio",
                "segments": segment_records,
                "prompts": [file_record(path) for path in prompts],
            },
            "finishing": {
                "script": "scripts/render_releases.ps1",
                "canvas": [1080, 1920],
                "video": "H.264 High, CRF 18, yuv420p, 24 fps, faststart",
                "audio": "AAC stereo 48 kHz 192 kbps; EBU R128 target -16 LUFS with -2.5 dBTP headroom and a 0.82 non-normalizing peak limiter",
                "captions": file_record(captions),
            },
            "deliverables": {
                "video": {**file_record(final), "probe": probe(final), "measured_loudness": measure_loudness(final)},
                "cover": file_record(cover),
                "posting_card": file_record(card),
            },
            "disclosure": "AI生成 / AI辅助制作；本地MiniMax H3生成，确定性字幕与FFmpeg后期。",
        }
        provenance.mkdir(parents=True, exist_ok=True)
        target = provenance / "manifest.json"
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
