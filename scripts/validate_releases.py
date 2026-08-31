#!/usr/bin/env python3
"""Validate publish-ready folder naming, media format, provenance and campaign guards."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,codec_type,width,height,pix_fmt,r_frame_rate,sample_rate,channels:format=duration", "-of", "json", str(path)],
        text=True,
        encoding="utf-8",
    ))


def filter_report(path: Path, kind: str, expression: str) -> str:
    stream_flag = "-af" if kind == "audio" else "-vf"
    disable_flag = "-vn" if kind == "audio" else "-an"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), stream_flag, expression, disable_flag, "-f", "null", os.devnull],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stderr


def loudness(path: Path) -> tuple[float, float]:
    report = filter_report(path, "audio", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json")
    match = re.search(r'\{\s*"input_i".*?\}', report, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not parse loudness report for {path}")
    values = json.loads(match.group(0))
    return float(values["input_i"]), float(values["input_tp"])


def main() -> int:
    config = json.loads((ROOT / "data" / "releases.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    seen: set[str] = set()
    summaries: list[str] = []
    for release in config["releases"]:
        expected_folder = f"{release['game']}__{release['plan_folder']}__{release['file_title']}"
        if release["folder"] != expected_folder:
            errors.append(f"{release['id']}: folder does not match pattern")
        if release["folder"] in seen:
            errors.append(f"{release['id']}: duplicate folder")
        seen.add(release["folder"])
        if "待核验" in release["eligibility"] and release["campaign_tag_allowed"]:
            errors.append(f"{release['id']}: unverified campaign cannot enable campaign tag")

        folder = ROOT / "publishing" / "ready" / release["folder"]
        video = folder / f"{release['file_title']}.mp4"
        cover = folder / f"{release['file_title']}_封面.jpg"
        card = folder / f"{release['file_title']}_投稿卡.txt"
        provenance = folder / "provenance"
        expected_top = {video.name, cover.name, card.name, "provenance"}
        if not folder.is_dir():
            errors.append(f"{release['id']}: missing release folder")
            continue
        actual_top = {item.name for item in folder.iterdir()}
        if actual_top != expected_top:
            errors.append(f"{release['id']}: top level must contain only video, cover, posting card and provenance; got {sorted(actual_top)}")
        for path in (video, cover, card, provenance / "captions.ass", provenance / "manifest.json"):
            if not path.exists():
                errors.append(f"{release['id']}: missing {path.relative_to(ROOT)}")
        if not video.is_file():
            continue

        media = probe(video)
        streams = media.get("streams", [])
        v = next((item for item in streams if item.get("codec_type") == "video"), {})
        a = next((item for item in streams if item.get("codec_type") == "audio"), {})
        if (v.get("codec_name"), v.get("width"), v.get("height"), v.get("pix_fmt"), v.get("r_frame_rate")) != ("h264", 1080, 1920, "yuv420p", "24/1"):
            errors.append(f"{release['id']}: unexpected video stream {v}")
        if (a.get("codec_name"), a.get("sample_rate"), a.get("channels")) != ("aac", "48000", 2):
            errors.append(f"{release['id']}: unexpected audio stream {a}")
        duration = float(media.get("format", {}).get("duration", 0))
        if not 9.0 <= duration <= 35.0:
            errors.append(f"{release['id']}: unexpected duration {duration:.3f}s")
        black = filter_report(video, "video", "blackdetect=d=0.25:pic_th=0.98:pix_th=0.03").count("black_start")
        freeze = filter_report(video, "video", "freezedetect=n=-60dB:d=2.0").count("freeze_start")
        silence = filter_report(video, "audio", "silencedetect=n=-50dB:d=2.0").count("silence_start")
        integrated_lufs, true_peak_dbtp = loudness(video)
        if black:
            errors.append(f"{release['id']}: detected {black} black event(s)")
        if freeze:
            errors.append(f"{release['id']}: detected {freeze} freeze event(s) longer than 2s")
        if silence:
            errors.append(f"{release['id']}: detected {silence} silence event(s) longer than 2s")
        if not -21.0 <= integrated_lufs <= -13.0:
            errors.append(f"{release['id']}: integrated loudness {integrated_lufs:.2f} LUFS outside release guard")
        if true_peak_dbtp > -1.0:
            errors.append(f"{release['id']}: true peak {true_peak_dbtp:.2f} dBTP leaves insufficient transcode headroom")
        summaries.append(
            f"{release['id']}: {duration:.3f}s, {integrated_lufs:.2f} LUFS, {true_peak_dbtp:.2f} dBTP, "
            f"black/freeze/silence={black}/{freeze}/{silence}"
        )

        captions = provenance / "captions.ass"
        if captions.is_file() and "AI生成" not in captions.read_text(encoding="utf-8-sig"):
            errors.append(f"{release['id']}: captions missing persistent AI label")
        manifest_path = provenance / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = manifest.get("deliverables", {}).get("video", {})
            if record.get("sha256") != sha256(video):
                errors.append(f"{release['id']}: manifest video hash mismatch")

    if errors:
        print("Release validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Release validation passed: {len(config['releases'])} publish-ready works")
    for summary in summaries:
        print(f"- {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
