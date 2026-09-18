---
name: blog-3p-harness
description: "初始化、冻结、恢复并机械校验仅人工原生发布交接的博客 3P 内容项目；要求用户先确认完整写前方案和每篇平台/账号映射，严格限制用户提供的平台范围，且不自动发布。用于启动内容项目、准备工作区、汇报写前方案、锁定需求或校验工作流结构。"
---

# 博客 3P：本地流程工具

先阅读[术语约定](../../docs/terminology.zh-CN.md)。本技能负责可恢复的本地工作区和机械校验，不代替编辑判断、平台发布或人工原生编辑器操作。

## 初始化

运行 `scripts/harnessctl.py init --workspace <absolute-path> --campaign-id <id>`。它只创建本地文件：`campaign.json`、`state.json`、`confirmation.md`、`requirements-contract.md`、唯一可编辑的 `prewrite-plan.json`、确定性只读视图 `prewrite-plan.md`、一次性 `pre-clearance-checklist.md` 及标准证据/输出目录。当前 schema-2.11 工作区使用写前方案 schema `1.7` 和 evidence pack schema `1.3`，并创建 `evidence/owner-confirmations/` 保存用户原始确认回执；schema-2.10 / plan-1.6 / evidence-1.2 仅保留读取和校验兼容。当前工作区只支持人工原生发布交接；脚本绝不执行平台写入。

## 写前方案与用户确认

G 的第一阶段是 `prewrite_planning`。在用户确认前，不得存在文章独立 Git 工作区、文章专属 W/R 对、文章队列、大纲、正文、图片、唯一基准稿或文章调研子角色。G 编辑 `prewrite-plan.json` 后运行 `sync-prewrite-plan`，再向用户展示生成的 `prewrite-plan.md`；Markdown 是只读视图，禁止双份手填。

每篇方案卡固定为四个可读区块：任务/受众；独立读者价值和必保留次要 CTA（精确可见锚文本、目标链接、主张依据、读者相关性和披露）；`editorial_brief`；风险与待用户决定事项。卡片还必须把 `frozen_delivery_mapping`（文章语言、市场、平台、账号、适配模式）、`topic_slot`（读者任务、核心意图、市场、差异化角度、禁止偏离项）和 `evidence_posture`（方法模板或有记录的实测）展示给用户。`topic_slot` 是 W 的选词/标题边界而不是冻结的字面关键词或标题。`editorial_brief` 要完整汇总关键词/本地化路径、事实来源及边界、暂定标题/大纲、图文叙事和已知人工发布传递假设，而不是把同一事实拆成九份反复维护。每篇还要冻结 `review_effort`：默认 `STANDARD_INTEGRATED_REVIEW / INTEGRATED_IN_FULL_REVIEW`；只有有明确风险理由才用 `ELEVATED_EARLY_CHALLENGE / SEPARATE_RESEARCH_REVIEW_REQUIRED`。不可证实的内容标为 `UNVERIFIED` 并说明风险；该方案不是 `RESEARCH_READY` 或 `RESEARCH_APPROVED`，确认后 W 仍要完成一体化研究。

只有明确的 `OWNER_PREWRITE_PLAN_CONFIRMED` 才允许启动文章任务。schema 2.11 必须先把用户原始确认文本保存到 `evidence/owner-confirmations/`，再运行 `confirm-prewrite-plan --confirmation-id ... --receipt-file ... --receipt-type OWNER_MESSAGE|OWNER_FILE --source-locator ...`。该命令将确认 ID、准确文章 ID 集合、报告／清单哈希、受保护范围快照，以及回执路径／哈希／来源定位／时间同时绑定到 `state.json`、`confirmation.md`、`requirements-contract.md` 和 `campaign.json.scope_lock.prewrite_plan_receipt`；直接编辑状态或确认 ID 不能提升方案。`article_language`、`market`、`platform`、`account`、`fit_mode`、跨语言例外、`topic_slot` 或 `evidence_posture` 发生改变时，`sync-prewrite-plan` 返回 `SCOPE_RECONFIRM_REQUIRED` 且不得覆盖旧回执。要主动改方案，先运行 `invalidate-prewrite-confirmation --workspace <absolute-path> --reason <reason>` 留存旧回执，再取得新确认；`OWNER_PREWRITE_PLAN_CHANGES_REQUESTED` 不允许部分启动。

## 平台范围与本地化

- 没有平台映射时，G 只可创建或恢复一个可见、可复用的 `blog-3p-platform-matching` 子角色；它只在用户提供的 XLSX/表格/消息候选中做语言/市场/内容格式匹配。G 只核对来源与唯一性，不排序、不选平台。
- 当前 schema 2.11 的唯一执行配置是 `HUMAN_RELEASE_ONLY_V1` 与 `release_policy.mode = HUMAN_NATIVE_ONLY`；`machine_external_writes_allowed` 必须为 `false`。`human_release_requested` 已废弃，不能作为跳过人工发布映射的开关。`platform_scope.allowed_pairs` 只可为已确认 `owner-platform-selection.json` 的投影，不能自行授权。每篇文章在 W/R 派发前必须有一个不同的 `{platform, account}`，以及兼容的主读者语言/市场记录；每个 pair 必须有用户来源哈希、精确定位、平台原文、账号确认原文和确认 ID。
- 登录页、注册公告、编辑器行为、会话恢复、内部配置和历史记录只能说明可承接性，绝不能新增允许的平台/账号。模糊的“新增语言”或“平台不重复”请求没有平台选择授权，只能返回 `OWNER_DECISION_REQUIRED`。
- 文章语言来自用户确认。每篇 `locale_platform_validation` 必须分开记录 `primary_reader_languages`、`primary_reader_markets`、`primary_audience_evidence_path` 与 `transport_supported_content_languages`、`transport_evidence_path`。平台支持语言只决定传递资格，不能证明英语或任何语言是平台主读者语言；默认只有 `PRIMARY_AUDIENCE_MATCH` 可派发。语言/市场不匹配只能是逐篇、逐字绑定的 `CROSS_LANGUAGE_EXCEPTION_OWNER_CONFIRMED`，否则写 `PLATFORM_AUDIENCE_MISMATCH_RECONFIRM_OWNER`，不得自动翻译或改配。
- 跨语言用语顺序固定为 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`。Google Trends 如可用，只比较英文种子和英文候选，并且只是全球相对关注度背景；数据不足、无 `Breakout` 或无清晰趋势时，不得强求或阻塞，继续以当前品牌站与地区 SERP 的有边界证据选择长尾意图。两次地区 SERP 核验都没有可用共识时，才以有据模型翻译兜底。平台资料只能决定表达形式、技术深度和传递风险，不能作为关键词、自然变体、搜索意图、当地需求或热门度依据。

## 运行与交接

1. G 完成写前方案、保存并绑定用户确认回执后，运行 `check` 和 `dispatch-readiness`。前者仅证明结构可读；后者必须显示 `DISPATCH_READY`，否则先补齐明确列出的 `REQ-*`、可见项目 G 登记、每篇人工发布映射或语言/平台兼容记录，再创建独立 Git 工作区和文章专属 W/R 协作组。`build-article-context` 的 `--workspace` 始终是内容项目根目录，或包含 `campaign.json`、`state.json`、`prewrite-plan.json` 与 `requirements-contract.md` 的完整项目 Git 工作树根目录；不能使用新建的空文章目录。
2. `blog-3p-writer` 是唯一可执行 W；`blog-writer-merged` 只作编辑参考。默认路线中，W 连续完成研究、成稿、图片和交付页，然后该文同一 `blog-3p-review` 做一次独立 `FULL_REVIEW`，其中覆盖研究证据。只有冻结或 R 升级的增强路线才在正文前要求 `RESEARCH_APPROVED`；两种路线都必须有完整审稿。
3. `blog-3p-gate` 在一个 `BATCH_GATE_ACCEPTANCE` 回合中验收当前所有 R 已批准文章是否保留用户需求；每篇保留独立结论行。`blog-3p-human-handoff` 仅在该行 `HUMAN_RELEASE_READY` 后编译人工发布交接包。
4. 人工回传 `HUMAN_ACCEPTED` URL 后，校验回执并生成只读快照；复用同一项目统筹 G 的 `PUBLIC_QA_BATCH_READONLY` 回合比对当前已回传文章，不重启 W/R。

可见、可复用的角色与独立 Git 工作区是不同概念。支持独立 Git 工作区时，每篇就绪文章必须由唯一 W/R 对作为根创建可见独立 Git 工作区；全项目只登记一个可复用的 `CAMPAIGN_GATEKEEPER`。不支持时仅可使用已记录、路径互不重叠的共享工作区降级。CLI 只可执行文件读取、JSON 校验、哈希、脚本测试和版本控制等确定性本地操作，不能代替独立角色。

每次交接前运行 `scripts/harnessctl.py check --workspace <absolute-path>`。W 将最终稿交给 R 前，再运行 `check-review-ready --workspace <article-workspace> --article-contract context/article-contract.json --review-index reviews/review-index.json --article-package article-package.json`：它校验当前 article contract、review index、实际文件哈希、固定载荷、研究证据的结构边界、topic-slot 对齐和精确 CTA，防止 R 把 token 花在缺件或过期交付包上；它不是质量评分或批准。`TOPIC_EVIDENCE_CONFLICT` 只能在同一已登记 G 的可见 `TOPIC_EVIDENCE_DECISION` 记录为 `KEEP_SLOT` / `NARROW_WITHIN_SLOT` 后恢复可审，且不新增 R。当前 schema-2.11 文章包还运行 `check-article-package`、`check-handoff-manifest`，并在 G 批量验收时运行 `check-batch-gate`；它们只验证结构、哈希、正确审稿路线、人工发布映射和声明保真，不评分文章质量。标准路线要求绑定 evidence pack 的一次完整 R 审稿，不要求虚构一份提前研究审；增强路线同时要求研究审和完整审。公开回传先运行 `check-public-return-receipt`。任何修复仍回到同一 R，但有完整变更摘要时优先作边界明确的 R-Δ，而不是为单一已定位问题机械重审全文。

需要量化而不是猜测时，运行 `summarize-efficiency --workspace <campaign-workspace> [--output evidence/operations/efficiency-summary.json]`。它只读取已有任务记录；`input_tokens`、`output_tokens`、`wall_time_seconds` 和 `tool_calls` 都是可选运行时字段，缺失时明确输出 `UNAVAILABLE`，不写入文章包、不成为发布门，也不启动模型或新角色。

## 恢复

发生压缩、恢复或上下文不确定时，先重读[流程核心](../../docs/workflow-core.md)，再读取 `campaign.json`、`state.json`、`requirements-contract.md`、`reviews/review-index.json` 和当前变更文件。只有哈希漂移、问题项谱系不清、代理替换或升级时，才完整重读历史报告；在状态历史中追加 `CONTEXT_REHYDRATED`，不得推断缺失证据。

日常先以[流程核心](../../docs/workflow-core.md)和当前结构化记录行动；仅在范围冻结、恢复异常或对应风险触发时，按需读取[内容项目契约](references/campaign-contract.md)或[写前检查清单](references/pre-clearance.md)的相关段落。机器字段、状态码、命令参数与路径保持不变。
