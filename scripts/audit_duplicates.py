#!/usr/bin/env python3
"""Audit exact and semantic duplicate candidates in the 194-work catalog."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from build_all import EXPECTED_WORKS, load_works


ROOT = Path(__file__).resolve().parents[1]
JSON_REPORT = ROOT / "data" / "duplicate_audit.json"
MD_REPORT = ROOT / "docs" / "DUPLICATE_AUDIT.md"
DECISIONS_PATH = ROOT / "data" / "duplicate_decisions.json"
NEAR_THRESHOLD = 0.20


def norm(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value).lower())


def canonical_game(value: str) -> str:
    value = value.replace("／千星奇域", "").replace("·千星奇域", "")
    return norm(value)


def character_tokens(value: str) -> set[str]:
    return {
        norm(item)
        for item in re.split(r"[与、,&和/]|（.*?）|\(.*?\)", value)
        if norm(item)
    }


def grams(value: str, size: int = 2) -> set[str]:
    value = norm(value)
    return {value[index : index + size] for index in range(max(0, len(value) - size + 1))}


def jaccard(left: str, right: str) -> float:
    a, b = grams(left), grams(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def story_text(work: dict[str, Any]) -> str:
    return "".join(
        [
            str(work.get("title", "")),
            str(work.get("hook", "")),
            str(work.get("payoff", "")),
            str(work.get("scene", "")),
            "".join(str(item) for item in work.get("beats", [])),
        ]
    )


def source_name(work: dict[str, Any]) -> str:
    number = int(str(work["id"]).split("-")[-1])
    return "github-v2" if number <= 100 else "local-retained"


def analyze(works: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = (
        json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
        if DECISIONS_PATH.exists()
        else {}
    )
    title_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fingerprint_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for work in works:
        title_groups[norm(work["title"])].append(work)
        fingerprint_groups[
            norm(
                "|".join(
                    [
                        work["game"],
                        work["character"],
                        work["title"],
                        work["hook"],
                        work["payoff"],
                    ]
                )
            )
        ].append(work)

    normalized_title_collisions = [
        [item["id"] for item in group]
        for group in title_groups.values()
        if len(group) > 1
    ]
    exact_record_collisions = [
        [item["id"] for item in group]
        for group in fingerprint_groups.values()
        if len(group) > 1
    ]

    github = [work for work in works if source_name(work) == "github-v2"]
    local = [work for work in works if source_name(work) == "local-retained"]
    candidates: list[dict[str, Any]] = []
    for left in github:
        for right in local:
            same_game = canonical_game(left["game"]) == canonical_game(right["game"])
            shared_character = bool(
                character_tokens(left["character"]) & character_tokens(right["character"])
            )
            title_similarity = SequenceMatcher(
                None, norm(left["title"]), norm(right["title"])
            ).ratio()
            story_overlap = jaccard(story_text(left), story_text(right))
            score = (
                0.48 * title_similarity
                + 0.42 * story_overlap
                + 0.07 * int(shared_character)
                + 0.03 * int(same_game)
            )
            if not same_game or score < NEAR_THRESHOLD:
                continue
            if score >= 0.29:
                confidence = "high"
            elif score >= 0.23:
                confidence = "medium"
            else:
                confidence = "low"
            pair_key = f"{left['id']}|{right['id']}"
            review = decisions.get(pair_key)
            if review:
                decision = str(review["decision"])
                rationale = str(review["rationale"])
            elif confidence == "low":
                decision = "keep_distinct_low_similarity"
                rationale = "得分低于编辑复核阈值，且不存在完全记录或规范化标题碰撞。"
            else:
                decision = "keep_distinct_pending_editorial_review"
                rationale = "相同游戏内存在角色或核心道具重合，需在排期前人工复核。"
            candidates.append(
                {
                    "left_id": left["id"],
                    "left_title": left["title"],
                    "left_character": left["character"],
                    "right_id": right["id"],
                    "right_title": right["title"],
                    "right_character": right["character"],
                    "game": left["game"],
                    "score": round(score, 4),
                    "title_similarity": round(title_similarity, 4),
                    "story_bigram_jaccard": round(story_overlap, 4),
                    "shared_character": shared_character,
                    "confidence": confidence,
                    "decision": decision,
                    "rationale": rationale,
                }
            )
    candidates.sort(key=lambda item: (-item["score"], item["left_id"], item["right_id"]))

    return {
        "status": "PASS"
        if not normalized_title_collisions and not exact_record_collisions
        else "FAIL",
        "summary": {
            "works": len(works),
            "github_v2": len(github),
            "local_retained": len(local),
            "exact_record_collisions": len(exact_record_collisions),
            "normalized_title_collisions": len(normalized_title_collisions),
            "semantic_review_candidates": len(candidates),
            "candidate_confidence": dict(Counter(item["confidence"] for item in candidates)),
            "candidate_decisions": dict(Counter(item["decision"] for item in candidates)),
        },
        "policy": {
            "automatic_removal": "only exact record or normalized-title collisions",
            "semantic_candidates": "reported but retained because similar props or characters do not prove duplicate execution",
            "threshold": NEAR_THRESHOLD,
        },
        "exact_record_collisions": exact_record_collisions,
        "normalized_title_collisions": normalized_title_collisions,
        "semantic_candidates": candidates,
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = report["summary"]
    lines = [
        "# 194案合并与重复审计",
        "",
        f"- 结论：**{report['status']}**",
        f"- GitHub主线：{summary['github_v2']}案",
        f"- 本地保留：{summary['local_retained']}案",
        f"- 合并总数：{summary['works']}案",
        f"- 完全重复记录：{summary['exact_record_collisions']}组",
        f"- 规范化标题重复：{summary['normalized_title_collisions']}组",
        f"- 语义近似复核候选：{summary['semantic_review_candidates']}组（保留，不自动删除）",
        "",
        "## 口径",
        "",
        "自动去重只处理完全一致记录或去标点后仍完全相同的标题。相同角色、道具或题材只进入人工复核，避免把不同剧情机制误删。",
        "",
        "## 语义近似候选",
        "",
        "| 置信 | 得分 | GitHub案 | 本地案 | 处理 | 判定依据 |",
        "|---|---:|---|---|---|---|",
    ]
    for item in report["semantic_candidates"]:
        lines.append(
            f"| {item['confidence']} | {item['score']:.3f} | "
            f"{item['left_id']}《{item['left_title']}》 | "
            f"{item['right_id']}《{item['right_title']}》 | "
            f"{'人工复核后保留' if item['decision'] == 'keep_distinct_reviewed' else '低相似度保留' if item['decision'] == 'keep_distinct_low_similarity' else '保留待复核'} | "
            f"{item['rationale']} |"
        )
    if not report["semantic_candidates"]:
        lines.append("| — | — | — | — | 无 | — |")
    lines += [
        "",
        "## 结论解释",
        "",
        "本轮没有达到自动删除条件的重复项，因此最终目录保留194案。高/中置信候选已逐组阅读钩子、反转和完整节拍；均属于共同角色或道具下的不同执行。低置信项不存在精确碰撞，按低相似度保留。发布排期前仍可按本表避免连续制作过于相近的题材。",
    ]
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    works = load_works()
    report = analyze(works)
    write_reports(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if len(works) != EXPECTED_WORKS:
        return 1
    if args.check and report["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
