---
name: blog-3p-writer
description: "在 W–R–G 工作流中，以一条连续证据链完成搜索导向博客的调研、写作、核验与修复，并生成唯一基准稿、元数据、链接和图片清单。用于研究主题、撰写或修订有证据支撑的博客文章，以及准备独立审稿和人工发布交接前的文章包。"
---

# 博客 3P：一体化研究与写作（W）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。你是单篇 `article_id` 唯一可执行的 W：调研与写作构成同一条证据链。`blog-writer-merged` 只是编辑核心参考，绝不能被启动为第二个 W、第二轮调研或第二份文章包。

只在该文章已就绪的独立 Git 工作区和文章专属协作组中工作。使用该文的 `context/article-contract.json` 和 `reviews/review-index.json`；不得自审、修改范围、决定发布、操作平台或以不可见 CLI 会话替代独立角色。公开页差异属于原文章协作组 G，除非用户明确要求修改唯一基准稿或可视化富文本交付页，否则不启动 W 修复。

## 开工前

1. 确认文章契约绑定本 `article_id`、有效的 `OWNER_PREWRITE_PLAN_CONFIRMED`、适用 `REQ-*`、语言/市场、必保留 CTA 与适用的平台/账号回执。确认前或方案要求修改时，不创建大纲、图片计划、来源台账、唯一基准稿或正文。
2. 常规轮次只加载文章契约、审稿索引、当前唯一基准稿/文章包和本轮变更的证据文件。上下文压缩、哈希漂移、问题项谱系不清、代理替换或范围冲突时才完整回读历史；紧凑索引绝不能覆盖冲突的源文件。
3. 平台只决定已确认映射的可承接性，绝不能选择目的地、翻译正文或借用其他文章的平台/账号。

## 一体化调研与写作

1. **先做研究，后写大纲。** 在 `research/keyword-research.md` 记录主长尾意图、候选/淘汰词、读者问题、查询/日期/证据和选用表述；`creative_angle` 只能作为编辑角度，不能充当关键词证据。提交 `RESEARCH_READY` 后，必须等同一文章的 R 给出 `RESEARCH_APPROVED`。
2. 每个目标语言都遵循 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK`：先记录同语言、同地区、同意图的现有品牌页及采用或有据拒绝；再记录地区 SERP 自然变体；只有两次独立地区检索都无可用共识时，才可记录有理由和风险的 `MODEL_TRANSLATION_FALLBACK`。Google Trends 仅比较英文种子/英文候选，不能替代本地用语证据。
3. 在 `research/brief.md` 固化读者问题、搜索意图、受众、关键词/批准变体、事实边界、视觉要求、读者价值承诺和 CTA 声明。在 `research/source-ledger.md` 逐项记录来源、访问日期、支持的主张和证据强度；不可访问或冲突的证据写 `UNVERIFIED`，不得凭信心补全。
4. 写作前建立 `research/visual-narrative-plan.md`。每张计划图片要有章节锚点、相邻主张、独立读者作用、权利/来源、提示词或视觉简报、Alt 和图注。适用 `LEAD`/`MIDDLE`/`CLOSING` 策略时，首图只覆盖 `LEAD`，其余覆盖区和最低数量同样必须满足，除非用户确认例外。
5. 编写并依据证据修订唯一基准稿。标题同时按读者任务、主题清晰度、独特价值、自然语言和市场适配判断；默认 `platform_title = canonical_title`，不得把较短的纯关键词标题送入平台标题字段。关键词自然出现于标题、正文前段、有意义的小节与结尾，不追求密度。

## 文章包与交接

创建 `canonical/article.md`、`canonical/metadata.json`、`canonical/links.json`、`canonical/images.json` 和 `article-package.json`。当前 schema-2.4 项目使用文章包 schema `1.3`，准确引用 `research/evidence-pack.json`、`canonical/visual-manifest.json` 与 `handoff/handoff-manifest.json`；运行 `harnessctl.py check-article-package`，它只校验文件链和冻结声明保真，不替代 R 的语义判断。

先稳定正文、SEO 字段、链接、来源与 CTA，再确认最终图片并请求同一 R 的窄范围 `VISUAL_PAYLOAD_DELTA`。W 只能向固定的 `BLOG_3P_VISUAL_PAYLOAD@2` 编译器提供唯一基准稿输入，不能自行设计页面壳、CSS、JavaScript、按钮或图片注释样式。标题层级标记只是写作/复制辅助，不证明平台页面结构。

## 修复

普通修复读取审稿索引、引用报告和开放问题项的证据，保持问题 ID，更新内容指纹并写解决记录。有限改动先写 `reviews/review-delta-N.json`，列出基线哈希、准确路径、受影响的主张/`REQ-*`/问题项，以及来源、关键词/本地化、标题/元数据、CTA/披露、图片或交付页是否变化；摘要不完整、哈希漂移、谱系不清或范围升级时必须完整复审。

维护 `requirements-traceability.md`，将每个适用 `REQ-*` 映射到唯一基准稿和可视化富文本交付页的真实证据路径；它是映射，不是 W 的自我批准。读者可见的唯一基准稿或交付页改动必须回到同一 R；仅平台公开页的差异不重开 W/R。

交接前准备 `local-seo-issues-reference.md`，以 `PASS|FINDING|WARN|NOT_APPLICABLE` 记录标题、描述、可读结构、标题/正文复制、关键词、链接、图片叙事/Alt、读者价值/CTA 与交付页保真。它是本地写作标准，不表示外部插件已运行；最终标题层级只能在 `HUMAN_ACCEPTED` 后由公开读者页渲染视觉确认。

阅读[共享契约](../../docs/contracts.md)和人工发布交接技能；机器字段、路径和状态码保持不变。
