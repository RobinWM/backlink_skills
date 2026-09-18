---
name: blog-3p-human-handoff
description: "提供统一可视化富文本载荷的编译/校验器，以及已验收文章的人工发布交接包和公开页回传证据。W 在 FULL_REVIEW 前编译载荷；G 通过后只生成派生交接清单。全程不操作平台编辑器。"
---

# 博客 3P：人工发布交接包

先阅读[术语约定](../../docs/terminology.zh-CN.md)。W 在 `FULL_REVIEW` 前使用本技能的编译器生成浏览器可打开、人工可直接选择标题和正文的**可视化富文本交付页**；G 将文章置为 `human_release_ready` 后，本技能只使用该已审载荷生成／核对派生交接清单与回传证据。它不登录平台、不输入编辑器、不上传图片、不保存草稿、不发布、不删除或回滚。

## 唯一交接面

`article-package.json@1.5` 是冻结声明与上游唯一来源的连接点：`canonical/article.html`、metadata、evidence pack 和视觉清单。它不反向引用派生的 handoff manifest，也不手工重复 SEO 字段、链接或图片清单。编译器只能读取 package 声明且哈希相符的四项来源，不能用另一份正文、标题、metadata 或视觉清单替换输入。唯一接受的交付页是一对由该编译器生成的 `BLOG_3P_VISUAL_PAYLOAD@3`：`handoff/visual-payload.html` 供富文本复制和 R 主审，`handoff/visual-payload.md` 是完全对应的可读／追溯备用稿。不得手写、二次编辑任一交付页、页面壳、CSS、JavaScript、按钮、卡片或操作顺序；`1.4` 仅作历史读取/校验兼容。

交付页固定自上而下显示：博客标题、在准确位置带中文图片注释的正文、SEO 标题、标签、描述。没有复制按钮、剪贴板脚本或平台专属控件。`SEPARATE_TITLE_FIELD` 表示人工分开复制标题和正文；`TITLE_IN_BODY` 用于没有独立标题字段的平台。旧 `BODY_H1_REQUIRED` 仅作为兼容输入别名，归一化为 `TITLE_IN_BODY`。本地 `<h1>`/`<h2>`/`<h3>` 标记只是写作和富文本选择辅助，绝不证明目标平台最终标题层级。

每张图在唯一基准稿 HTML 正文的精确位置使用一个独立注释标记：`<!-- BLOG_3P_IMAGE:01 -->`、`<!-- BLOG_3P_IMAGE:02 -->`……；不得使用聚合的 `{{IMAGE_CARDS}}` 槽位。编译器只在该标记原处渲染编号中文注释，HTML 与 Markdown 的图卡必须一一对应。视觉清单按顺序声明 `ordinal`、`coverage_zone`、`placement_anchor`、本地化 Alt／图注等；`placement_anchor` 必须在相应标记之前可见。素材必须真实存在、哈希匹配，并以 `01-lead-<slug>.png`、`02-middle-<slug>.jpg`、`03-closing-<slug>.png` 这类稳定文件名交付；只接受 PNG、JPG 或 JPEG，不能用 WebP、GIF、SVG 或未编号的替代品。Alt 或其他图卡字段为空、标记缺失／重复／乱序、文件格式／命名／哈希不符时编译失败，不能以占位文本替代。唯一基准稿只能含文章内容和结构标记；脚本、样式、布局标签、自定义控件和 `<img>` 会被拒绝，因为固定模板拥有布局与图片注释。保留真实链接和可读结构。适用 `LEAD`/`MIDDLE`/`CLOSING` 时，`validate_payload.py` 会从 package 声明的来源重新渲染并核对 HTML/Markdown 的正文、卡片字段、素材文件、放置锚点和 CTA，从而拦截编译后的手工替换。只有它明确输出 `COMPANION_DUAL_READ_REQUIRED`，R 才需要额外语义审读 Markdown。

交接目录应包含 `RELEASE-CARD.md`、内容指纹、本地预检、两份交付页和 `handoff/handoff-manifest.json`。后者单向索引唯一基准稿、metadata、证据包、视觉清单、HTML／Markdown 交付页、审稿索引和需求追溯哈希；发布卡仅是人工提示，不是第二份文章、SEO 文档或证据源。

## 平台传输预检与已观察限制

在生成 `RELEASE-CARD.md` 前，先读取 [平台发布观察](references/platform-release-observations.md) 中与该平台/账号相同的行；它是提问清单，不是平台选择、账号授权或发布成功的证据。每条观察都必须保留平台、账号/站点、文章、日期和观察面。不得把一个账号的编辑器或读者页现象推广到该平台其他账号，也不得从公开可见性反推编辑器传输能力。

若人工需要插入正文图片，交接正文默认使用编译器在真实 `<!-- BLOG_3P_IMAGE:NN -->` 标记处生成的可删除图卡；图卡必须紧邻稳定的正文锚点。不得仅交付 `LEAD`／`MIDDLE`／`CLOSING` 的独立图片列表并让发布者自行猜测位置。原生独立标题字段只接收冻结标题的纯文本，不带 Markdown `#`；仅 `TITLE_IN_BODY` 路线才将标题放入正文。把已验证的正文图、仅封面图和未知图片传输分别记录，不能以富文本粘贴成功代替读者页图片验证。

## 编译与 R 的一次最终审稿

只有正文、metadata、链接、来源、读者价值承诺、冻结 CTA 和最终 visual manifest 都稳定后才编译。随后该文章既有 R 的 `FULL_REVIEW` 一次审本篇 evidence pack、实际引用的共享记录、唯一基准稿、metadata、最终图片、视觉清单和 HTML 主交付页，检查图文邻接适配、每张图是否就在对应正文标记处、可读性、独立读者作用、覆盖区、Alt/图注、素材格式／命名、CTA 保真和固定模板一致性。Markdown 的同源性由验证器处理；只有 `COMPANION_DUAL_READ_REQUIRED` 才把它加入 R 的语义双读。review index 仍绑定两份最终文件哈希；默认标准路线同时绑定 evidence-pack 哈希，而不是额外创建研究审。

若完整审稿后视觉资产、visual manifest、payload 或 package 的视觉指针改变，同一 R 才做窄范围 `R_VISUAL_DELTA`。正文、metadata、链接、来源、CTA 或读者价值改变不是视觉复审，必须回到同一 W → R 修复；R 应先读取变更摘要、变更文件和直接依赖，只有风险面不清、哈希漂移、问题项谱系不清或范围升级才完整重审。R 批准后，交接清单生成只能复用逐字节一致的既有交付页；若重新渲染会改变它，编译器必须在覆盖前失败，W 先生成候选再获得相应 R 回执。G 只核验交接清单哈希、适用 `REQ-*` 映射、必需的 `FULL_REVIEW` 与适用 R-Δ 回执链；只有 `ELEVATED_EARLY_CHALLENGE` 路线才另核验同一 R 的 `RESEARCH_REVIEW`。标准路线的 `NOT_REQUIRED / INTEGRATED_IN_FULL_REVIEW` 正是正确状态。G 不替 R 判断图片或编辑质量。机器校验只证明包装结构，不能证明平台标题层级。

## 人工发布后的轻量回传

人工在平台完成操作后，将 `templates/public-return-receipt.json` 复制为 `handoff/public-return-receipt.json`，记录公开 URL、精确 `HUMAN_ACCEPTED` 或 `HUMAN_NEEDS_FIX`、回传时间、已知版本/时间或 `UNVERIFIED`、渲染证据路径和已知限制。限制必须明确平台、账号/站点、编辑器/主题、地区/市场、观察日期、证据、受影响契约项，并设 `not_generalizable: true`。

同一已登记的项目统筹 G 在 `PUBLIC_QA_BATCH_READONLY` 中使用这些回执和规范化快照写一份批量报告。每篇有独立的条目、回执/快照哈希、渲染视觉证据、尝试次数与 `unverified_retry_count`，并独立分类为 `PUBLIC_QA_PASSED`、`PUBLIC_QA_PASSED_WITH_LIMITATION`、`HUMAN_TRANSPORT_FIX_REQUIRED`、`PUBLIC_QA_UNVERIFIED` 或 `CANONICAL_CHANGE_REQUESTED`。平台传输修复返回给人工的一份合并清单，再回到同一 G 的下一次批量复核；只有带用户请求 ID 的 `CANONICAL_CHANGE_REQUESTED` 能回到该文 W → R。

`HUMAN_ACCEPTED` 后，标题层级仅凭公开读者页的渲染视觉判断。提供足以辨别页面标题、章节、子章节、顺序和扁平化/重复问题的视觉证据；编辑器 HTML/DOM、公开源码、Feed 与 JSON 快照均不能覆盖该结论。证据不足是 `PUBLIC_QA_UNVERIFIED`，可见层级问题使用稳定 `PUBLIC-VISUAL-HIERARCHY-NNN` 并交由人工修复决定。

机器字段、HTML 模板签名、`Alt：` 标记、路径与状态码保持不变。
