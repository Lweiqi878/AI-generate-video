#!/usr/bin/env python3
"""Build posting cards and the concise upload queue from data/releases.json."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "releases.json"
PUBLISHING = ROOT / "publishing"


def post_block(platform: str, post: dict) -> str:
    tags = " ".join(f"#{tag}" for tag in post["tags"])
    return f"""【{platform}标题】
{post['title']}

【{platform}正文】
{post['description']}

【{platform}标签】
{tags}
"""


def posting_card(release: dict) -> str:
    variants = release.get("platform_posts")
    if variants:
        body = "\n".join(post_block(platform, post) for platform, post in variants.items())
    else:
        body = post_block(release["platform"], release["posting"])
    image_workflow = (
        "角色、场景与首中尾关键帧由 Image2 生成；本地 MiniMax H3 仅完成首尾帧动态；"
        if release.get("image2_assets")
        else "画面与音频由本地 MiniMax H3 生成；"
    )
    return f"""{body}
【活动处理】
{release['posting']['campaign_note']}

【AI标识】
AI生成 / AI辅助制作；{image_workflow}人工完成选题、叙事、字幕、声音与剪辑。

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
        "运行 `./投稿准备.ps1`，选择作品与平台后会自动校验、复制该平台文案并在资源管理器中定位成片；加 `-OpenUploadPage` 可打开对应官方上传页。",
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
        "活动名称仅用于排产与归档。带“资格待核验”或“无激励任务关联”的作品，在账号内出现正式任务卡且规则明确接受生成式AI前，只作普通AI标识内容发布。",
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
