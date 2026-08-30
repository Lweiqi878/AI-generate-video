#!/usr/bin/env python3
"""Import the retained local catalog into the canonical V2 JSONL schema.

The importer is intentionally deterministic: the same source file produces the
same four JSONL slates and merge manifest.  It never copies the six explicitly
retired franchises into the merged catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SLATE_DIR = ROOT / "data" / "slates"
MANIFEST_PATH = ROOT / "data" / "merge_manifest.json"
EXCLUDED_GAMES = {"鸣潮", "明日方舟", "崩坏3", "第五人格"}
REMOTE_COUNT = 100
EXPECTED_LOCAL_INPUT = 100
EXPECTED_LOCAL_RETAINED = 94
REMOTE_COMMIT = "2233ffcd5815b3704287ff6acca7f8c9fa7a4101"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def split_short_beats(raw_beats: list[str], old_id: int) -> list[str]:
    text = "；".join(str(item).strip() for item in raw_beats if str(item).strip())
    parts = [part.strip(" 。") for part in re.split(r"[；;]", text) if part.strip(" 。")]
    if len(parts) != 4:
        raise ValueError(
            f"Legacy work {old_id:03d} must resolve to four 10-second beats; "
            f"found {len(parts)}"
        )
    return parts


def extract_dialogue(work: dict[str, Any]) -> str:
    haystack = " ".join(
        [str(work.get("audio", "")), *(str(x) for x in work.get("beats", []))]
    )
    matches = re.findall(r"[“「『](.*?)[”」』]", haystack)
    unique: list[str] = []
    for item in matches:
        item = item.strip()
        if item and item not in unique:
            unique.append(item)
    return "；".join(unique[:2])


def priority_for(value: str) -> str:
    value = str(value).strip().upper()
    if value.startswith("A"):
        return "P0"
    if value.startswith("B"):
        return "P1"
    return "P2"


def risk_for(value: str) -> str:
    value = str(value)
    if "高" in value:
        return "high"
    if "中" in value:
        return "medium"
    return "low"


def convert_work(work: dict[str, Any], new_number: int) -> dict[str, Any]:
    mode = str(work["mode"])
    if mode == "10s":
        beats = split_short_beats(list(work.get("beats", [])), int(work["id"]))
    elif mode == "60s":
        beats = [str(item).strip() for item in work.get("beats", [])]
        if len(beats) != 6:
            raise ValueError(
                f"Legacy work {int(work['id']):03d} must contain six 60-second segments"
            )
    else:
        raise ValueError(f"Legacy work {work['id']} has unsupported mode {mode!r}")

    tags = [str(item).strip() for item in work.get("tags", []) if str(item).strip()]
    for fallback in ("AI动画", "MiniMaxH3", "AI生成内容"):
        if len(tags) >= 3:
            break
        if fallback not in tags:
            tags.append(fallback)

    query = str(work.get("official_reference_query") or "").strip()
    if not query:
        query = "使用自制或明确授权的原创场景参考图，不使用Logo、UI或第三方未授权素材"

    return {
        "id": f"V2-{new_number:03d}",
        "game": str(work["game"]),
        "character": str(work["character"]),
        "mode": mode,
        "title": str(work["title"]),
        "form": str(work["transformation"]),
        "scene": str(work["scene"]),
        "hook": str(work["hook"]),
        "beats": beats,
        "payoff": str(work["synopsis"]),
        "dialogue": extract_dialogue(work),
        "sound": str(work["audio"]),
        "loop": f"按原节拍收束并保留清晰末帧：{beats[-1]}",
        "camera": (
            f"{work.get('aspect_ratio', '9:16')}竖屏，{work.get('fps', 24)}fps，"
            f"稳定单镜头；{work.get('visual_style', '电影级微缩动画质感')}"
        ),
        "priority": priority_for(str(work.get("pilot_tier", ""))),
        "risk": risk_for(str(work.get("production_complexity", ""))),
        "tags": tags,
        "r1_query": query,
        "qc": (
            f"从本地旧目录第{int(work['id']):03d}条迁入；保留原题名、角色、"
            "场景、钩子、剧情节拍、声音与合规边界，并转换为统一V2字段。"
        ),
    }


def write_slates(converted: list[dict[str, Any]]) -> list[str]:
    filenames: list[str] = []
    for offset in range(0, len(converted), 25):
        chunk = converted[offset : offset + 25]
        start = chunk[0]["id"]
        end = chunk[-1]["id"]
        volume = 5 + offset // 25
        filename = f"{volume:02d}_works_{start}_{end}.jsonl"
        payload = "\n".join(
            json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in chunk
        ) + "\n"
        (SLATE_DIR / filename).write_text(payload, encoding="utf-8")
        filenames.append(f"data/slates/{filename}")
    return filenames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    raw = source.read_bytes()
    works = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(works, list) or len(works) != EXPECTED_LOCAL_INPUT:
        raise ValueError(
            f"Expected {EXPECTED_LOCAL_INPUT} legacy works, found "
            f"{len(works) if isinstance(works, list) else 'non-list'}"
        )

    excluded = [item for item in works if item.get("game") in EXCLUDED_GAMES]
    retained = [item for item in works if item.get("game") not in EXCLUDED_GAMES]
    if len(retained) != EXPECTED_LOCAL_RETAINED:
        raise ValueError(
            f"Expected {EXPECTED_LOCAL_RETAINED} retained works, found {len(retained)}"
        )

    converted = [
        convert_work(item, REMOTE_COUNT + index)
        for index, item in enumerate(retained, start=1)
    ]
    filenames = write_slates(converted)

    mapping = []
    for old, new in zip(retained, converted, strict=True):
        mapping.append(
            {
                "new_id": new["id"],
                "legacy_id": int(old["id"]),
                "game": old["game"],
                "character": old["character"],
                "title": old["title"],
                "legacy_record_sha256": sha256_bytes(canonical_json(old)),
            }
        )

    manifest = {
        "policy": {
            "expected_merged_count": REMOTE_COUNT + EXPECTED_LOCAL_RETAINED,
            "excluded_games": sorted(EXCLUDED_GAMES),
            "deduplication": "exact and normalized title collisions fail validation; semantic candidates are reported for review",
        },
        "github_source": {
            "repository": "https://github.com/Lweiqi878/AI-generate-video",
            "commit": REMOTE_COMMIT,
            "works": REMOTE_COUNT,
            "id_range": ["V2-001", "V2-100"],
        },
        "local_source": {
            "filename": source.name,
            "sha256": sha256_bytes(raw),
            "input_works": len(works),
            "retained_works": len(retained),
            "excluded_works": [
                {
                    "legacy_id": int(item["id"]),
                    "game": item["game"],
                    "character": item["character"],
                    "title": item["title"],
                }
                for item in excluded
            ],
            "generated_slates": filenames,
        },
        "result": {
            "works": REMOTE_COUNT + len(converted),
            "id_range": ["V2-001", f"V2-{REMOTE_COUNT + len(converted):03d}"],
            "legacy_mapping": mapping,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Imported {len(converted)} retained local works; excluded {len(excluded)}; "
        f"merged target is {REMOTE_COUNT + len(converted)} works."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
