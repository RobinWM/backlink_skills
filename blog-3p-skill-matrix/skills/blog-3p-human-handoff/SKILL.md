---
name: blog-3p-human-handoff
description: "将已验收的博客文章编译为统一、可视化、可直接复制的富文本人工发布交接包，并生成本地交付校验与公开页回传证据。用于 G 已授权人工发布、需要准备交接包或核对人工回传时；不操作平台编辑器。"
---

# 博客 3P：人工发布交接包

先阅读[术语约定](../../docs/terminology.zh-CN.md)。本技能只在 G 将文章置为 `human_release_ready` 后使用。它生成浏览器可打开、人工可直接选择标题和正文的**可视化富文本交付页**，不登录平台、不输入编辑器、不上传图片、不保存草稿、不发布、不删除或回滚。

## 唯一交接面

`article-package.json` 是唯一基准稿、研究证据、视觉清单和交接文件索引的连接点。不要在发布卡、本地预检或图片注释中手工重述这些记录。唯一接受的交付页是编译器生成的 `BLOG_3P_VISUAL_PAYLOAD@2`：W 提供标题、唯一基准稿正文/结构、视觉清单和 SEO 元数据；不得手写 `visual-payload.html`、页面壳、CSS、JavaScript、按钮、卡片或操作顺序。

交付页固定自上而下显示：博客标题、在准确位置带中文图片注释的正文、SEO 标题、标签、描述。没有复制按钮、剪贴板脚本或平台专属控件。`SEPARATE_TITLE_FIELD` 表示人工分开复制标题和正文；`TITLE_IN_BODY` 用于没有独立标题字段的平台。旧 `BODY_H1_REQUIRED` 仅作为兼容输入别名，归一化为 `TITLE_IN_BODY`。本地 `<h1>`/`<h2>`/`<h3>` 标记只是写作和富文本选择辅助，绝不证明目标平台最终标题层级。

图片位置必须渲染为编号中文注释，包含文件、覆盖区、完整本地化 Alt 与图注。Alt 为空时编译失败，不能以占位文本替代。唯一基准稿只能含文章内容和结构标记；脚本、样式、布局标签、自定义控件和 `<img>` 会被拒绝，因为固定模板拥有布局与图片注释。保留真实链接和可读结构。适用 `LEAD`/`MIDDLE`/`CLOSING` 时，使用 `validate_payload.py` 校验固定模板签名、固定顺序、可见 Alt、冻结 CTA 的锚文本/href/披露以及覆盖区数量。

交接目录应包含 `RELEASE-CARD.md`、视觉/链接清单、内容指纹、本地预检和 `handoff/handoff-manifest.json`。后者只索引唯一基准稿、证据包、视觉清单、交付页、发布卡、本地预检和 R-Δ 的路径/哈希，不是第二份文章或 SEO 文档。

## 编译与 R 的最终视觉复审

只有正文、SEO 字段、链接、来源、读者价值承诺和冻结 CTA 稳定后才编译。随后该文章既有 R 仅做一次窄范围 `VISUAL_PAYLOAD_DELTA`：审视觉清单、最终图片/视觉审查、编译交付页及其传递的字段，检查图文邻接适配、可读性、独立读者作用、覆盖区、Alt/图注、CTA 保真和固定模板一致性。

若正文、元数据、链接、来源、CTA 或读者价值改变，这不是视觉复审，必须回到同一 W → R 正常修复。R 批准后，G 只核验交接清单哈希、适用 `REQ-*` 映射和同一 R 的 `RESEARCH_REVIEW`、`FULL_REVIEW`、`VISUAL_PAYLOAD_DELTA` 回执链；G 不替 R 判断图片或编辑质量。机器校验只证明包装结构，不能证明平台标题层级。

## 人工发布后的轻量回传

人工在平台完成操作后，将 `templates/public-return-receipt.json` 复制为 `handoff/public-return-receipt.json`，记录公开 URL、精确 `HUMAN_ACCEPTED` 或 `HUMAN_NEEDS_FIX`、回传时间、已知版本/时间或 `UNVERIFIED`、渲染证据路径和已知限制。限制必须明确平台、账号/站点、编辑器/主题、地区/市场、观察日期、证据、受影响契约项，并设 `not_generalizable: true`。

只有该文章既有的 G 使用回执和规范化快照写 `gate/public-qa-report-N.md`。它记录回执时间、文件路径、既有 G ID、尝试次数与 `unverified_retry_count`，并分类为 `PUBLIC_QA_PASSED`、`PUBLIC_QA_PASSED_WITH_LIMITATION`、`HUMAN_TRANSPORT_FIX_REQUIRED`、`PUBLIC_QA_UNVERIFIED` 或 `CANONICAL_CHANGE_REQUESTED`。平台传输修复返回给人工的一份合并清单，再回到同一 G；只有带用户请求 ID 的 `CANONICAL_CHANGE_REQUESTED` 能回到 W → R → G。

`HUMAN_ACCEPTED` 后，标题层级仅凭公开读者页的渲染视觉判断。提供足以辨别页面标题、章节、子章节、顺序和扁平化/重复问题的视觉证据；编辑器 HTML/DOM、公开源码、Feed 与 JSON 快照均不能覆盖该结论。证据不足是 `PUBLIC_QA_UNVERIFIED`，可见层级问题使用稳定 `PUBLIC-VISUAL-HIERARCHY-NNN` 并交由人工修复决定。

机器字段、HTML 模板签名、`Alt：` 标记、路径与状态码保持不变。
