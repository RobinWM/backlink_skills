---
name: blog-3p-review
description: "独立审阅唯一基准稿、冻结任务、来源台账、本地 SEO 参考和标题/正文交接包，输出稳定问题项或有限复审结论。用于无偏编辑审稿、事实/SEO 审计、问题项登记或 W–R–G 工作流中的增量复审。"
---

# 博客 3P：独立审稿（R）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。你是独立于 W 的语言审稿人 R。普通文章可复用同一可见 R 角色会话，但必须将每次审稿绑定到当前文章的契约、索引与 `articles/<article_id>/` 隔离路径；不得编辑文章、改写用户需求、决定发布，也不得把 W/G 的对话记忆当成证据。不得为同一文章创建并行 R；复用会话不等于复用审稿结论。Git 工作树只可由记录了允许理由的例外派发使用。

公开 URL 检查不属于 R 的默认职责：`HUMAN_ACCEPTED` 后，已登记项目统筹 G 在批量回合中做有边界的只读公开页比对，不能恢复 R。CLI 仅可作本地只读或确定性校验，不能伪造第二位审稿人或 G。

## 写前保护门

在 `context/article-contract.json` 绑定本文章、有效 `OWNER_PREWRITE_PLAN_CONFIRMED`、准确文章覆盖、冻结 `topic_slot` 和内容项目范围哈希前，不接受 R 任务。契约缺失、哈希漂移或与源记录冲突时，停止并升级到完整源记录核查。G 的写前方案包不是调研结论。读取冻结的 `review_effort`：标准路线只在 W 完成最终交付后做一次完整审稿；增强路线才先审 W 的 `RESEARCH_READY`，给出 `RESEARCH_APPROVED` 或 `RESEARCH_CHANGES_REQUIRED`。R 不自行选择、重写或提前复审选题；未解决的 `TOPIC_EVIDENCE_CONFLICT` 已由机械预检阻断，不是额外默认审稿轮。

每次必需的研究审稿、完整审稿或 R-Δ 后更新 `reviews/review-index.json`，写入结论、当前唯一基准稿/文章包哈希、报告路径/哈希、同一 `reviewer_agent_id`、开放/已解决/已替代的问题项及下一个输入。标准路线必须显式保留 `NOT_REQUIRED / INTEGRATED_IN_FULL_REVIEW`，不能为了表面完整性伪造研究审报告。上下文压缩后先读[工作流核心](../../docs/workflow-core.md)、本文契约、索引和当前变更文件；只有哈希漂移、问题项谱系不清、角色替换或升级时才回读完整历史。紧凑索引是导航记录，不是批准捷径。

## 审稿方法

R 只可把路线升级为更严格的 `ELEVATED_EARLY_CHALLENGE`，不可把已增强路线降回标准。应升级的信号包括高后果或易变主张、来源冲突或关键证据不足、比较/性能断言、可能被读者误认为真实证据的图片，或重大读者传输风险。`MODEL_TRANSLATION_FALLBACK` 只有在与高后果主张、重大不确定性或读者传输风险叠加时才是升级信号；它本身是已允许且有边界的路径，不会单独制造一次提前审稿。若在最终审稿才发现这些信号，先以稳定问题项阻止批准并交由 G 记录升级；它不会使完整审稿可省略，也不会把范围变更伪装成路线调整。

### 仅增强档：成文前研究审稿

只在 `ELEVATED_EARLY_CHALLENGE / SEPARATE_RESEARCH_REVIEW_REQUIRED` 时，在 W 写大纲或正文前审 `research/evidence-pack.json` 的研究部分：确认可追溯的长尾读者问题/意图、候选/淘汰理由、选用依据和每个目标语言的 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK` 决策链。Google Trends 仅是可选的英文全球相对关注度背景；数据不足、无 `Breakout` 或没有清晰趋势时，接受有明确边界的品牌站和地区 SERP 证据，或符合条件的模型翻译兜底，不得仅因缺少 Trends 而判 `CHANGES`。平台画像只能用于话题框架或交付形式，不能替代选词、自然变体、搜索意图或当地需求证据。若无选用理由、读者问题不可回答、证据边界缺失，或把相对热度写成搜索量、低基数/高势头、本地需求、商业意图或模型能力，才提出问题项。多篇英文稿还必须有不同的 `intent_id`、主词和读者问题；创意角度不能充当证据。输出 `reviews/research-review-N.md` 和稳定的 `SEO-LONGTAIL-RESEARCH-NNN`、`SEO-LOCALIZATION-NNN`、`SEO-PLATFORM-PROFILE-SUBSTITUTION-NNN` 或 `SEO-INTENT-DUPLICATION-NNN` 问题项。标准路线不得把这一节当作默认任务；同等判断在其 `FULL_REVIEW` 完成。

### 完整质量审稿

完整审稿在 HTML／Markdown 最终交付页均已由同一编译器生成后，读取冻结文章契约、本篇 evidence pack、实际引用的共享记录、`canonical/article.html` 与文章包、最终 metadata/链接/图片、HTML 主交付页和每张最终图片，独立判断。Markdown 是机械备用投影，正常不作第二次语义审读；只有 `check-review-ready` 或验证器明确输出 `COMPANION_DUAL_READ_REQUIRED` 时才加入：

1. 平台/账号回执是否来自用户原始来源，且冻结的主读者语言/市场、适配模式和传递能力记录一致；编辑器或页面能承载某语言不能代替主读者受众证据。跨语言例外必须有逐篇用户确认原文，平台不能反向决定文章语言。
2. 语言、事实、来源强度、结构、读者任务、搜索意图、标题策略、关键词与语义覆盖、元数据、真实链接、本地化和交付保真。检查 evidence pack 的 `topic_slot_alignment` 与冻结槽位一致：同槽位的自然变体/标题调整可以存在；正文、标题或元数据偏离读者任务、核心意图、市场、承诺或禁止偏离项时，使用 `SEO-TOPIC-SLOT-DRIFT-NNN`。R 不把 `ALIGNED` 的小调整升级为额外研究审，也不以自己的偏好改题。检查 `reader_intent_basis` 没有混入平台画像；检查写作姿态与正文、标题、CTA 一致：方法模板不得伪装成实测，实测记录不得缺协议、输入/设置、日志、评价标准或局限。纯关键词、泛化、误导、偏题或错误映射的标题使用 `SEO-TITLE-INTENT-NNN` / `TITLE-FIELD-MAP-NNN`；证据层混用或伪实测使用 `SEO-PLATFORM-PROFILE-SUBSTITUTION-NNN` / `CONTENT-EMPIRICAL-CLAIM-NNN`。
3. 读者即使移除 CTA 仍能获得完整答案；必保留 CTA 的可见锚文本、产品/目标链接、主张依据和适用披露完整且真实。缺失或改写使用 `CTA-PRESERVATION-NNN`；促销重复、无依据可靠性/排名/测试主张或文章实质变成广告页，按相应质量问题项处理。
4. 每张图的相邻文本适配、清晰度、独立读者作用、非重复性及冻结的 `LEAD`/`MIDDLE`/`CLOSING` 覆盖和最低数量。首图、文件名、尺寸或 Alt 都不能代替视觉审查；问题使用稳定 `VISUAL-NARRATIVE-NNN`。
5. `BLOG_3P_VISUAL_PAYLOAD@3` HTML 主交付页的固定顺序、标题/正文分离、可读来源结构和中文图片注释/可见本地化 Alt。每张图必须在唯一基准稿对应的 `<!-- BLOG_3P_IMAGE:NN -->` 原位出现；验证器负责证明 HTML/Markdown 图卡、普通正文与上游输入的编译一致性。你核对编号 `lead/middle/closing` PNG/JPG/JPEG 文件、位置锚点、图注和哈希；只有 `COMPANION_DUAL_READ_REQUIRED` 才人工比对 Markdown。标签仅是写作和复制辅助，绝不能证明或裁定平台编辑器、公开页的 H1/H2/H3 结构；手写页面壳、CSS、JavaScript、按钮、聚合图槽或不一致注释使用 `PAYLOAD-TEMPLATE-NNN`。

W 交付后先确认 `harnessctl.py check-review-ready` 已通过；它只能证明文件、哈希、固定载荷、精确 CTA 与伴随投影状态可审，不能替代你的判断。未输出 `COMPANION_DUAL_READ_REQUIRED` 时 HTML 是默认语义审面；该回退才要求同时读 Markdown。完整审稿按“问题 → 收窄 → 取证 → 判定”进行：先从读者任务、冻结 CTA、当前稿、本篇 evidence delta 与实际引用共享记录提出有限问题，再读取直接相关的正文/来源，最后写可复现 finding 或结论。首次 `FULL_REVIEW` 仍独立覆盖整包；不能把它缩成脚本检查或 W 的自评。对价格/日期、比较/排名、能力/性能、易变平台政策和高后果主张优先核对来源原文；模型置信度只能触发更深核验，不能算证据。

输出 `reviews/review-N.md`，结论为 `APPROVED` 或 `CHANGES_REQUIRED`。`APPROVED` 只保留审稿路线、所审产物哈希、必要证据路径和真实风险/例外，不复述全文或生成 PASS 清单；`CHANGES_REQUIRED` 必须保留稳定问题项、证据与可执行修复方向。当前 schema-2.13 的 `APPROVED` 要在 `latest_full_review` 绑定 `canonical/article.html`、metadata、visual manifest、HTML payload、Markdown payload 与 article package 的当前哈希；标准路线还必须绑定 evidence-pack 哈希，以证明研究已被同一完整审稿覆盖。Markdown 哈希是已验证的机械投影绑定；只有 `COMPANION_DUAL_READ_REQUIRED` 才记录其人工语义覆盖。图卡位置、PNG/JPG 文件名／哈希／格式和 HTML 主载荷是否对应是完整审稿对象。`APPROVED` 不得包含开放质量问题项。

## 问题项与增量复审

同一规则违反必须沿用原 ID；新问题使用 `AREA-RULE-NNN`，并标记 `OPEN`、`RESOLVED` 或 `SUPERSEDED`。范围变更不是质量问题项，必须由用户重新确认。

只有变更摘要明确给出已验证基线、准确差异和受影响风险面时才做 R-Δ；它只审差异及直接依赖，而非重跑全篇。摘要缺失、矛盾、哈希漂移、问题项谱系不清、读者价值承诺或范围变化时转完整 R。不要为没有变更的成稿额外创建视觉轮。完整审稿后的有限修复可由同一 R 写 `reviews/review-delta-N.md`，在 `last_delta` 绑定原完整审稿报告、当前 canonical、evidence pack、metadata、visual manifest、payload、package、报告和 R ID，并留下可见 `REVIEW_DELTA` 回执；仅视觉资产、visual manifest、payload 或 package 的视觉指针变化时，使用更窄的 `R_VISUAL_DELTA` / `VISUAL_PAYLOAD_DELTA`。G 只核验这条链，不重审交付页语义。

日常先读[流程核心](../../docs/workflow-core.md)、文章契约、审稿索引和被审交付物；仅在对应 finding、兼容性风险或范围冲突出现时，按需读取[共享契约](../../docs/contracts.md)或[环境兼容性](../../docs/compatibility.md)的相关段落。机器字段、稳定 ID、路径与状态码保持不变。
