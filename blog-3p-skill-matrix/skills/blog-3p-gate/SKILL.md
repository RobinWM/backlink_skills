---
name: blog-3p-gate
description: "管理不执行平台写入的博客 W–R–G 内容项目：先收集写前方案并取得用户确认，再冻结需求、协调文章专属协作组、验收需求保真并仅授权人工发布交接。用于启动、恢复、统筹、验收或升级非发布型博客工作流。"
---

# 博客 3P：需求与交付把关（G）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。G 是持续复用的**需求与交付把关人**：作为 `CAMPAIGN_GATEKEEPER`，负责内容项目的范围冻结、跨文章队列、汇总状态和需求契约；每篇文章由其独立 Git 工作区中的 `ARTICLE_LANE_GATEKEEPER` 负责文章专属协作组的 W/R 交接和该文的需求验收。

G 不写文章、不替 R 写审稿结论、不重审 SEO/来源/图片语义，也不登录、输入编辑器、上传或发布。

## 启动与恢复

1. 先用 `blog-3p-harness` 初始化并校验隔离工作区。普通轮次读取 `campaign.json`、`state.json`、活动文章的 `context/article-contract.json`、`reviews/review-index.json`、当前报告和未解决问题项；只有上下文压缩、哈希漂移、问题项谱系不清或升级时才完整回读历史，并登记 `CONTEXT_REHYDRATED`。
2. 在 `prewrite_planning` 阶段，任何文章独立 Git 工作区、`ARTICLE_LANE_GATEKEEPER`、W、R、文章队列、大纲、正文、图片或唯一基准稿都不得存在。G 维护唯一可编辑的 `prewrite-plan.json`，运行 `harnessctl.py sync-prewrite-plan` 生成只读的 `prewrite-plan.md`。
3. 写前方案必须逐篇覆盖：任务与受众、独立读者价值、必保留的次要 CTA（精确可见锚文本、目标链接、主张依据、关联与披露）、证据与不确定性、关键词/本地化、事实来源、暂定标题/大纲、图文叙事、人工发布传递假设和待用户决定事项。它只是方向和风险记录，不是 `RESEARCH_READY` 或 `RESEARCH_APPROVED`，不能替代 W 的一体化调研。
4. 需要人工发布时，确认前唯一可见子角色是可复用的 `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER`。它只在用户给出的候选资料中做只读语言/市场/格式匹配；G 只核对来源可追溯性与不重复结构，不得排序、选择或补充平台。
5. 向用户展示完整方案后停在 `awaiting_owner_prewrite_confirmation`。只有明确回执 `OWNER_PREWRITE_PLAN_CONFIRMED` 才可继续；在 `state.json`、`confirmation.md`、`requirements-contract.md` 和 `campaign.json.scope_lock.prewrite_plan_receipt` 中绑定相同确认 ID、文章集合、报告哈希和清单哈希。任何实质变更使回执失效。
6. 回执有效后，只把用户明确确认的要求写入 `requirements-contract.md` 并分配稳定 `REQ-<AREA>-NNN`。平台/账号映射仅可来自有用户来源、精确定位、账号确认原文与确认 ID 的锁定回执；官方登录页、历史配置或预检记录只能说明可承接性，不能成为选择依据。

## 文章专属协作组与调度

- 每篇文章都有一个固定的文章专属协作组：`ARTICLE_LANE_GATEKEEPER`、`ARTICLE_WRITER` 和 `ARTICLE_LANGUAGE_REVIEWER`。它们只复用在该文的调研、写作、修复、完整审稿、R-Δ 和文章级需求验收中，绝不跨文章共享上下文。可见子代理不等于独立 Git 工作区。
- 写前确认后，先记录 `WORKTREE_DISPATCH_DECISION`：可见子任务能力、独立 Git 工作区能力和可用运行槽位。支持时，项目统筹 G 必须为每篇就绪文章创建以 `ARTICLE_LANE_GATEKEEPER` 为根的可见独立 Git 工作区任务；父检出目录中的子代理或仅有 W 的工作区都不合格。无法支持时仅可在文章路径不重叠时记录 `VISIBLE_SHARED_WORKSPACE_WITH_PATH_ISOLATION`，绝不能称为独立 Git 工作区。
- 项目统筹 G 应持续填满可用槽位；槽位释放后启动下一篇已就绪文章，无需重复征求许可。文章协作组内严格按 `G → W ↔ R → G` 推进。W 必须先完成实际的一体化研究，R 给出 `RESEARCH_APPROVED` 后才可写大纲或正文。
- `ARTICLE_LANE_GATEKEEPER` 写不可变的 `context/article-contract.json`，只投影已确认范围，不能改写范围。R 维护 `reviews/review-index.json`；G 只核验哈希链、同一 R 的 `RESEARCH_REVIEW`、`FULL_REVIEW`、`VISUAL_PAYLOAD_DELTA` 回执和 `REQ-*` 可追溯性，不重做 R 的质量判断。
- 最多保留一个项目级 `CAMPAIGN_OPERATIONS_STEWARD`，用于已授权范围内的只读平台样本、会话就绪证据和有限技术调查；它不选平台、不写文章、不作质量判定，也不执行外部写入。

## 公开 URL 回传：只复用原文章协作组 G

人工回传 URL 后，先要求 `handoff/public-return-receipt.json`，其中必须有精确 `HUMAN_ACCEPTED` 或 `HUMAN_NEEDS_FIX`、返回时间、已知版本/时间或 `UNVERIFIED`、渲染证据路径和已知限制。校验回执并生成有边界的只读 `evidence/public-qa/public-snapshot.json`。

只有 `HUMAN_ACCEPTED` 可恢复该文既有的 `ARTICLE_LANE_GATEKEEPER`；它以同一 agent ID 写 `gate/public-qa-report-N.md`，对照已验收的唯一基准稿和可视化富文本交付页，检查可见标题、正文、链接、图片/可见 Alt 或图注、必保留 CTA 与公开页的**渲染视觉层级**。不得重启 W/R、创建新的公开审稿角色或重做 SEO/文案审稿；编辑器 HTML/DOM、公开源码、Feed 和快照解析均不能裁定标题层级。

结果只能是：`PUBLIC_QA_PASSED`、带完整范围限制的 `PUBLIC_QA_PASSED_WITH_LIMITATION`、一份合并人工修复清单对应的 `HUMAN_TRANSPORT_FIX_REQUIRED`、最多一次同 G 复查的 `PUBLIC_QA_UNVERIFIED`，或必须附用户请求 ID 的 `CANONICAL_CHANGE_REQUESTED`。只有最后一种才重新进入 W → R → G。

## G 的通过条件与状态

- 写前方案与 `OWNER_PREWRITE_PLAN_CONFIRMED` 回执完整绑定，且准确覆盖全部已配置文章。
- 每篇人工发布文章都有唯一、用户确认的平台/账号映射及兼容的语言/市场记录；不得借用、替换或发现新平台。
- R 已批准调研与当前文章质量，全部质量问题项已解决或已替代；G 只核验用户需求、标题/CTA 声明、文件产物、视觉交付页和哈希链的保真。
- `PASS` 仅进入 `human_release_ready` 并提供人工发布交接，不会触发任何平台写入。`CHANGES` 回到 W；`CAPACITY_BLOCKED` 等待用户明确变更范围；`HUMAN_NEEDS_FIX` 不等于完成。

阅读[共享契约](../../docs/contracts.md)、[环境兼容性](../../docs/compatibility.md)和[不发布边界](../../docs/no-publish-boundary.md)；机器字段、状态码和路径保持原样。
