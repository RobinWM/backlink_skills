---
name: blog-3p-harness
description: "初始化、冻结、恢复并机械校验可移植的博客 3P 内容项目；要求用户先确认完整写前方案，严格限制用户提供的平台范围，且不自动发布。用于启动内容项目、准备工作区、汇报写前方案、锁定需求或校验工作流结构。"
---

# 博客 3P：本地流程工具

先阅读[术语约定](../../docs/terminology.zh-CN.md)。本技能负责可恢复的本地工作区和机械校验，不代替编辑判断、平台发布或人工原生编辑器操作。

## 初始化

运行 `scripts/harnessctl.py init --workspace <absolute-path> --campaign-id <id>`。它只创建本地文件：`campaign.json`、`state.json`、`confirmation.md`、`requirements-contract.md`、唯一可编辑的 `prewrite-plan.json`、确定性只读视图 `prewrite-plan.md`、一次性 `pre-clearance-checklist.md` 及标准证据/输出目录。当前 schema-2.5 工作区的写前方案清单为 schema `1.3`。

## 写前方案与用户确认

G 的第一阶段是 `prewrite_planning`。在用户确认前，不得存在文章独立 Git 工作区、文章协作组 G/W/R、文章队列、大纲、正文、图片、唯一基准稿或文章调研子角色。G 编辑 `prewrite-plan.json` 后运行 `sync-prewrite-plan`，再向用户展示生成的 `prewrite-plan.md`；Markdown 是只读视图，禁止双份手填。

每篇方案卡必须包含任务/受众、独立读者价值、必保留的次要 CTA（精确可见锚文本、目标链接、主张依据、读者相关性和披露）、证据/不确定性、关键词/本地化、事实来源、暂定标题/大纲、图文叙事、人工发布传递假设和待用户决定事项。不可证实的内容标为 `UNVERIFIED` 并说明风险；该方案不是 `RESEARCH_READY` 或 `RESEARCH_APPROVED`，确认后 W 仍要完成一体化研究并由同一 R 审批。

只有明确的 `OWNER_PREWRITE_PLAN_CONFIRMED` 才允许启动文章任务。将一个确认 ID、准确文章 ID 集合、报告 SHA-256 和清单 SHA-256 同时绑定到 `state.json`、`confirmation.md`、`requirements-contract.md` 和 `campaign.json.scope_lock.prewrite_plan_receipt`。任务、范围、标题/大纲、语言、视觉、事实或传递假设发生实质改变时，旧回执失效并回到用户确认；`OWNER_PREWRITE_PLAN_CHANGES_REQUESTED` 不允许部分启动。

## 平台范围与本地化

- 没有平台映射时，G 只可创建或恢复一个可见、可复用的 `blog-3p-platform-matching` 子角色；它只在用户提供的 XLSX/表格/消息候选中做语言/市场/内容格式匹配。G 只核对来源与唯一性，不排序、不选平台。
- `platform_scope.allowed_pairs` 只是已确认 `owner-platform-selection.json` 的投影，不能自行授权。人工发布的每个 `{platform, account}` 必须有用户来源哈希、精确定位、平台原文、账号确认原文和确认 ID；每篇文章只绑定一个且不可重复的平台/账号组合。
- 登录页、注册公告、编辑器行为、会话恢复、内部配置和历史记录只能说明可承接性，绝不能新增允许的平台/账号。模糊的“新增语言”或“平台不重复”请求没有平台选择授权，只能返回 `OWNER_DECISION_REQUIRED`。
- 文章语言来自用户确认；平台支持语言只决定可否承接。对每篇人工发布文章记录 `locale_platform_validation`，不兼容时写 `LOCALE_PLATFORM_MISMATCH_RECONFIRM_OWNER`，不得自动翻译或改配。
- 跨语言用语顺序固定为 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`。Google Trends 如可用，只比较英文种子和英文候选，并且只是全球相对关注度背景；数据不足、无 `Breakout` 或无清晰趋势时，不得强求或阻塞，改以有边界的目标平台读者需求、品牌站和地区 SERP 制定长尾意图。目标语言用语仍由地区 SERP 或有据的模型翻译兜底决定。

## 运行与交接

1. G 完成写前方案、取得确认并绑定哈希后，才可为已就绪文章创建独立 Git 工作区和文章专属协作组。
2. `blog-3p-writer` 是唯一可执行 W；`blog-writer-merged` 只作编辑参考。该文同一 `blog-3p-review` 先给出 `RESEARCH_APPROVED`，再贯穿完整质量循环。
3. `blog-3p-gate` 只验收已批准交付是否保留用户需求；`blog-3p-human-handoff` 仅在 G 授权后编译人工发布交接包。
4. 人工回传 `HUMAN_ACCEPTED` URL 后，校验回执并生成只读快照；只恢复该文章既有 G 做公开页比对，不重启 W/R。

可见、可复用的角色与独立 Git 工作区是不同概念。支持独立 Git 工作区时，每篇就绪文章必须由 `ARTICLE_LANE_GATEKEEPER` 作为根创建可见独立 Git 工作区，再在其中复用唯一 W/R；不支持时仅可使用已记录、路径互不重叠的共享工作区降级。CLI 只可执行文件读取、JSON 校验、哈希、脚本测试和版本控制等确定性本地操作，不能代替独立角色。

每次交接前运行 `scripts/harnessctl.py check --workspace <absolute-path>`。当前 schema-2.5 文章包还运行 `check-article-package` 和 `check-handoff-manifest`；它们验证结构、哈希、同一 R 的可见回执和声明保真，不评分文章质量。公开回传先运行 `check-public-return-receipt`。

## 恢复

发生压缩、恢复或上下文不确定时，停止并重读 `campaign.json`、`state.json`、`prewrite-plan.md/json`、`confirmation.md`、`requirements-contract.md`、全部报告、开放问题项和当前唯一基准稿；在状态历史中追加 `CONTEXT_REHYDRATED`，不得推断缺失证据。

详见[内容项目契约](references/campaign-contract.md)和[写前检查清单](references/pre-clearance.md)。机器字段、状态码、命令参数与路径保持不变。
