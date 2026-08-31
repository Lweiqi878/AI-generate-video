# AI Generate Video｜194案 MiniMax H3 短视频生产库

这是把 [GitHub 原100案](https://github.com/Lweiqi878/AI-generate-video) 与本地旧目录中合规保留的94案合并后的可执行版本。四个明确排除项——`鸣潮`、`明日方舟`本体、`崩坏3`、`第五人格`——不进入最终目录；`明日方舟：终末地`作为独立作品方向保留。

## 合并结果

| 指标 | 数量 |
|---|---:|
| GitHub主线 | 100 |
| 本地输入 | 100 |
| 本地排除 | 6 |
| 本地保留 | 94 |
| **最终作品** | **194** |

- ID连续为 `V2-001`–`V2-194`。
- 完全重复记录：0；规范化标题重复：0。
- 同角色、同道具或同题材的近似项只进入人工复核，不在证据不足时自动误删。
- 详细映射见 [`data/merge_manifest.json`](data/merge_manifest.json)，重复检查见 [`docs/DUPLICATE_AUDIT.md`](docs/DUPLICATE_AUDIT.md)。

## 六支发布级试片

本仓库包含六支经 FFmpeg 完成叙事包装、字幕、AI标识、音频规范和封面导出的试片。文件夹统一采用 `游戏或原创分类__激励计划__视频名`。最新两支先由 Codex Image2 生成角色、场景与故事关键帧，再把相邻关键帧交给本地 MiniMax H3 做首尾帧视频，避免“先生成抽象动态、剪完仍看不懂”的问题：

| 作品 | 类型 | 叙事方式 |
|---|---|---|
| V2-191《小戏楼下班后，偷偷长腿回家了》 | 原创动画重包装 | 直说“关灯出走—管理员折返—停歪露馅” |
| V2-193《录像带越狱到一半，老板回来了》 | 原创动画重包装 | 直说“集体逃跑—叠梯开门—钥匙响起装死” |
| V2-021《汉堡纸机甲出动，只为挡住一滴番茄酱》 | 绝区零AI辅助二创 | 两个8秒段；第一段末帧作为第二段首帧 |
| V2-023《比利和扫地机的正午决斗，赌注竟是做家务》 | 绝区零AI辅助二创 | 两个8秒段；对峙后连续揭示清洁比赛 |
| V2-143《安比吃光整桌汉堡，却把最后一根薯条留给了我》 | 绝区零AI辅助二创 | 结果前置；“只吃一口—只剩一根—分你一半”的完整情绪回报 |
| V2-122《帕姆催了三次，开拓者还是要翻完最后一个垃圾桶》 | 星铁AI辅助二创 | 玩家梗开场；“催发车—翻垃圾桶—瓶盖战利品—推上车”的完整笑点 |

成片入口见 [`publishing/README.md`](publishing/README.md)。较大的原始生成片段、前后帧和审片图保留在本地 `production/`，不进入Git历史；MiniMax部署目录只提供推理服务，不存放本项目结构。

## 发布结构与一键准备

```text
publishing/
├─ README.md
├─ UPLOAD_QUEUE.md
└─ ready/
   └─ 游戏__激励计划__视频名/
      ├─ 视频名.mp4
      ├─ 视频名_封面.jpg
      ├─ 视频名_投稿卡.txt
      └─ provenance/        # 字幕、提示词、生成参数、哈希
```

运行 `./投稿准备.ps1`，选择作品和平台后会先执行发布校验，只复制该平台的标题、正文与标签，并在资源管理器中定位成片。需要同时打开平台上传页时运行 `./投稿准备.ps1 -OpenUploadPage`；也可直接运行 `./投稿准备.ps1 -ReleaseId V2-143 -Platform 抖音 -OpenUploadPage`。标有“资格待核验”或“无激励任务关联”的作品不会默认关联官方激励话题。抖音、小红书与B站的任务查找方式见 [`docs/PLATFORM_INCENTIVE_GUIDE.md`](docs/PLATFORM_INCENTIVE_GUIDE.md)。

## Image2 × 本地 MiniMax H3 协作链

```text
故事与钩子
  → Image2角色锚点 + 场景锚点
  → Image2首/中/尾关键帧
  → 本地MiniMax H3相邻关键帧I2V
  → 结果前置、字幕、声音与封面剪辑
  → 分平台标题/正文/标签
  → 投稿前规则校验
```

Image2图片与创作说明随作品放在 `publishing/ready/<作品>/provenance/`；MiniMax部署目录只负责本地推理。可复现的本地提交脚本为 `scripts/submit_local_h3_i2v.ps1`，不会调用外部图片API。

## 最短使用路径

```powershell
python .\scripts\validate_catalog.py
python .\scripts\audit_duplicates.py --check
python .\scripts\build_all.py
python .\scripts\build_publishing.py
python .\scripts\validate_releases.py
```

也可以直接运行 `./run_build.ps1`。构建结果写入：

```text
generated/
├─ catalog/ALL_194.md
├─ catalog/works/
├─ prompts/image2/
├─ prompts/h3/
├─ manifests/run_manifest.csv
├─ works.v2.compiled.json
└─ site/index.html
```

`generated/` 可完全重建，因此不提交到Git；GitHub Actions会把它上传为短期构建制品。

## 数据组织

```text
data/slates/
├─ 01–04_*.jsonl   # GitHub原100案，V2-001–V2-100
└─ 05–08_*.jsonl   # 本地保留94案，V2-101–V2-194
```

每案统一包含角色/主体、造型、场景、首秒钩子、剧情节拍、反转、声音、循环、相机、风险、检索式和自检字段。编译器会进一步生成 Image 2 R2/R3 提示词、MiniMax H3 每个10秒生成单元的Ref2VA提示词、离线检索页、CSV任务清单和总目录。

## 重新导入本地94案

仓库已提交转换后的JSONL，日常构建不依赖旧目录。需要核验或重做迁移时：

```powershell
python .\scripts\import_legacy_catalog.py --source G:\ai-generate-video-game\works.json
python .\scripts\audit_duplicates.py --check
python .\scripts\validate_catalog.py
```

导入器会校验本地输入必须为100案、精确排除6案，并输出确定性的94案与来源哈希。

## 重要边界

- 仓库只保存原创脚本、提示词、检索式、工具和六支AI辅助试片，不重新分发游戏官方立绘、CG、配音、音乐或第三方画师图片。
- “存在创作者计划”不代表生成式AI自动有参赛资格；投稿前需重新核对当期规则、AI条款、时长、分辨率与授权范围。
- 不克隆官方声优声线，不使用官方原声，不暗示官方合作。
- 发布时保留生成文件的溯源信息，并在画面和投稿说明中明确标注AI生成/AI辅助制作。

## 来源与许可

GitHub源仓库：[Lweiqi878/AI-generate-video](https://github.com/Lweiqi878/AI-generate-video)。代码与本仓库原创文字按仓库许可使用；第三方游戏名称、角色、商标、图像、音乐和声音不属于本项目许可范围。
