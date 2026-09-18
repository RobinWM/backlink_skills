---
name: blog-3p-writer
description: "在 W–R–G 工作流中，以一条连续证据链完成搜索导向博客的调研、写作、核验与修复，并生成唯一基准稿、元数据、链接和图片清单。用于研究主题、撰写或修订有证据支撑的博客文章，以及准备独立审稿和人工发布交接前的文章包。"
---

# 博客 3P：一体化研究与写作（W）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。你是单篇 `article_id` 唯一可执行的 W：调研与写作构成同一条证据链。`blog-writer-merged` 只是编辑核心参考，绝不能被启动为第二个 W、第二轮调研或第二份文章包。

只在该文章已就绪的独立 Git 工作区和文章专属 W/R 协作组中工作。使用该文的 `context/article-contract.json` 和 `reviews/review-index.json`；不得自审、修改范围、决定发布、操作平台或以不可见 CLI 会话替代独立角色。公开页差异属于项目统筹 G 的批量只读检查，除非用户明确要求修改唯一基准稿或可视化富文本交付页，否则不启动 W 修复。

## 开工前

1. 确认文章契约绑定本 `article_id`、有效的 `OWNER_PREWRITE_PLAN_CONFIRMED`、适用 `REQ-*`、冻结 `topic_slot`、语言/市场、必保留 CTA 与适用的平台/账号回执。确认前或方案要求修改时，不创建大纲、图片计划、来源台账、唯一基准稿或正文。
2. 常规轮次只加载文章契约、审稿索引、当前唯一基准稿/文章包和本轮变更的证据文件。上下文压缩后先完整重读[工作流核心](../../docs/workflow-core.md)；哈希漂移、问题项谱系不清、代理替换或范围冲突时才完整回读历史。紧凑索引绝不能覆盖冲突的源文件。
3. 平台只决定已确认映射的可承接性，绝不能选择目的地、翻译正文或借用其他文章的平台/账号。

## 一体化调研与写作

### 默认：连续创作路线

冻结的 `review_effort` 为 `STANDARD_INTEGRATED_REVIEW / INTEGRATED_IN_FULL_REVIEW` 时，按一条连续工作完成 `RESEARCH → DRAFT → VISUALS → PAYLOAD`。先在 `research/evidence-pack.json` 建立足以支撑文章主张的本篇研究差异与引用索引，再以它完成大纲、正文、最终图片和交付页；不要为了流程形式等待 `RESEARCH_APPROVED`、创建独立 `RESEARCH_REVIEW` 或重复维护四份研究文件。最终 R 的 `FULL_REVIEW` 会独立覆盖本篇证据与实际引用的共享记录。

1. evidence pack 必须记录主长尾读者问题/意图、候选/淘汰词、选用理由、查询/日期、来源记录、支持的主张、证据强度和不确定性。若项目内的 `evidence/shared/campaign-evidence-pack.json` 有精确匹配且可复用的记录，写可选 `campaign_shared_evidence` 的 `path`、`sha256`、`record_ids`，并在 `article_delta` 写 `decision`、`freshness_or_scope_check` 与 `additional_evidence_refs`；只引用实际采用的记录，不复制整包或重写同一观察。两字段都缺表示无命中，正常继续本篇调研，绝不造空缓存。只将会显著改变读者决定或易变的主张（价格/日期、比较、性能、平台政策、高后果内容）标成可核验 material claim；不要把普通背景句机械拆成台账。`creative_angle` 只能作为编辑角度，不能充当关键词证据。若 Google Trends 数据不足、无结果或无明确趋势，不得反复试探或编造趋势理由：读者问题与选词仍须来自当前品牌站用语、地区 SERP 或已记录的模型翻译兜底；平台画像只可帮助选择技术深度、示例形式和交付结构，绝不能成为关键词、自然变体、搜索意图、当地需求或热门度的证据。
2. 每个目标语言都遵循 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`：先记录同语言、同地区、同意图的现有品牌页及采用或有据拒绝；再记录地区 SERP 自然变体；只有两次独立地区检索都无可用共识时，才可记录有理由和风险的 `MODEL_TRANSLATION_FALLBACK`。Google Trends 如可用，仅比较英文种子/英文候选，作为全球相对关注度背景；不能替代本地用语证据，也不能证明搜索量、低基数/高势头、本地需求、商业意图或模型能力。缺少 `Breakout` 或清晰趋势本身不阻塞研究或写作。
3. 精确关键词、自然变体和标题只能在冻结 `topic_slot` 内调整。若读者任务、核心意图、市场和承诺都未变，在 `topic_slot_alignment` 写 `ALIGNED` 与简短 `within_slot_adjustments` 即可，不重开 G 或 R。若证据表明本地意图不符、原选题无可靠依据，或必须换成另一个读者问题，写 `TOPIC_EVIDENCE_CONFLICT`、稳定冲突 ID、理由、证据引用和建议动作，停止换题并交同一 G 决定。G 的 `KEEP_SLOT` / `NARROW_WITHIN_SLOT` 决定须在 `resolved_conflicts` 和既有可见任务账本中对应记录后才可继续；`PAUSE` / `OWNER_RECONFIRM_REQUIRED` 不得由 W 绕过。W 绝不能直接修改 `topic_slot`。
4. 在同一 evidence pack 明确分开 `reader_intent_basis`、`platform_profile_use` 与 `evidence_posture`，并记录读者问题、受众、批准变体、事实边界、视觉要求、读者价值承诺、CTA 声明和图片计划。共享包只允许精确引用 `GLOBAL_ENGLISH_TRENDS`、`BRAND_SITE_VARIANT` 或 `REGIONAL_SERP_VARIANT`；易变主张、平台政策/账号状态和 `MODEL_TRANSLATION_FALLBACK` 仍须本篇独立取证。平台画像如被采用，必须标为 `TOPIC_FRAMING` 或 `FORMAT_ADAPTATION`，且不得写入选词或需求证据。`METHOD_TEMPLATE_NO_EXECUTION` 只能交付读者可自行使用的比较设计、记录模板或试行方法，标题、正文和 CTA 不得暗示已验证、A/B 结果、稳定性或因果结论；`DOCUMENTED_EMPIRICAL_RECORD` 则须在完整 R 前具备协议、输入/设置、运行日志、评价标准和局限路径。每张计划图片要有章节锚点、相邻主张、独立读者作用、权利/来源、提示词或视觉简报、Alt 和图注。适用 `LEAD`/`MIDDLE`/`CLOSING` 策略时，首图只覆盖 `LEAD`，其余覆盖区和最低数量同样必须满足，除非用户确认例外。`keyword-research.md`、`brief.md`、`source-ledger.md`、`visual-narrative-plan.md` 和跨语言说明如有需要只能作为从 evidence pack 派生的查阅视图，不得手工双写或成为额外审批门。
5. 编写并依据证据修订唯一基准稿。标题同时按读者任务、主题清晰度、独特价值、自然语言和市场适配判断；默认 `platform_title = canonical_title`，不得把较短的纯关键词标题送入平台标题字段。关键词自然出现于标题、正文前段、有意义的小节与结尾，不追求密度。

### 仅增强档：成文前研究挑战

当冻结的 `review_effort` 为 `ELEVATED_EARLY_CHALLENGE / SEPARATE_RESEARCH_REVIEW_REQUIRED`，W 在写大纲或正文前提交 evidence pack 的研究部分给同一 R。只有此路线需要 `RESEARCH_READY` 与 `RESEARCH_APPROVED`；R 批准后继续完成成稿、图片、交付页，并仍接受完整 `FULL_REVIEW`。W 不得自行把增强路线降为标准路线。若 R 或 G 记录升级，保留其风险理由并按增强路线执行。

## 文章包与交接

创建 `canonical/article.html`、`canonical/metadata.json`、`research/evidence-pack.json`、`canonical/visual-manifest.json` 和 `article-package.json`。当前 schema-2.12 项目使用 evidence pack schema `1.3` 与文章包 schema `1.5`：metadata 是标题/SEO 元数据的唯一来源，evidence pack 是本篇研究差异、topic-slot 对齐和（仅在实际复用时）共享记录引用的唯一来源，visual manifest 是图片的唯一最终来源；文章包只声明这些上游文件及其哈希，绝不反向指向 handoff，也不另写链接或图片清单。`2.11 / 1.4` 仅作历史读取/校验兼容。当前项目只进入人工原生发布交接，不提供本地-only 或自动发布分支。

先完成正文、metadata、链接、来源、CTA 和最终图片，再让同一编译器仅从 package 声明且哈希相符的来源生成固定的 `BLOG_3P_VISUAL_PAYLOAD@3` HTML／Markdown 双交付页；不得手写、二次编辑或用另一份正文/metadata 生成其中任何一页。唯一基准稿 HTML 必须把每张图放在准确的独立位置标记中（`<!-- BLOG_3P_IMAGE:01 -->` 起按顺序），素材采用实际存在且哈希匹配的 `01-lead-<slug>.png`、`02-middle-<slug>.jpg`、`03-closing-<slug>.png` 命名；不使用 `{{IMAGE_CARDS}}`、WebP/GIF/SVG 或任意未编号文件。**编译完成后、交给 R 前**运行 `harnessctl.py check-review-ready --workspace <article-workspace> --article-contract context/article-contract.json --review-index reviews/review-index.json --article-package article-package.json`；它只校验当前文件、哈希、固定图卡、精确 CTA 与交付页伴随投影是否可审，失败直接修机械问题，不替代 R 的语义判断，也不产生通过结论。未输出 `COMPANION_DUAL_READ_REQUIRED` 时，同一 R 语义审最终稿、图片、上游源和 HTML 主交付页；只有该回退才再审 Markdown。未发生后续变更时不得额外创建视觉审稿。完整审稿后的有限修复先提交同一 R 的 `R_DELTA`：它必须绑定原完整审稿报告、当前全部交付哈希、准确变更路径和受影响问题项；纯视觉资产/载荷改动才使用更窄的 `R_VISUAL_DELTA`。范围、读者价值承诺、哈希漂移、问题项谱系不清或超出已声明风险面的改动必须回到完整 R。W 不能自行设计页面壳、CSS、JavaScript、按钮或图片注释样式。标题层级标记只是写作/复制辅助，不证明平台页面结构。

## 修复

普通修复读取审稿索引、引用报告和开放问题项的证据，保持问题 ID，更新内容指纹并写解决记录。有限改动先写 `reviews/review-delta-N.json`，列出基线哈希、准确路径、受影响的主张/`REQ-*`/问题项，以及来源、关键词/本地化、标题/元数据、CTA/披露、图片或交付页是否变化；摘要不完整、哈希漂移、谱系不清或范围升级时必须完整复审。

维护 `requirements-traceability.md`，将每个适用 `REQ-*` 映射到唯一基准稿和可视化富文本交付页的真实证据路径；它是映射，不是 W 的自我批准。读者可见的唯一基准稿或交付页改动必须回到同一 R；仅平台公开页的差异不重开 W/R。

以共享的本地 SEO ISSUES 参考审自查；只在 R 报告、审稿索引或 handoff 中记录实际 `FINDING` / `WARN`，不为全绿文章再生成逐项 `PASS` 副本。它是本地写作标准，不表示外部插件已运行；最终标题层级只能在 `HUMAN_ACCEPTED` 后由公开读者页渲染视觉确认。

日常先读[流程核心](../../docs/workflow-core.md)、文章契约、审稿索引与本轮所涉证据；仅当范围、交接或传递风险实际相关时，按需读取[共享契约](../../docs/contracts.md)或人工发布交接技能的对应段落。机器字段、路径和状态码保持不变。
