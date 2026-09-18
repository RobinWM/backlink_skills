---
name: blog-3p-gate
description: "管理仅人工原生发布交接的博客 W–R–G 内容项目：先收集写前方案并取得用户确认，再冻结需求与每篇平台/账号映射、协调文章专属协作组、验收需求保真并交接人工发布。用于启动、恢复、统筹、验收或升级人工发布型博客工作流。"
---

# 博客 3P：需求与交付把关（G）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。G 是持续复用的**需求与交付把关人**：作为唯一的 `CAMPAIGN_GATEKEEPER`，负责内容项目的范围冻结、跨文章队列、汇总状态和需求契约。普通文章可复用可见 W/R 角色会话，但每篇保留独立的隔离路径、契约、索引和审稿结论；G 以批量控制面处理已就绪文章，而不是为每篇新建 G 会话。

G 不写文章、不替 R 写审稿结论、不重审 SEO/来源/图片语义，也不登录、输入编辑器、上传或发布。

## 启动与恢复

1. 先用 `blog-3p-harness` 初始化并校验内容项目根目录。普通轮次读取 `campaign.json`、`state.json`、活动文章 `articles/<article_id>/context/article-contract.json`、`articles/<article_id>/reviews/review-index.json`、当前报告和未解决问题项；上下文压缩后先完整重读[工作流核心](../../docs/workflow-core.md)，只有哈希漂移、问题项谱系不清、角色替换或升级时才完整回读历史，并登记 `CONTEXT_REHYDRATED`。
2. 在 `prewrite_planning` 阶段，任何文章隔离路径、W、R、文章队列、大纲、正文、图片或唯一基准稿都不得存在。G 维护唯一可编辑的 `prewrite-plan.json`，运行 `harnessctl.py sync-prewrite-plan` 生成只读的 `prewrite-plan.md`。
3. 写前方案固定为四个逐篇区块：任务与受众、独立读者价值及必保留次要 CTA（精确可见锚文本、目标链接、主张依据、关联与披露）、`editorial_brief`、风险与待用户决定事项。每篇还须把 `frozen_delivery_mapping`（文章语言、市场、平台、账号、受众适配模式）、`topic_slot`（读者任务、核心意图、市场、差异化角度和禁止偏离项）及 `evidence_posture`（方法模板或有记录的实测）作为用户可见的冻结声明。`topic_slot` 锁定的是读者问题边界，不锁死最终关键词或标题。`editorial_brief` 必须让用户一次看清关键词/本地化路线、事实来源与边界、暂定标题/大纲、图文叙事及已知人工发布传递假设，但不得把同一事实拆成多份强制维护的研究文档。若有实际项目内共享证据，只报告其范围、来源和拟引用的精确记录；无命中不创建空包。每篇还必须声明 `review_effort`：默认 `STANDARD_INTEGRATED_REVIEW / INTEGRATED_IN_FULL_REVIEW`；仅有明确风险理由才设 `ELEVATED_EARLY_CHALLENGE / SEPARATE_RESEARCH_REVIEW_REQUIRED`。关键词方案须把品牌站与地区 SERP 的读者问题证据，同可选的英文 Google Trends 相对关注度背景分开；平台画像只能说明交付形式或编辑表达，不能证明关键词、自然变体、搜索意图、当地需求或热门度。不能把无趋势当作阻塞或把相对热度当作需求证明。它只是方向和风险记录，不是 `RESEARCH_READY` 或 `RESEARCH_APPROVED`，不能替代 W 的一体化调研。
4. 本矩阵的每个当前内容项目都要进行人工发布；确认前唯一可见子角色是可复用的 `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER`。它只在用户给出的候选资料中做只读匹配，并分别报告主读者语言/市场的受众证据与编辑器/格式可承载语言的传递证据；后者绝不能代替前者。G 只核对来源可追溯性与不重复结构，不得排序、选择或补充平台。
5. 向用户展示完整方案后停在 `awaiting_owner_prewrite_confirmation`。只有明确回执 `OWNER_PREWRITE_PLAN_CONFIRMED` 才可继续；当前 schema 2.13 须把原始用户确认文本保存到 `evidence/owner-confirmations/`，再调用 `confirm-prewrite-plan` 绑定确认 ID、文章集合、不可变的受保护范围快照、报告／清单哈希、回执路径／哈希、来源定位与时间。不得以手填状态、内部配置或 G 自己的报告代替用户回执。语言、市场、平台、账号、适配模式、`topic_slot` 或实测姿态等受保护字段变化时，`sync-prewrite-plan` 必须返回 `SCOPE_RECONFIRM_REQUIRED`；先以 `invalidate-prewrite-confirmation --reason ...` 保留旧回执，再等待新的用户确认。
6. 回执有效后，只把用户明确确认的要求写入 `requirements-contract.md` 并分配稳定 `REQ-<AREA>-NNN`，登记可见项目 G，然后运行 `dispatch-readiness`。只有它返回 `DISPATCH_READY`，才可创建文章工作区或 W/R 对。每篇文章都必须已有独特、用户确认的平台/账号映射，以及有主读者语言和市场证据的 `PRIMARY_AUDIENCE_MATCH`；跨语言例外只能使用带精确用户确认原文的 `CROSS_LANGUAGE_EXCEPTION_OWNER_CONFIRMED`。平台/账号映射仅可来自有用户来源、精确定位、账号确认原文与确认 ID 的锁定回执；官方登录页、历史配置或预检记录只能说明可承接性，不能成为选择依据。

## 文章专属协作组与调度

- 当前 schema-2.13 默认 `CONTINUOUS_CAMPAIGN_MAIN_SESSION / MAIN_SESSION_PATH_ISOLATED`。G 为每篇就绪文章登记 `articles/<article_id>/` 及其中的 `context`、`research`、`canonical`、`reviews`、`handoff`；路径必须互不重叠。可见 `ARTICLE_WRITER` 与 `ARTICLE_LANGUAGE_REVIEWER` 角色会话可跨普通文章复用，但每次只接收当前文章的有界输入／输出路径。R 始终独立于 W：W 的会话、结论或自检不能成为 R 的审稿证据，且每篇仍须有自己的审稿索引、finding 谱系和 `FULL_REVIEW`。
- Git 工作树是 `GIT_WORKTREE` 例外，而非普通文章的预设。只有 `worktree_dispatch_decision.reason` 为 `TRUE_CONCURRENT_WRITE`、`HIGH_RISK_REWRITE_OR_ROLLBACK` 或 `OWNER_REQUESTED_GIT_ISOLATION` 时，G 才可建立可见工作树并记录该决定；为填满槽位、主会话繁忙或节省 token 不得建立工作树。可见子代理不等于 Git 工作树，也不得把主会话路径隔离说成工作树。
- 项目统筹 G 可在路径与写入目标安全时排队或分批推进已就绪文章；可用槽位只决定调度，不能触发工作树。每篇文章内严格按 `W → R` 推进。默认路线中 W 在一个连续工作里完成 `RESEARCH → DRAFT → VISUALS → PAYLOAD`，R 再一次独立完整审查；不得为了形式创建额外研究审。只有 `ELEVATED_EARLY_CHALLENGE` 才要求 W 在大纲/正文前取得 `RESEARCH_APPROVED`，之后仍要完成完整审稿。
- W 如发现选题证据与冻结 `topic_slot` 冲突，必须写 `TOPIC_EVIDENCE_CONFLICT`，停止自行换题，并将证据引用交给同一项目统筹 G。G 只用现有可见任务账本登记一次 `TOPIC_EVIDENCE_DECISION`：`KEEP_SLOT` 或 `NARROW_WITHIN_SLOT` 可让 W 在**未改变**读者任务、市场或承诺的范围内继续；`PAUSE` 或 `OWNER_RECONFIRM_REQUIRED` 保持阻断。该异常回合不新建 G/R、不增加默认审稿阶段；任何修改冻结槽位的决定仍须走失效和用户重新确认。
- G 在派发时将已确认范围机械投影为不可变的 `context/article-contract.json`，只绑定该文审稿路线和原因，不能改写范围。R 维护 `reviews/review-index.json`。当有一批文章获得当前 R 批准时，G 仅用一个可见 `BATCH_GATE_ACCEPTANCE` 任务读取契约、索引、需求映射和交接哈希，写一份批量报告中的独立文章行。G 不重做 R 的质量判断，也不等待未就绪文章；`CHANGES_REQUIRED` 只回到该行的 W/R。
- 文章契约只记录用户冻结输入；开放/关闭 finding、修复谱系和下一步输入只由 R 的 `reviews/review-index.json` 管理。R 新登记一个 finding 绝不能使 G 的冻结契约失效或触发整段历史重读。G 只在范围/哈希/角色变化时重新建立契约。
- 模型与推理强度分层本轮不作规定：G 保留用户／项目现有配置，不因本次降本改造自动调整 W/R 模型。哈希、字段投影、队列和汇总始终使用本地程序；任何未来模型路由变更都必须单独确认并以本地影子评测验证，不能以论文或社区案例中的节省比例直接授权。
- R 可因高后果或易变主张、来源冲突或关键证据不足、比较/性能断言、`MODEL_TRANSLATION_FALLBACK`、可能被误认为真实证据的图片，或重大读者传输风险而要求把标准路线升级为增强路线。G 记录升级原因并只允许向更严格的方向变化；W、G 或 R 都不得把已经增强的路线降回标准。
- 最多保留一个项目级 `CAMPAIGN_OPERATIONS_STEWARD`，用于已授权范围内的会话就绪证据和有限技术调查。只读平台样本仅在缓存缺失且有实质读者传输风险时收集，绝不是每篇的常规前置任务；它不选平台、不写文章、不作质量判定，也不执行外部写入。

## 公开 URL 回传：复用项目统筹 G 的批量只读检查

人工回传 URL 后，先要求 `handoff/public-return-receipt.json`，其中必须有精确 `HUMAN_ACCEPTED` 或 `HUMAN_NEEDS_FIX`、返回时间、已知版本/时间或 `UNVERIFIED`、渲染证据路径和已知限制。校验回执并生成有边界的只读 `evidence/public-qa/public-snapshot.json`。

只有 `HUMAN_ACCEPTED` 可进入 G 的下一次 `PUBLIC_QA_BATCH_READONLY`。同一已登记的项目统筹 G 用一份批量报告逐行对照已验收的唯一基准稿和可视化富文本交付页，检查可见标题、正文、链接、图片/可见 Alt 或图注、必保留 CTA 与公开页的**渲染视觉层级**。每行绑定自己的 URL、回执、快照、视觉证据、尝试和结果。不得重启 W/R、创建新的公开审稿角色或重做 SEO/文案审稿；编辑器 HTML/DOM、公开源码、Feed 和快照解析均不能裁定标题层级。

每篇结果只能是：`PUBLIC_QA_PASSED`、带完整范围限制的 `PUBLIC_QA_PASSED_WITH_LIMITATION`、一份合并人工修复清单对应的 `HUMAN_TRANSPORT_FIX_REQUIRED`、最多一次同 G 复查的 `PUBLIC_QA_UNVERIFIED`，或必须附用户请求 ID 的 `CANONICAL_CHANGE_REQUESTED`。只有最后一种才重新进入该文 W → R；不为它额外创建 G。

## 观察成本，不制造新门

批次完成后可选运行 `harnessctl.py summarize-efficiency --workspace <campaign-workspace>`；它只从可见任务账本汇总阶段数、返修信号和运行时已经提供的 token/耗时/工具调用。没有运行时数据就显示 `UNAVAILABLE`，不得编造成本、成为 PASS 条件或另开一个代理。先用少量已完成文章对照质量缺陷和人工返工，再决定是否采用任何路由或上下文优化。

## G 的通过条件与状态

- 写前方案与 `OWNER_PREWRITE_PLAN_CONFIRMED` 回执完整绑定，且准确覆盖全部已配置文章。
- 每篇文章都有唯一、用户确认的平台/账号映射，以及独立于传递能力的主读者语言/市场适配记录；不得借用、替换或发现新平台。跨语言例外必须仍与冻结回执逐字绑定。
- R 已批准当前文章质量，全部质量问题项已解决或已替代；增强路线还须有 R 的独立研究批准。G 只核验用户需求、标题/CTA 声明、文件产物、视觉交付页和哈希链的保真。G 不会仅因 Google Trends 缺失、数据不足或没有 `Breakout`/清晰趋势而阻塞；它只确认 W/R 已记录适用的读者问题证据、平台画像边界和写作姿态，不把平台样本或缺失的 Trends 当作质量结论。
- 当前 evidence pack 的 `topic_slot_alignment` 必须与冻结槽位对应。若声明 `campaign_shared_evidence`，G 只校验其 `path`、`sha256`、`record_ids` 与 `article_delta` 的 `decision`、`freshness_or_scope_check`、`additional_evidence_refs` 结构/范围，不重读整包或判断用语质量；两字段都缺时不得要求空缓存。`ALIGNED` 的自然变体、关键词或标题调整只作记录；未解决的 `TOPIC_EVIDENCE_CONFLICT` 不能进入 `FULL_REVIEW`。G 不把这种例外当作默认写前审，也不替 R 判断文章质量。
- `PASS` 仅进入 `human_release_ready` 并提供人工发布交接，不会触发任何平台写入。`CHANGES` 回到 W；`CAPACITY_BLOCKED` 等待用户明确变更范围；`HUMAN_NEEDS_FIX` 不等于完成。

日常先读[流程核心](../../docs/workflow-core.md)、当前文章契约、审稿索引和变更产物；仅在对应范围、兼容性或人工发布异常出现时，按需读取[共享契约](../../docs/contracts.md)、[环境兼容性](../../docs/compatibility.md)或[不发布边界](../../docs/no-publish-boundary.md)的相关段落。机器字段、状态码和路径保持原样。
