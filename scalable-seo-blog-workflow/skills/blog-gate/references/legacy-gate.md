# 旧 G 接口：仅已有 campaign.json 项目

此文不是新任务流程；新任务以当前 SKILL.md 和短流程为准。不得据此追加日常门禁。

# 博客：需求与交付把关（G）

先阅读[术语约定](../../../docs/terminology.zh-CN.md)。G 是持续复用的**需求与交付把关人**：作为唯一的 `CAMPAIGN_GATEKEEPER`，负责范围冻结、跨文章队列、汇总状态和需求契约。普通文章走可见 W 的同上下文 WQ 自查；只有用户明确选择独立审稿的文章才激活 WR 的 R。每篇保留隔离路径、契约、索引和与路线相符的质量结论；G 以批量控制面处理已就绪文章。

G 不写文章、不替 WQ/R 写质量结论、不重审 SEO/来源/图片语义，不输入文章编辑器、上传文章图片或发布。写前账号注册/登录及最低必要设置仅按[账号准备](../../../docs/account-preparation.md)的独立用户授权执行，不能打开自动发布权限。

效率与质量是同等目标，执行[工作流核心](../../../docs/workflow-core.md)的“效率与质量同等重要”。有多个已确认、已就绪且路径独立的文章时，优先多个可见 W 子代理并行，复用原代理修复和接续任务；不默认一个 W 串行包办全批，也不按文章总数一次开满。G 独占项目级状态、确认、队列、共享证据和汇总的写入，代理只写获派文章路径。每篇仍按已选路线一次质量核验，不增加重复审稿；单篇或不适合并行时复用现有角色。

完整任务按[工作流核心](../../../docs/workflow-core.md)的“整个博客任务的固定顺序”推进，覆盖接收、只读调研、一次确认、任务安排、成稿核验、交付、人工发布等待、公开复核和记录保存；不把规则局限于写作。G 冻结用户明确要求和选题边界，不把暂定大纲、模型示例或经验性 SEO 指标升级成硬要求；模型在范围内选择写法不新增确认或质量回合。每次新任务给出一次性准备清单，确认后逐篇推进，单篇受阻不拖住其他已确认文章；不擅改总量或平台。等待人工操作时保存状态并结束执行，不重复审稿或轮询。

## 启动与恢复

写前在原方案说明品牌参考、正文图外的独立封面，以及从首页推送/Trending/Popular/Featured 等实际文章得到的平台主流语言观察。未指定语言时据此建议，用户指定语言冲突时先报告，在用户提供的平台范围内调整映射或由用户确认调整语言，不强投、不新增跨语言例外绕过冲突。G 交付核需求保真，不重做文章审稿；多锚多链接保留用户约定并如实报政策风险，不保证零误判。

写前先把关键词分为必保留主词、研究种子和文章角度；新任务默认 `title_mode = MEANING_PRESERVING`，共享核心含义而不统一标题前缀，只有用户明确锁定原文才用 `COMPLETE_PHRASE`。旧确认的方式不得静默放宽。必保留主词及范围在原 `prewrite-plan.json.keyword_requirements` 保存一次，源于用户原文而非作者选词；工具在原方案展示并投影到文章。候选词和角度不全部升级为要求，共同主词也不为“各篇不同”而替换。G 批量验收对照继承要求，不只看作者的字段，不重审语义或新增确认轮。见[关键词要求](../../../docs/keyword-requirements.md)。

1. 先用 `blog-harness` 初始化并校验内容项目根目录。普通轮次读取 `campaign.json`、`state.json`、活动文章 `articles/<article_id>/context/article-contract.json`、`articles/<article_id>/reviews/review-index.json`、当前报告和未解决问题项；上下文压缩后先完整重读[工作流核心](../../../docs/workflow-core.md)，只有哈希漂移、问题项谱系不清、角色替换或升级时才完整回读历史，并登记 `CONTEXT_REHYDRATED`。
2. 在 `prewrite_planning` 阶段，任何文章隔离路径、W、R、文章队列、大纲、正文、图片或唯一基准稿都不得存在。G 维护唯一可编辑的 `prewrite-plan.json`，运行 `harnessctl.py sync-prewrite-plan` 生成只读的 `prewrite-plan.md`。
3. 写前方案固定为四个逐篇区块：任务与受众、独立读者价值及必保留次要 CTA（精确锚文本、目标链接、主张依据和披露）、`editorial_brief`、风险与待用户决定事项。将 `frozen_delivery_mapping`、`topic_slot`（读者任务、核心意图、市场、差异化角度和禁止偏离项）及 `evidence_posture` 作为可见冻结声明；`topic_slot` 不自动锁最终标题；用户必保留主词另在共享要求中冻结，研究种子和标题附加措辞才可自主优化。`editorial_brief` 让用户一次看清关键词/本地化、事实边界、暂定结构、图文叙事与人工传递假设，避免重复研究文档。只引用实际共享证据命中。每篇默认 `AUTHOR_QA_INTEGRATED / WQ_SHARED_CONTEXT / INTEGRATED_IN_AUTHOR_QA`；只有用户明确选择独立 R，且在 `review_effort.reasons` 记录 `OWNER_EXPLICIT_INDEPENDENT_REVIEW`，才设 `INDEPENDENT_R_ESCALATION / WR_INDEPENDENT`。重大风险写入“待用户决定事项”，不能替代这项选择。仅用户明确选择的 WR 才可加 `SEPARATE_RESEARCH_REVIEW_REQUIRED`。品牌站和地区 SERP 的读者问题证据须与可选英文 Google Trends 背景分开；平台画像不能证明关键词、自然变体、当地需求或热门度。方案只是方向，不替代 W 的一体化调研。
4. 本矩阵的每个当前内容项目都要进行人工发布；确认前可见服务仅有复用的只读 `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` 与明确授权的账号准备 `CAMPAIGN_OPERATIONS_STEWARD`，不得提前派 W/R。匹配角色按[平台匹配技能](../../blog-platform-matching/REFERENCE.md)比较受众/政策、品牌展示、实际入口及人工成本；账号准备按[账号准备](../../../docs/account-preparation.md)在只读调研后、完整方案确认前处理拟用账号。先收齐具体平台/身份、注册或登录、必要发布空间创建、邮箱及浏览器授权，复用一个服务依次执行；单平台短检查可由 G 执行。最低设置就停，装修/付费/持续试错不默认继续。G 核对来源、不重复结构、用户要求，将两类结果引用进原 `task_and_audience` / `risks_and_owner_decisions` 和 `evidence_refs`，不重做调研或增添审稿。账号授权不替代映射确认，`founder` 不证明账号或权限；未知/受阻项如实展示，用户可在完整方案明确选择带账号风险继续本地写作。
5. 向用户展示完整方案后停在 `awaiting_owner_prewrite_confirmation`。只有明确回执 `OWNER_PREWRITE_PLAN_CONFIRMED` 才可继续；当前 schema 2.14 须把用户原文保存到 `evidence/owner-confirmations/`，再运行 `confirm-prewrite-plan` 绑定确认 ID、文章集合、受保护范围、报告/清单及回执哈希、来源与时间。不得以内部状态或 G 报告代替用户回执。语言、市场、平台、账号、适配模式、`topic_slot` 或实测姿态变化时须失效旧确认并等待新确认。
6. 回执有效后，只把用户明确确认的要求写入 `requirements-contract.md` 并分配稳定 `REQ-<AREA>-NNN`，登记可见项目 G，然后运行 `dispatch-readiness`。只有它返回 `DISPATCH_READY`，才可创建文章工作区或 W/R 对。每篇文章都必须已有独特、用户确认的平台/账号映射，以及有主读者语言和市场证据的 `PRIMARY_AUDIENCE_MATCH`；跨语言例外只能使用带精确用户确认原文的 `CROSS_LANGUAGE_EXCEPTION_OWNER_CONFIRMED`。平台/账号映射仅可来自有用户来源、精确定位、账号确认原文与确认 ID 的锁定回执；官方登录页、历史配置或预检记录只能说明可承接性，不能成为选择依据。

## 文章专属协作组与调度

- 当前 schema-2.14 默认 `CONTINUOUS_CAMPAIGN_MAIN_SESSION / MAIN_SESSION_PATH_ISOLATED`。G 为每篇就绪文章登记互不重叠的 `articles/<article_id>/` 路径。WQ 只需可见 `ARTICLE_WRITER` 会话，且每篇须有自己的审稿索引、finding 谱系和 `AUTHOR_QA_READY` 凭据；WR 才需与 W 身份不同的可见 `ARTICLE_LANGUAGE_REVIEWER` 及本篇 `FULL_REVIEW`。同上下文作者自查绝不记为独立 R 批准。
- Git 工作树是 `GIT_WORKTREE` 例外，而非普通文章的预设。只有 `worktree_dispatch_decision.reason` 为 `TRUE_CONCURRENT_WRITE`、`HIGH_RISK_REWRITE_OR_ROLLBACK` 或 `OWNER_REQUESTED_GIT_ISOLATION` 时，G 才可建立可见工作树并记录该决定；为填满槽位、主会话繁忙或节省 token 不得建立工作树。可见子代理不等于 Git 工作树，也不得把主会话路径隔离说成工作树。
- 项目统筹 G 优先让路径与写入目标独立的就绪文章安全并行，运行容量不足时排队；一篇完成即可由原代理接下一篇，不等全批。涉及公共文件的命令由 G 串行执行；槽位只决定调度，不能触发工作树。WQ 为 `W: RESEARCH → DRAFT → VISUALS → PAYLOAD → CANDIDATE_LOCK → ADVERSARIAL_SELF_QA → TARGETED_REPAIR → FINAL_BIND`，结果仅为 `AUTHOR_QA_READY` 或 `OWNER_DECISION_REQUIRED`；后者不得注册 R。WR 是用户明确选择后连续 W 再接独立 R `FULL_REVIEW`。只有用户明确选择的 WR 成文前证据挑战才要求 `RESEARCH_APPROVED`，不得为了形式创建研究审。
- W 如发现选题证据与冻结 `topic_slot` 冲突，必须写 `TOPIC_EVIDENCE_CONFLICT`，停止自行换题，并将证据引用交给同一项目统筹 G。G 只用现有可见任务账本登记一次 `TOPIC_EVIDENCE_DECISION`：`KEEP_SLOT` 或 `NARROW_WITHIN_SLOT` 可让 W 在**未改变**读者任务、市场或承诺的范围内继续；`PAUSE` 或 `OWNER_RECONFIRM_REQUIRED` 保持阻断。该异常回合不新建 G/R、不增加默认审稿阶段；任何修改冻结槽位的决定仍须走失效和用户重新确认。
- G 在派发时将已确认范围机械投影为不可变的 `context/article-contract.json`，只绑定该文质量路线和原因。适用质量角色维护 `reviews/review-index.json`。当一批文章有当前质量凭据时，G 用一个可见 `BATCH_GATE_ACCEPTANCE` 任务读取契约、索引、需求映射和交接哈希：WQ 行须有 W 的可见 `AUTHOR_QA` 回执、最终哈希和零开放问题；用户明确选择的 WR 行须有独立 R 的 `APPROVED`，含适用研究审及 Delta。`OWNER_DECISION_REQUIRED` 行不得验收或交接。G 不重做语义判断，也不等待未就绪文章；问题只回到受影响路线。
- 文章契约只记录用户冻结输入；开放/关闭 finding、路线升级、修复谱系和下一步输入记在 `reviews/review-index.json`。WQ 的真实 finding 或 WR 的 R finding 不会使 G 的冻结契约失效；G 只在范围/哈希/角色变化时重建适用绑定。
- 模型与推理强度分层本轮不作规定：G 保留用户／项目现有配置，不因本次降本改造自动调整 W/R 模型。哈希、字段投影、队列和汇总始终使用本地程序；任何未来模型路由变更都必须单独确认并以本地影子评测验证，不能以论文或社区案例中的节省比例直接授权。
- 只有用户明确要求独立审稿，G 才可冻结 `INDEPENDENT_R_ESCALATION`。重大高后果或易变主张、来源冲突或核心证据不足、无依据的比较/性能/排名、误导性图片或实测、CTA 主张依据不清、重大传递风险，以及 WQ 无法关闭的核心问题，必须由 W 记录稳定 finding ID、候选哈希和证据边界，并由 G 报为 `OWNER_DECISION_REQUIRED`；它们不是自动拉起 R 的条件。普通本地化、缺少 Trends、例行 CTA 或有边界的 `MODEL_TRANSLATION_FALLBACK` 本身都不单独阻断。
- 最多保留一个项目级 `CAMPAIGN_OPERATIONS_STEWARD`，复用处理有独立用户授权的账号准备，以及有限会话恢复/只读调查；不按平台或阶段开一次性代理。其外部操作仅限[账号准备](../../../docs/account-preparation.md)白名单，不选平台、不写文章、不作质量判定、不碰稿件发布。账号等待只影响该目标，不阻塞其他已授权准备；完整方案确认前仍不写稿。只读平台样本仅在缓存缺失且有实质传递风险时收集。

## 公开 URL 回传：复用项目统筹 G 的批量只读检查

人工回传 URL 和接受/需修复结论后，G 整理为 `handoff/public-return-receipt.json`；不要求用户填写内部 JSON。回执必须有精确 `HUMAN_ACCEPTED` 或 `HUMAN_NEEDS_FIX`、返回时间、已知版本/时间或 `UNVERIFIED`、实际取得的渲染证据路径和已知限制。缺少必要信息时只询问缺项；不得把一个裸 URL 擅自视为人工接受。校验回执并生成有边界的只读 `evidence/public-qa/public-snapshot.json`。

只有 `HUMAN_ACCEPTED` 可进入 G 的下一次 `PUBLIC_QA_BATCH_READONLY`。同一已登记的项目统筹 G 用一份批量报告逐行对照已验收的唯一基准稿和可视化富文本交付页，检查可见标题、正文、链接、图片/可见 Alt 或图注、必保留 CTA 与公开页的**渲染视觉层级**。每行绑定自己的 URL、回执、快照、视觉证据、尝试和结果。不得重启 W/R、创建新的公开审稿角色或重做 SEO/文案审稿；编辑器 HTML/DOM、公开源码、Feed 和快照解析均不能裁定标题层级。

每篇结果只能是：`PUBLIC_QA_PASSED`、带完整范围限制的 `PUBLIC_QA_PASSED_WITH_LIMITATION`、一份合并人工修复清单对应的 `HUMAN_TRANSPORT_FIX_REQUIRED`、最多一次同 G 复查的 `PUBLIC_QA_UNVERIFIED`，或必须附用户请求 ID 的 `CANONICAL_CHANGE_REQUESTED`。只有最后一种才按该文当前 WQ/WR 路线重开质量环节；不额外创建 G。

## 观察成本，不制造新门

批次完成后可选运行 `harnessctl.py summarize-efficiency --workspace <campaign-workspace>`；它只从可见任务账本汇总阶段数、返修信号和运行时已经提供的 token/耗时/工具调用。没有运行时数据就显示 `UNAVAILABLE`，不得编造成本、成为 PASS 条件或另开一个代理。先用少量已完成文章对照质量缺陷和人工返工，再决定是否采用任何路由或上下文优化。

## G 的通过条件与状态

对照原用户要求核最终交付，不只接收 W/R 的自评：确认平台/语言、关键词保护含义、必需 CTA 与披露、数量约定、封面/正文图和可用入口没有遗漏。程序检查数量、文件和一致性，质量角色判断正文与图片；G 正常不重做研究、全文审稿或润色。若发现具体错误证据，交原 WQ 作者或已选 WR 的 R 定向处理，不为偏好追加一轮；短回执足够，不另写全绿报告。

- 写前方案与 `OWNER_PREWRITE_PLAN_CONFIRMED` 回执完整绑定，且准确覆盖全部已配置文章。
- 每篇文章都有唯一、用户确认的平台/账号映射，以及独立于传递能力的主读者语言/市场适配记录；不得借用、替换或发现新平台。旧跨语言回执只作历史兼容；新任务发现语言相悖先回用户决定，不能新增例外来绕过适配要求。
- WQ 必须有 W 同上下文对抗式自查后的 `AUTHOR_QA_READY`、可见任务回执、当前全部交付哈希和零开放问题；用户明确选择的 WR 须有独立 R 的 `APPROVED`，仅明确选择的额外研究挑战才须研究批准。G 只核验用户需求、标题/CTA 声明、文件产物、交付页和哈希链，不把 WQ 记成 R 批准，也不因 Trends 无结果而阻塞或重做质量判断。
- 当前 evidence pack 的 `topic_slot_alignment` 必须与冻结槽位对应。若声明 `campaign_shared_evidence`，G 只校验其引用与本篇差异的结构/范围，不重读整包或判断用语质量；无引用不要求空缓存。`ALIGNED` 的自然变体、关键词或标题调整只作记录；未解决的 `TOPIC_EVIDENCE_CONFLICT` 不能进入适用的 WQ/WR 最终质量门。G 不把例外当作默认写前审。
- `PASS` 仅进入 `human_release_ready` 并提供人工发布交接，不会触发任何平台写入。`CHANGES` 回到 W；`CAPACITY_BLOCKED` 等待用户明确变更范围；`HUMAN_NEEDS_FIX` 不等于完成。

日常先读[流程核心](../../../docs/workflow-core.md)、当前文章契约、审稿索引和变更产物；仅在对应范围、兼容性或人工发布异常出现时，按需读取[共享契约](../../../docs/contracts.md)、[环境兼容性](../../../docs/compatibility.md)或[不发布边界](../../../docs/no-publish-boundary.md)的相关段落。机器字段、状态码和路径保持原样。
