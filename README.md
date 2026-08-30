# AI Generate Video｜MiniMax H3 短视频生产体系

> 版本：`v2.0.0-anchor`  
> 进度锚点：2026-08-30  
> 目标：把“原角色图 → Image 2 造型参考图/首帧 → MiniMax H3 10 秒镜头 → 60 秒连续故事 → B站/抖音/小红书发布”做成可复用、可校验、可持续扩展的本地生产线。

## 本轮结论

- 新建 **100 个全新作品方案**，不沿用旧版故事。
- 主选题池不再包含：**鸣潮、明日方舟、崩坏3、第五人格**。
- 原神常规角色占比显著下调，合并为“原神／千星奇域”小规模实验组。
- 新增重点方向：**无限暖暖、恋与深空、蛋仔派对、燕云十六声、逆水寒手游、王者荣耀**。
- 每个作品由结构化源数据驱动，可在本地批量生成 Image 2 提示词、H3 Ref2VA 提示词、镜头任务单、CSV、静态网页和 FFmpeg 拼接清单。
- 仓库只保存提示词、脚本和来源清单，不重新分发游戏官方立绘或第三方画师图片。

## 100 案分布

| 方向 | 数量 |
|---|---:|
| 原神／千星奇域 | 6 |
| 崩坏：星穹铁道 | 14 |
| 绝区零 | 14 |
| 明日方舟：终末地 | 12 |
| 异环 | 10 |
| 无限暖暖 | 10 |
| 恋与深空 | 8 |
| 蛋仔派对 | 8 |
| 燕云十六声 | 6 |
| 逆水寒手游 | 6 |
| 王者荣耀 | 6 |
| **总计** | **100** |

## 目录

```text
AI-generate-video/
├─ data/
│  ├─ slates/                 # 100案结构化源数据，分4卷
│  ├─ incentive_candidates.json
│  └─ schema/work.schema.json
├─ catalog/
│  └─ INDEX.md                # 100案快速索引
├─ docs/
│  ├─ WORKFLOW.md             # R1/R2/R3/R4生产流程
│  ├─ H3_PROMPT_SPEC.md       # 按官方Ref2VA结构编译
│  ├─ INCENTIVE_STRATEGY.md   # 激励候选分层与逐期核验
│  ├─ REFERENCE_ASSETS.md     # 官方素材查找与选图规范
│  ├─ QUALITY_GATE.md         # 三轮自检与淘汰规则
│  └─ COMPLIANCE.md           # AI标识、IP与活动规则边界
├─ scripts/
│  ├─ build_all.py            # 一键编译全部提示词与网页
│  ├─ validate_catalog.py     # 数据与时长校验
│  ├─ extract_last_frame.py   # 提取R4末帧
│  └─ concat_segments.py      # 拼接6×10秒故事
├─ .github/workflows/
│  └─ validate.yml
├─ run_build.ps1
├─ run_build.bat
└─ README.md
```

## 最短使用路径

```powershell
# Windows PowerShell
python .\scripts\validate_catalog.py
python .\scripts\build_all.py
```

或直接双击：

```text
run_build.bat
```

编译结果写入 `generated/`：

```text
generated/
├─ catalog/ALL_100.md
├─ prompts/image2/
├─ prompts/h3/
├─ manifests/run_manifest.csv
└─ site/index.html
```

## 每个作品的输入职责

- **R1 原角色身份图**：只负责脸、发型、瞳色、服装识别点与角色身份。
- **R2 Image 2 造型图**：负责手办化、动物化、微缩化、材质和全身比例。
- **R3 Image 2 首帧图**：负责9:16构图、现实/游戏场景、光线、道具位置和接触关系。
- **R4 上一段末帧**：仅用于60秒作品第2—6段的空间、动作与姿态衔接。

冲突优先级：`R4起始姿态 > R1身份 > R2造型 > R3长期场景`。

## 重要边界

1. “有创作者计划”不等于“本期活动允许AI作品”。仓库中的激励表是**选题决策工具**，不是奖金承诺。
2. 所有活动在投稿前都要记录官方规则页、截止时间、AI条款、平台和作品时长要求。
3. 不克隆官方声优声线；对白使用原创短句或后期字幕/自有配音。
4. 发布时保留并补充AI生成标识；不删除模型或平台写入的溯源信息。
5. 官方立绘、PV截图和游戏内截图由制作者按授权边界自行取得，仓库只提供检索式和选图标准。

## 版本策略

- `main`：可执行、可校验的当前基线。
- `generated/`：默认由本地电脑编译，可按需要另行提交。
- 每次扩充先改 `data/slates/*.jsonl`，再运行校验与编译，避免手工维护数百份重复提示词。
