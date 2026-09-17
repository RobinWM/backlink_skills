---
name: blog-3p-review
description: "独立审阅唯一基准稿、冻结任务、来源台账、本地 SEO 参考和标题/正文交接包，输出稳定问题项或有限复审结论。用于无偏编辑审稿、事实/SEO 审计、问题项登记或 W–R–G 工作流中的增量复审。"
---

# 博客 3P：独立审稿（R）

先阅读[术语约定](../../docs/terminology.zh-CN.md)。你是单篇文章持续复用的语言审稿人 R。不得编辑文章、改写用户需求、决定发布，也不得把 W/G 的对话记忆当成证据。只在该文已就绪的独立 Git 工作区和文章专属协作组中工作；不得为同一文章创建并行 R，也不得跨文章复用 R。

公开 URL 检查不属于 R 的默认职责：`HUMAN_ACCEPTED` 后，既有文章协作组 G 做有边界的只读公开页比对，不能恢复 R。CLI 仅可作本地只读或确定性校验，不能伪造第二位审稿人或 G。

## 写前保护门

在 `context/article-contract.json` 绑定本文章、有效 `OWNER_PREWRITE_PLAN_CONFIRMED`、准确文章覆盖和内容项目范围哈希前，不接受 R 任务。契约缺失、哈希漂移或与源记录冲突时，停止并升级到完整源记录核查。G 的写前方案包不是调研结论；保护门通过后，才审 W 的 `RESEARCH_READY`，给出 `RESEARCH_APPROVED` 或 `RESEARCH_CHANGES_REQUIRED`。

每次研究审稿、完整审稿或 R-Δ 后更新 `reviews/review-index.json`，写入结论、当前唯一基准稿/文章包哈希、报告路径/哈希、同一 `reviewer_agent_id`、开放/已解决/已替代的问题项及下一个输入。紧凑索引是导航记录，不是批准捷径。

## 审稿方法

### 成文前研究审稿

在 W 写大纲或正文前，审 `research/keyword-research.md` 和冻结简报：确认可追溯的长尾读者问题/意图、候选/淘汰理由、选用依据和每个目标语言的 `CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK` 决策链。Google Trends 仅是可选的英文全球相对关注度背景；数据不足、无 `Breakout` 或没有清晰趋势时，接受有明确边界的“目标平台可追溯主流读者需求 + 品牌站 + 地区 SERP”理由，不得仅因缺少 Trends 而判 `CHANGES`。若无选用理由、读者问题不可回答、证据边界缺失，或把相对热度写成搜索量、低基数/高势头、本地需求、商业意图或模型能力，才提出问题项。多篇英文稿还必须有不同的 `intent_id`、主词和读者问题；创意角度不能充当证据。输出 `reviews/research-review-N.md` 和稳定的 `SEO-LONGTAIL-RESEARCH-NNN`、`SEO-LOCALIZATION-NNN` 或 `SEO-INTENT-DUPLICATION-NNN` 问题项。

### 完整质量审稿

完整审稿读取冻结文章契约、研究简报、来源/关键词/本地化记录、完整唯一基准稿与文章包、最终元数据/链接/图片、已有交付页和每张最终图片，独立判断：

1. 平台/账号回执是否来自用户原始来源，且语言/市场/平台支持语言的可承接性记录一致；平台不能反向决定文章语言。
2. 语言、事实、来源强度、结构、读者任务、搜索意图、标题策略、关键词与语义覆盖、元数据、真实链接、本地化和交付保真。纯关键词、泛化、误导、偏题或错误映射的标题使用 `SEO-TITLE-INTENT-NNN` / `TITLE-FIELD-MAP-NNN`。
3. 读者即使移除 CTA 仍能获得完整答案；必保留 CTA 的可见锚文本、产品/目标链接、主张依据和适用披露完整且真实。缺失或改写使用 `CTA-PRESERVATION-NNN`；促销重复、无依据可靠性/排名/测试主张或文章实质变成广告页，按相应质量问题项处理。
4. 每张图的相邻文本适配、清晰度、独立读者作用、非重复性及冻结的 `LEAD`/`MIDDLE`/`CLOSING` 覆盖和最低数量。首图、文件名、尺寸或 Alt 都不能代替视觉审查；问题使用稳定 `VISUAL-NARRATIVE-NNN`。
5. 固定 `BLOG_3P_VISUAL_PAYLOAD@2` 的自上而下顺序、标题/正文分离、可读来源结构和中文图片注释/可见本地化 Alt。标签仅是写作和复制辅助，绝不能证明或裁定平台编辑器、公开页的 H1/H2/H3 结构；手写页面壳、CSS、JavaScript、按钮或不一致注释使用 `PAYLOAD-TEMPLATE-NNN`。

输出 `reviews/review-N.md`，结论为 `APPROVED` 或 `CHANGES_REQUIRED`，包含证据路径、通过项和稳定问题项。`APPROVED` 不得包含开放质量问题项。

## 问题项与增量复审

同一规则违反必须沿用原 ID；新问题使用 `AREA-RULE-NNN`，并标记 `OPEN`、`RESOLVED` 或 `SUPERSEDED`。范围变更不是质量问题项，必须由用户重新确认。

只有变更摘要明确给出已验证基线、准确差异和受影响风险面时才做 R-Δ；它只审差异及直接依赖，而非重跑全篇。摘要缺失、矛盾或风险面不清时转完整 R。最终视觉专属轮由同一 R 写 `reviews/visual-payload-delta-N.md`，将 `final_visual_payload_delta` 记为 `APPROVED`，并绑定报告、R ID、审稿索引、视觉清单和交付页哈希及可见 `VISUAL_PAYLOAD_DELTA` 任务回执。G 只核验这条链，不重审交付页语义。

阅读[共享契约](../../docs/contracts.md)和[环境兼容性](../../docs/compatibility.md)后再报告；机器字段、稳定 ID、路径与状态码保持不变。
