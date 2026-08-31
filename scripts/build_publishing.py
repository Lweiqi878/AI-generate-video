#!/usr/bin/env python3
"""Build posting cards and the concise upload queue from data/releases.json."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "releases.json"
PUBLISHING = ROOT / "publishing"


def posting_card(release: dict) -> str:
    tags = " ".join(f"#{tag}" for tag in release["posting"]["tags"])
    return f"""【投稿标题】
{release['posting']['title']}

【投稿简介】
{release['posting']['description']}

【建议标签】
{tags}

【活动处理】
{release['posting']['campaign_note']}

【AI标识】
AI生成 / AI辅助制作；本地 MiniMax H3 生成，人工完成叙事设计、连续镜头衔接、字幕与剪辑。

【上传文件】
视频：{release['file_title']}.mp4
封面：{release['file_title']}_封面.jpg
"""


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = []
    readme = [
        "# 发布中心",
        "",
        "最终投稿只进入 `ready/`。每个作品顶层只有成片、封面和投稿卡；提示词、字幕、生成参数与哈希统一放在 `provenance/`。",
        "",
        "运行 `./投稿准备.ps1`，选择作品后会自动校验、复制投稿卡并在资源管理器中定位成片。",
        "",
        "| ID | 游戏/分类 | 激励计划 | 成片 | 活动状态 |",
        "|---|---|---|---|---|",
    ]
    for release in config["releases"]:
        folder = PUBLISHING / "ready" / release["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        card = folder / f"{release['file_title']}_投稿卡.txt"
        card.write_text(posting_card(release), encoding="utf-8")
        video_link = f"ready/{release['folder']}/{release['file_title']}.mp4"
        readme.append(
            f"| {release['id']} | {release['game']} | {release['incentive_plan']} | "
            f"[{release['display_title']}]({video_link}) | {release['eligibility']} |"
        )
        rows.append(
            f"| {release['id']} | {release['posting']['title']} | {release['platform']} | "
            f"{'可关联' if release['campaign_tag_allowed'] else '暂不关联活动话题'} | "
            f"`{release['folder']}` |"
        )

    readme.extend([
        "",
        "活动名称仅用于排产与归档。带“资格待核验”的作品，在确认当期规则明确接受生成式AI前，只作普通AI标识内容发布。",
        "",
    ])
    (PUBLISHING / "README.md").write_text("\n".join(readme), encoding="utf-8")
    queue = [
        "# 上传队列",
        "",
        "| ID | 投稿标题 | 平台 | 活动话题 | 文件夹 |",
        "|---|---|---|---|---|",
        *rows,
        "",
    ]
    (PUBLISHING / "UPLOAD_QUEUE.md").write_text("\n".join(queue), encoding="utf-8")
    print(f"Built {len(config['releases'])} posting cards and upload queue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
