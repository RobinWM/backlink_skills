# 已退出技能入口：blog-harness

此目录仅保留内部工具或旧项目资料，不是独立技能。新任务按[当前入口参考](../../docs/legacy-workflow-core.md)执行；下面的旧字段/状态链仅用于历史项目，不得加入新任务日常流程。

# 博客：本地流程工具

先阅读[术语约定](../../docs/terminology.zh-CN.md)。本技能负责可恢复的本地工作区和机械校验，不代替编辑判断、平台发布或人工原生编辑器操作。

完整任务顺序以[流程核心](../../docs/workflow-core.md)为准。本工具承接接收任务、写前方案、确认绑定、文章路径、交付及回传记录，不只校验成稿。每次启动新任务复用已有一次性准备清单，让用户一次看清必要资料与人工动作；不新增同义表单。等待用户确认或人工发布时保存状态并结束当前执行，不反复运行检查；只在输入/文件变化、交接或恢复时作相应校验。

## 初始化

运行 `scripts/harnessctl.py init --workspace <absolute-path> --campaign-id <id>`。它只创建本地文件：`campaign.json`、`state.json`、`confirmation.md`、`requirements-contract.md`、唯一可编辑的 `prewrite-plan.json`、确定性只读视图 `prewrite-plan.md`、一次性 `pre-clearance-checklist.md` 及标准证据/输出目录。当前 schema-2.14 工作区使用写前方案 schema `1.8`、evidence pack schema `1.3` 和 `article-package.json@1.5`，默认持续主会话及 `articles/<article_id>/{context,research,canonical,reviews,handoff}` 路径隔离，并保存原始用户确认回执；schema-2.13 的独立 R 及更早版本按各自历史规则读取/校验，不自动转成 WQ。当前工作区只支持人工原生发布交接；脚本绝不执行平台写入。

## 写前方案与用户确认

共享必保留主词可在原 `prewrite-plan.json.keyword_requirements` 声明；短语、范围、本地化权限与保护含义进入已有确认范围，修改或删除须重新确认。工具投影到文章契约，在原预检与 G 批量验收按已冻结的 `title_mode` 检查；默认新要求明确填写 `MEANING_PRESERVING`，仅用户锁定原文才用 `COMPLETE_PHRASE`。含义与同质化由原质量角色判断，不用作者新字段重新定义要求。空数组/缺省保留旧项目兼容。格式与边界见[关键词要求](../../docs/keyword-requirements.md)。

G 的第一阶段是 `prewrite_planning`。在用户确认前，不得存在文章隔离路径、W/R 派发、文章队列、大纲、正文、图片、唯一基准稿或文章调研子角色。G 编辑 `prewrite-plan.json` 后运行 `sync-prewrite-plan`，再向用户展示生成的 `prewrite-plan.md`；Markdown 是只读视图，禁止双份手填。

每篇方案卡固定为四个可读区块：任务/受众；独立读者价值和必保留次要 CTA；`editorial_brief`；风险与待用户决定事项。还须展示 `frozen_delivery_mapping`、`topic_slot`（读者任务、核心意图、市场、差异化角度、禁止偏离项）和 `evidence_posture`。`topic_slot` 不自动锁最终标题；用户必保留主词另在共享要求中冻结，未锁定候选词才可调整。`editorial_brief` 汇总关键词/本地化路径、事实边界、暂定结构、图文叙事与人工传递假设，不双份维护研究。只展示实际共享证据。冻结 `review_effort`：默认 `AUTHOR_QA_INTEGRATED / WQ_SHARED_CONTEXT / INTEGRATED_IN_AUTHOR_QA`；只有用户明确选择并记录 `OWNER_EXPLICIT_INDEPENDENT_REVIEW` 时才用 `INDEPENDENT_R_ESCALATION / WR_INDEPENDENT`。具体风险只写入待用户决定事项，不能自动选择 WR；只有用户同时确认时，WR 才追加独立研究审。不可证实的内容标 `UNVERIFIED` 并说明风险；写前方案不等于研究批准，W 仍要一体化研究。

只有明确的 `OWNER_PREWRITE_PLAN_CONFIRMED` 才允许启动文章任务。当前 schema 2.14 须先保存用户确认原文到 `evidence/owner-confirmations/`，再运行 `confirm-prewrite-plan --confirmation-id ... --receipt-file ... --receipt-type OWNER_MESSAGE|OWNER_FILE --source-locator ...`。该命令绑定文章集合、计划/回执哈希、受保护范围及来源/时间；手工改状态不能提升方案。语言、市场、平台、账号、适配模式、跨语言例外、`topic_slot` 或写作姿态变化时，`sync-prewrite-plan` 返回 `SCOPE_RECONFIRM_REQUIRED` 且保留旧回执；须显式失效后取得新确认。`OWNER_PREWRITE_PLAN_CHANGES_REQUESTED` 不允许部分启动。

## 平台范围与本地化

- 没有平台映射时，G 复用只读 `blog-platform-matching` 服务核对用户候选；只读调研后可按[账号准备](../../docs/account-preparation.md)复用一个获授权的运营服务完成注册/登录及最低必要设置。两项都不派 W/R、不写文章。G 核对来源、唯一性与用户要求，不排序、不选平台。
- 当前 schema 2.14 只使用 `HUMAN_RELEASE_ONLY_V1` 与 `release_policy.mode = HUMAN_NATIVE_ONLY`；发布层 `machine_external_writes_allowed = false` 保持不变。账号准备使用独立、逐目标的授权记录与 `check_account_preparation.py` 本地校验，不能把发布开关改为 true。它不执行浏览器操作，也不验证发布成功。`human_release_requested` 不能跳过映射确认。`platform_scope.allowed_pairs` 仅投影用户最终确认的选择；每篇不同映射、受众记录及来源回执要求不变。
- 登录页、注册公告、编辑器行为、会话恢复、内部配置和历史记录只能说明可承接性，绝不能新增允许的平台/账号。模糊的“新增语言”或“平台不重复”请求没有平台选择授权，只能返回 `OWNER_DECISION_REQUIRED`。
- 文章语言来自用户确认。每篇 `locale_platform_validation` 必须分开记录 `primary_reader_languages`、`primary_reader_markets`、`primary_audience_evidence_path` 与 `transport_supported_content_languages`、`transport_evidence_path`。平台支持语言只决定传递资格，不能证明英语或任何语言是平台主读者语言；默认只有 `PRIMARY_AUDIENCE_MATCH` 可派发。语言/市场不匹配只能是逐篇、逐字绑定的 `CROSS_LANGUAGE_EXCEPTION_OWNER_CONFIRMED`，否则写 `PLATFORM_AUDIENCE_MISMATCH_RECONFIRM_OWNER`，不得自动翻译或改配。
- 跨语言用语顺序固定为 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`。Google Trends 如可用，只比较英文种子和英文候选，并且只是全球相对关注度背景；数据不足、无 `Breakout` 或无清晰趋势时，不得强求或阻塞，继续以当前品牌站与地区 SERP 的有边界证据选择长尾意图。两次地区 SERP 核验都没有可用共识时，才以有据模型翻译兜底。平台资料只能决定表达形式、技术深度和传递风险，不能作为关键词、自然变体、搜索意图、当地需求或热门度依据。

## 运行与交接

1. G 完成写前方案、保存并绑定用户确认回执后，运行 `check` 和 `dispatch-readiness`。前者仅证明结构可读；后者必须显示 `DISPATCH_READY`，否则先补齐明确列出的 `REQ-*`、可见项目 G 登记、每篇人工发布映射或语言/平台兼容记录，再创建 `articles/<article_id>/` 的隔离交付路径并派发可见 W/R。`build-article-context` 的 `--workspace` 始终是含 `campaign.json`、`state.json`、`prewrite-plan.json` 与 `requirements-contract.md` 的内容项目根目录；文章产物由其下的确定性 `articles/<article_id>/` 路径承接，不能使用新建的空目录作为内容项目根。
2. `blog-writer` 是唯一可执行 W；`blog-writer-merged` 只作编辑参考。W 连续完成研究、成稿、图片和双载荷，再以 `CANDIDATE_LOCK → ADVERSARIAL_SELF_QA → TARGETED_REPAIR → FINAL_BIND` 自查本篇证据、正文、CTA、图文语义与载荷并绑定最终哈希。默认 WQ 只可登记 `AUTHOR_QA_READY`，不生成独立 R 的 `APPROVED`。只有用户明确选择 WR 时，独立 R 才作一次 `FULL_REVIEW`；高风险 finding 只能让 G 请求用户决定，不能自动派 R。仅用户已确认的 WR 才可另加成文前研究审。机械投影校验正常只语义读 HTML，`COMPANION_DUAL_READ_REQUIRED` 才双读 Markdown。
3. `blog-gate` 在一个 `BATCH_GATE_ACCEPTANCE` 回合中验收当前所有具备适用质量凭据的文章：WQ 是 W 的可见 `AUTHOR_QA_READY` 哈希回执，WR 是独立 R 的 `APPROVED`；若用户后来明确把 WQ 改为 WR，必须重新绑定路线后才可使用后者。每篇保留独立结论行。W 在质量核验前编译交付页；`blog-human-handoff` 仅在 `HUMAN_RELEASE_READY` 后生成派生清单，不改写已核验载荷。
4. 人工回传 `HUMAN_ACCEPTED` URL 后，校验回执并生成只读快照；复用同一项目统筹 G 的 `PUBLIC_QA_BATCH_READONLY` 回合比对当前已回传文章，不重启 W/R。

可见角色会话、文章路径隔离与 Git 工作树是不同概念。默认持续主会话统筹与文章路径隔离，不限制为一个 W；多个独立就绪文章优先由可复用的多个可见 W 安全并行，WR 才激活独立于 W 的 R。每篇只读写自己的 `articles/<article_id>/`；全项目只登记一个 G，项目级状态、确认、队列和共享证据仅由 G 写入。执行会修改公共文件的流程命令时交 G 串行完成，不让多个作者抢写状态；只读检查和各自文章内的编译可并行。Git 工作树只在记录真实并发写入、高风险重写/回滚或用户要求 Git 隔离时允许，槽位或 token 节省不是理由。CLI 只可执行确定性本地操作，不能冒充可见 WQ/WR 质量任务。

每次交接前运行 `scripts/harnessctl.py check --workspace <campaign-root>`。在 WQ 最终自查或 WR `FULL_REVIEW` 前，W 以内容项目根运行 `check-review-ready --workspace <campaign-root> --article-contract articles/<article_id>/context/article-contract.json --review-index articles/<article_id>/reviews/review-index.json --article-package articles/<article_id>/article-package.json`。它只校验身份、哈希、来源引用结构、固定载荷、冻结 CTA 与伴随投影，不作质量批准。`TOPIC_EVIDENCE_CONFLICT` 须同一 G 的有据决策后才能恢复。当前 schema-2.14 再运行 `check-article-package`、`check-handoff-manifest`、G 批量 `check-batch-gate`；它们验证适用质量凭据：WQ `AUTHOR_QA_READY`、WR 独立 `APPROVED`，不评分文章。WQ 改稿/改图/改载荷重跑同一 W 的完整自查并换新回执，不走 R-Δ；WR 的有限修复才可由同一 R 作有边界 R-Δ。公开回传先校验 receipt。

需要量化而不是猜测时，运行 `summarize-efficiency --workspace <campaign-workspace> [--output evidence/operations/efficiency-summary.json]`。它只读取已有任务记录；`input_tokens`、`output_tokens`、`wall_time_seconds` 和 `tool_calls` 都是可选运行时字段，缺失时明确输出 `UNAVAILABLE`，不写入文章包、不成为发布门，也不启动模型或新角色。

## 恢复

发生压缩、恢复或上下文不确定时，先重读[流程核心](../../docs/workflow-core.md)，再读取 `campaign.json`、`state.json`、`requirements-contract.md`、当前文章的 `articles/<article_id>/context/article-contract.json` 与 `articles/<article_id>/reviews/review-index.json`，以及当前变更文件。只有哈希漂移、问题项谱系不清、代理替换或升级时，才完整重读历史报告；在状态历史中追加 `CONTEXT_REHYDRATED`，不得推断缺失证据。

日常先以[流程核心](../../docs/workflow-core.md)和当前结构化记录行动；仅在范围冻结、恢复异常或对应风险触发时，按需读取[内容项目契约](references/campaign-contract.md)或[写前检查清单](references/pre-clearance.md)的相关段落。机器字段、状态码、命令参数与路径保持不变。
