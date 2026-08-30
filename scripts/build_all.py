#!/usr/bin/env python3
"""Compile the 100-work slate into Image 2 prompts, MiniMax H3 Ref2VA packs,
CSV manifests, JSON, Markdown and a self-contained offline browser.

No third-party Python packages are required.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SLATE_DIR = ROOT / "data" / "slates"
OUT = ROOT / "generated"
EXCLUDED = {"鸣潮", "明日方舟", "崩坏3", "第五人格"}
REQUIRED = {
    "id", "game", "character", "mode", "title", "form", "scene", "hook",
    "beats", "payoff", "dialogue", "sound", "loop", "camera", "priority",
    "risk", "tags", "r1_query", "qc",
}


def load_works() -> list[dict[str, Any]]:
    works: list[dict[str, Any]] = []
    paths = sorted(SLATE_DIR.glob("*.jsonl"))
    if not paths:
        raise FileNotFoundError(f"No JSONL slate found under {SLATE_DIR}")
    for path in paths:
        with path.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
                item["_source"] = str(path.relative_to(ROOT)).replace("\\", "/")
                item["_source_line"] = line_no
                works.append(item)
    works.sort(key=lambda x: x["id"])
    return works


def validate_works(works: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(works) != 100:
        errors.append(f"Expected exactly 100 works, found {len(works)}")

    ids = [w.get("id") for w in works]
    duplicates = [k for k, v in Counter(ids).items() if v > 1]
    if duplicates:
        errors.append(f"Duplicate ids: {duplicates}")

    expected_ids = [f"V2-{i:03d}" for i in range(1, 101)]
    if ids != expected_ids:
        missing = sorted(set(expected_ids) - set(ids))
        extra = sorted(set(ids) - set(expected_ids))
        errors.append(f"ID sequence mismatch; missing={missing}, extra={extra}")

    for w in works:
        where = f"{w.get('_source', '?')}:{w.get('_source_line', '?')}"
        missing_fields = sorted(REQUIRED - set(w))
        if missing_fields:
            errors.append(f"{where} missing fields: {missing_fields}")
            continue
        if w["mode"] not in {"10s", "60s"}:
            errors.append(f"{w['id']}: invalid mode {w['mode']!r}")
        expected_beats = 4 if w["mode"] == "10s" else 6
        if not isinstance(w["beats"], list) or len(w["beats"]) != expected_beats:
            errors.append(f"{w['id']}: expected {expected_beats} beats, found {len(w.get('beats', []))}")
        if w["priority"] not in {"P0", "P1", "P2"}:
            errors.append(f"{w['id']}: invalid priority {w['priority']!r}")
        if w["risk"] not in {"low", "medium", "high"}:
            errors.append(f"{w['id']}: invalid risk {w['risk']!r}")
        if any(name == w["game"] for name in EXCLUDED):
            errors.append(f"{w['id']}: excluded franchise present: {w['game']}")
        if not isinstance(w["tags"], list) or len(w["tags"]) < 3:
            errors.append(f"{w['id']}: at least 3 tags required")
    return errors


def slug(text: str, limit: int = 52) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "-", text).strip("-")
    return text[:limit] or "work"


def segment_count(work: dict[str, Any]) -> int:
    return 1 if work["mode"] == "10s" else 6


def input_manifest(segment_no: int) -> str:
    lines = [
        "- R1 / <Picture 1>: 原角色身份参考图。只锁定脸、五官、发型、瞳色、服装识别点。",
        "- R2 / <Picture 2>: Image 2生成的本片造型图。锁定材质、身体比例、变体结构和全身细节。",
        "- R3 / <Picture 3>: Image 2生成的9:16首帧/场景图。锁定机位、光线、道具位置和环境。",
    ]
    if segment_no > 1:
        lines.append("- R4 / <Picture 4>: 上一段导出的最后一帧。作为本段第0秒的精确姿态与构图锚点。")
    lines.append("- 冲突优先级：R4起始姿态 > R1身份 > R2造型 > R3长期场景。")
    return "\n".join(lines)


def image2_character_prompt(work: dict[str, Any]) -> str:
    return f"""这是严格的角色身份保持与视频参考图制作任务。

输入参考图R1只负责定义：{work['character']}的身份、脸型、五官比例、眼睛、发型、发色、服装主配色和不可替换的角色识别点。不要把参考图重新设计成相似角色，不要平均化五官，不要改变年龄感与性别表达。

目标造型：{work['form']}。

请生成一张供MiniMax H3使用的R2角色造型参考图：
1. 单一清晰主体；如作品包含双人或多人，严格保持每名角色各自身份并拉开颜色、站位与轮廓差异。
2. 全身完整，三分之二正面，镜头略低于眼平；头顶、双手、双脚、尾巴、帽饰、武器或关键配件不得裁切。
3. 中性稳定站姿，四肢关系清楚，手指尽量自然简化，避免交叉遮挡；为后续动作留出空间。
4. 材质、比例与变体必须服从“目标造型”，但人物身份必须服从R1；不得生成第三张折中脸。
5. 纯净浅灰背景，柔和三点光，真实接触阴影，边缘清楚，纹理不过密。
6. 不要场景、文字、字幕、UI、水印、品牌标志、额外人物、拼图、三视图排版或对比图。
7. 不要运动模糊，不要夸张透视，不要隐藏手脚，不要增加参考图中不存在的敏感暴露。

本片核心道具与动作需求：{work['hook']}。R2只需为该动作准备合适的造型与可见结构，不要直接演完剧情。"""


def image2_first_frame_prompt(work: dict[str, Any]) -> str:
    return f"""使用R1原角色身份图与R2造型图，生成MiniMax H3的R3首帧。R1只管身份，R2只管本片造型，不得平均融合。

作品：{work['id']}《{work['title']}》
场景：{work['scene']}。
首秒钩子：{work['hook']}。

画面必须停在“关键事件发生前约0.15至0.25秒”的可启动状态：观众一眼能看懂角色、关键道具、即将发生的动作关系，但不要把结果提前演完。

构图要求：
- 9:16竖屏，主体位于中部偏下，顶部和底部保留短视频UI安全区。
- {work['camera']}。
- 角色面部、双手/主要肢体、关键道具和触发点同时可见；接触关系与受力方向明确。
- 环境结构、家具、门窗、道路和光源位置必须稳定，便于后续连续镜头复用。
- 角色表情为动作触发前的自然状态，不要提前做夸张终局表情。
- 清晰、锐利、低噪点、低运动模糊；不要海报式文字，不要字幕、UI、水印、品牌和额外人物。
- 对存在安全边界的情节，仅表现卡通、玩具化、低风险互动，不展示真实伤害。

最终只输出一张完整首帧，不要拼图、对比图或说明文字。"""


def timeline_for(work: dict[str, Any], segment_no: int) -> str:
    if work["mode"] == "10s":
        return "\n".join(f"- {beat}" for beat in work["beats"])

    beat = work["beats"][segment_no - 1]
    clauses = [c.strip() for c in re.split(r"[；;。]", beat) if c.strip()]
    first = clauses[0]
    second = clauses[1] if len(clauses) > 1 else "动作继续发展，空间与角色外观保持稳定"
    extra = "；".join(clauses[2:]) if len(clauses) > 2 else ""
    bridge = work["loop"] if segment_no == 6 else f"本段结尾稳定保留第{segment_no + 1}段所需的动作方向、道具位置和视线"
    rows = [
        f"- 0.0-1.2秒：从本段首帧连续启动。{first}。",
        f"- 1.2-4.0秒：{second}。",
        f"- 4.0-7.8秒：{extra or first}；动作升级但不得突然换景、换脸或改变服装。",
        f"- 7.8-9.6秒：完成本段因果结果，角色视线与关键道具运动逐渐稳定。",
        f"- 9.6-10.0秒：{bridge}；保持约0.4秒清晰末帧供R4提取。",
    ]
    return "\n".join(rows)


def h3_prompt(work: dict[str, Any], segment_no: int) -> str:
    total = segment_count(work)
    prev = "" if segment_no == 1 else "\n<Picture 4> is the exact last frame exported from the previous segment and must be used as this segment's first-frame anchor."
    first_anchor = "<Picture 3>" if segment_no == 1 else "<Picture 4>"
    relation = "[reference generation + keyframe completion]"
    segment_story = work["beats"][0] if work["mode"] == "10s" else work["beats"][segment_no - 1]
    final_note = work["payoff"] if segment_no == total else "本段必须为下一段留下单一、明确、可复现的空间和动作状态。"
    return f"""subject_definitions:
<Subject 1> is {work['character']}, whose exact identity comes from <Picture 1> and whose target transformed design, material, body proportion, costume details, and visible accessories come from <Picture 2>. The identity from <Picture 1> must never be averaged with or replaced by another face.
<Subject 2> is the stable environment and key prop system shown in <Picture 3>: {work['scene']}.
<Picture 3> is the composition, lighting, prop-placement, and long-term scene anchor for this work. For segment 1 it is also the exact first frame.{prev}

summary:
{relation} Generate segment {segment_no}/{total} of a vertical 10-second audiovisual short titled “{work['title']}”. Preserve <Subject 1> exactly, keep <Subject 2> spatially stable, and execute this segment's causal action without introducing unrelated subjects. The segment must begin from {first_anchor} and end on a stable frame suitable for continuation or seamless looping.

retention_analysis:
<Subject 1> (appears throughout the segment): fully_preserved - preserve facial identity, hairstyle, eye color, costume recognition points, target material, body ratio, and all signature accessories. Do not create a third averaged design.
<Subject 2> (appears throughout the segment): fully_preserved - keep the scene layout, main light direction, furniture/architecture, and key prop positions coherent; only the explicitly described magical or mechanical state may change.
<Picture 3> (scene and composition anchor): fully_preserved - retain its camera axis, visual hierarchy, color logic, and long-term spatial arrangement.
{"<Picture 4> (segment first frame): fully_preserved - begin from the exact pose, camera, object state, and motion direction of the previous segment's last frame." if segment_no > 1 else "<Picture 3> (segment first frame): fully_preserved - the first generated frame must match the supplied first-frame anchor before motion begins."}

detailed_description:
The target is a polished vertical short-video animation with clear toy-scale material response, readable contact shadows, restrained depth of field, and physically understandable motion. Do not generate subtitles, watermarks, logos, UI, extra characters, duplicate limbs, identity drift, costume swaps, unexplained scene changes, or high-speed camera spins.

[Shot 1] The video begins exactly from {first_anchor}. Camera rule: {work['camera']}.
The main causal action for this segment is: {segment_story}

Exact 10-second timeline:
{timeline_for(work, segment_no)}

Performance and continuity constraints:
- The face and hairstyle remain recognizable in every visible frame; expressions change continuously rather than snapping.
- Hands, paws, wings, tails, tools, and props keep consistent counts and attachment points.
- Contact, weight, inertia, liquid, cloth, paper, glass, metal, soft vinyl, or plush deformation follow the material stated in the source design.
- No unsupported spoken lines or visible text are added. The only optional spoken line is: <d>[Chinese] {work['dialogue']}</d>
- {final_note}

overall_soundscape:
{work['sound']}。声音必须与动作同步，环境底噪连续，不复制官方配音，不加入可识别品牌提示音；对白可用自有配音、通用合成声或后期字幕替代。

non_diegetic_music:
Use an original, low-density musical cue that supports the action rhythm without imitating any official soundtrack or copyrighted melody. Keep dialogue and physical sound effects intelligible. For a loop, the final beat must reconnect naturally to the opening beat.
"""


def platform_copy(work: dict[str, Any]) -> str:
    tags = " ".join(f"#{t}" for t in work["tags"])
    return f"""- 封面大字：{work['title'][:18]}
- B站标题：{work['character']}｜{work['title']}【AI辅助二创 / MiniMax H3】
- 抖音标题：{work['title']}，最后一秒又回去了｜AI生成内容
- 小红书标题：把{work['character']}做成《{work['title']}》的短片是什么效果
- 简介：非官方同人二创；角色与游戏相关权利归原权利人。本视频包含AI生成/AI辅助制作内容，剧情、对白和镜头设计为本项目原创。
- 标签：{tags} #MiniMaxH3 #AI生成内容
"""


def work_markdown(work: dict[str, Any]) -> str:
    parts = [
        f"# {work['id']}｜{work['title']}",
        "",
        f"- 游戏：{work['game']}",
        f"- 角色：{work['character']}",
        f"- 成片：{work['mode']}（{segment_count(work)}个H3生成单元）",
        f"- 优先级：{work['priority']}",
        f"- 制作风险：{work['risk']}",
        f"- R1检索式：`{work['r1_query']}`",
        "",
        "## 故事设计",
        "",
        f"- 造型：{work['form']}",
        f"- 场景：{work['scene']}",
        f"- 首秒钩子：{work['hook']}",
        f"- 结果/反转：{work['payoff']}",
        f"- 循环/衔接：{work['loop']}",
        f"- 声音：{work['sound']}",
        f"- 自检修订：{work['qc']}",
        "",
        "### 原始节拍",
        "",
    ]
    parts.extend(f"{idx}. {beat}" for idx, beat in enumerate(work["beats"], 1))
    parts += [
        "",
        "## Image 2｜R2角色造型提示词",
        "",
        "```text",
        image2_character_prompt(work),
        "```",
        "",
        "## Image 2｜R3首帧提示词",
        "",
        "```text",
        image2_first_frame_prompt(work),
        "```",
        "",
        "## 发布包装",
        "",
        platform_copy(work),
    ]
    for seg in range(1, segment_count(work) + 1):
        parts += [
            "",
            f"## MiniMax H3｜第{seg}段 / 共{segment_count(work)}段",
            "",
            "### 输入清单",
            "",
            input_manifest(seg),
            "",
            "### Ref2VA提示词",
            "",
            "```text",
            h3_prompt(work, seg),
            "```",
        ]
    return "\n".join(parts).rstrip() + "\n"


def clean_out() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "catalog" / "works").mkdir(parents=True, exist_ok=True)
    (OUT / "prompts" / "image2").mkdir(parents=True, exist_ok=True)
    (OUT / "prompts" / "h3").mkdir(parents=True, exist_ok=True)
    (OUT / "manifests").mkdir(parents=True, exist_ok=True)
    (OUT / "site").mkdir(parents=True, exist_ok=True)


def write_manifest(works: list[dict[str, Any]]) -> None:
    path = OUT / "manifests" / "run_manifest.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["id", "game", "character", "mode", "segments", "priority", "risk", "status", "source"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for w in works:
            writer.writerow({
                "id": w["id"], "game": w["game"], "character": w["character"],
                "mode": w["mode"], "segments": segment_count(w), "priority": w["priority"],
                "risk": w["risk"], "status": "not_started", "source": w["_source"],
            })


def write_prompts(works: list[dict[str, Any]]) -> None:
    for w in works:
        base = f"{w['id']}_{slug(w['title'])}"
        md = work_markdown(w)
        (OUT / "catalog" / "works" / f"{base}.md").write_text(md, encoding="utf-8")
        image2 = (
            f"# {w['id']} R2\n\n{image2_character_prompt(w)}\n\n"
            f"# {w['id']} R3\n\n{image2_first_frame_prompt(w)}\n"
        )
        (OUT / "prompts" / "image2" / f"{base}.txt").write_text(image2, encoding="utf-8")
        for seg in range(1, segment_count(w) + 1):
            (OUT / "prompts" / "h3" / f"{base}_S{seg:02d}.txt").write_text(h3_prompt(w, seg), encoding="utf-8")


def write_all_catalog(works: list[dict[str, Any]]) -> None:
    index = [
        "# AI Generate Video V2｜100案完整目录",
        "",
        "本文件由 `scripts/build_all.py` 自动生成。每案含Image 2 R2/R3提示词与MiniMax H3全部10秒段提示词。",
        "",
    ]
    for w in works:
        index.append(work_markdown(w))
        index.append("\n---\n")
    (OUT / "catalog" / "ALL_100.md").write_text("\n".join(index), encoding="utf-8")


def write_json(works: list[dict[str, Any]]) -> None:
    clean = []
    for w in works:
        item = {k: v for k, v in w.items() if not k.startswith("_")}
        item["segments"] = segment_count(w)
        item["image2_r2_prompt"] = image2_character_prompt(w)
        item["image2_r3_prompt"] = image2_first_frame_prompt(w)
        item["h3_prompts"] = [h3_prompt(w, i) for i in range(1, segment_count(w) + 1)]
        clean.append(item)
    (OUT / "works.v2.compiled.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def write_site(works: list[dict[str, Any]]) -> None:
    payload = []
    for w in works:
        payload.append({
            "id": w["id"], "game": w["game"], "character": w["character"], "mode": w["mode"],
            "title": w["title"], "hook": w["hook"], "payoff": w["payoff"], "priority": w["priority"],
            "risk": w["risk"], "tags": w["tags"], "qc": w["qc"],
            "r2": image2_character_prompt(w), "r3": image2_first_frame_prompt(w),
            "h3": [h3_prompt(w, i) for i in range(1, segment_count(w) + 1)],
        })
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Generate Video V2</title>
<style>
:root{font-family:Inter,"Microsoft YaHei",sans-serif;color:#171717;background:#f4f5f7}*{box-sizing:border-box}body{margin:0}header{position:sticky;top:0;z-index:5;background:#111;color:#fff;padding:18px 5vw;box-shadow:0 2px 16px #0003}h1{margin:0 0 8px;font-size:clamp(22px,3vw,38px)}.sub{color:#bbb}.bar{display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px;margin-top:14px}input,select{width:100%;padding:11px;border:1px solid #555;border-radius:10px;background:#222;color:#fff}main{padding:24px 5vw 80px}.count{margin-bottom:16px;color:#555}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}.card{background:#fff;border:1px solid #e2e2e2;border-radius:18px;padding:18px;box-shadow:0 8px 28px #0000000d}.meta{display:flex;gap:8px;flex-wrap:wrap}.pill{font-size:12px;background:#eee;border-radius:999px;padding:5px 9px}.card h2{font-size:20px;margin:12px 0 6px}.character{color:#666}.hook{line-height:1.7}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}button{border:0;border-radius:9px;padding:9px 12px;cursor:pointer;background:#111;color:#fff}.secondary{background:#e9e9e9;color:#111}dialog{width:min(960px,94vw);max-height:90vh;border:0;border-radius:16px;padding:0;box-shadow:0 20px 80px #0007}dialog::backdrop{background:#0008}.modal-head{position:sticky;top:0;background:#fff;padding:16px 20px;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;gap:12px}.modal-body{padding:20px;white-space:pre-wrap;line-height:1.65}.close{background:#eee;color:#111}.empty{padding:60px;text-align:center;color:#777}@media(max-width:700px){.bar{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
</style></head><body>
<header><h1>AI Generate Video V2</h1><div class="sub">100案｜Image 2 R2/R3｜MiniMax H3 Ref2VA｜离线可检索</div><div class="bar"><input id="q" placeholder="搜索标题、角色、游戏、标签"><select id="game"><option value="">全部游戏</option></select><select id="mode"><option value="">全部时长</option><option>10s</option><option>60s</option></select></div></header>
<main><div id="count" class="count"></div><div id="grid" class="grid"></div></main>
<dialog id="dlg"><div class="modal-head"><strong id="dlgTitle"></strong><button class="close" onclick="dlg.close()">关闭</button></div><div id="dlgBody" class="modal-body"></div></dialog>
<script>const works=__DATA__;const q=document.querySelector('#q'),game=document.querySelector('#game'),mode=document.querySelector('#mode'),grid=document.querySelector('#grid'),count=document.querySelector('#count'),dlg=document.querySelector('#dlg'),dlgTitle=document.querySelector('#dlgTitle'),dlgBody=document.querySelector('#dlgBody');[...new Set(works.map(x=>x.game))].sort().forEach(x=>game.add(new Option(x,x)));function show(title,text){dlgTitle.textContent=title;dlgBody.textContent=text;dlg.showModal()}function copy(text){navigator.clipboard.writeText(text).then(()=>alert('已复制'))}function render(){const key=q.value.trim().toLowerCase();const rows=works.filter(x=>(!game.value||x.game===game.value)&&(!mode.value||x.mode===mode.value)&&(!key||JSON.stringify(x).toLowerCase().includes(key)));count.textContent=`显示 ${rows.length} / ${works.length} 案`;grid.innerHTML=rows.map((x,i)=>`<article class="card"><div class="meta"><span class="pill">${x.id}</span><span class="pill">${x.game}</span><span class="pill">${x.mode}</span><span class="pill">${x.priority}/${x.risk}</span></div><h2>${x.title}</h2><div class="character">${x.character}</div><p class="hook"><b>钩子：</b>${x.hook}</p><p class="hook"><b>反转：</b>${x.payoff}</p><div class="buttons"><button onclick="show('${x.id} R2',works[${works.indexOf(x)}].r2)">R2提示词</button><button onclick="show('${x.id} R3',works[${works.indexOf(x)}].r3)">R3提示词</button><button onclick="show('${x.id} H3',works[${works.indexOf(x)}].h3.join('\n\n===== NEXT SEGMENT =====\n\n'))">H3提示词</button><button class="secondary" onclick="copy(works[${works.indexOf(x)}].h3[0])">复制首段</button></div></article>`).join('')||'<div class="empty">没有匹配项目</div>'}q.oninput=game.onchange=mode.onchange=render;render();</script></body></html>'''
    (OUT / "site" / "index.html").write_text(template.replace("__DATA__", data), encoding="utf-8")


def print_summary(works: list[dict[str, Any]]) -> None:
    games = Counter(w["game"] for w in works)
    modes = Counter(w["mode"] for w in works)
    units = sum(segment_count(w) for w in works)
    print("Validation: OK")
    print(f"Works: {len(works)} | 10s: {modes['10s']} | 60s: {modes['60s']} | H3 units: {units}")
    for game, count in games.items():
        print(f"  {game}: {count}")
    print(f"Output: {OUT}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    works = load_works()
    errors = validate_works(works)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if args.validate_only:
        print_summary(works)
        return 0

    clean_out()
    write_manifest(works)
    write_prompts(works)
    write_all_catalog(works)
    write_json(works)
    write_site(works)
    print_summary(works)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
