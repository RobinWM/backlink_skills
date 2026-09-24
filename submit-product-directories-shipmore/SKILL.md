---
name: submit-product-directories-shipmore
description: Shipmore 驱动的产品目录提交 worker。消费 Shipmore Queue API 提供的持久化提交 Run，持续维护租约，以返回的 Product/Directory/Submission 快照作为事实来源，按照 SPD V1 Batch 安全规则执行已授权的浏览器表单操作，准确分类结果，并以幂等方式完成 Run Item。仅当 Shipmore 已创建提交 Run、需要 Codex 作为浏览器 worker 执行时使用。不要创建第二个本地队列，也不要用推断出的成功结果覆盖 Shipmore 状态。
---

# Shipmore 目录提交 Worker

## 角色

本 Skill 是执行 worker，不是队列所有者。

以下内容以 Shipmore 为权威来源：

- Product × Directory 的当前状态（`product_directory`）；
- 持久化的 Run / Run Item 顺序；
- 活跃任务去重；
- worker 租约与恢复；
- 只追加的完成事件；
- 后续跟进调度；
- 提供给目录表单使用的已验证 Product 事实和有效提交身份。

本 Skill 只对持有有效租约期间观察和操作浏览器的行为负责。

绝不要创建并行 Markdown 队列、本地队列游标或第二份规范提交记录。

## 必需配置

使用非敏感的运行时环境变量。绝不要打印 agent token。

```text
BACKLINK_APP_URL=https://shipmore.app
BACKLINK_AGENT_TOKEN=<secret>
BACKLINK_WORKER_ID=<stable worker alias, e.g. codex-windows-01>
```

调用方还必须提供 Shipmore `runId`。

在任何可变操作前阅读以下参考文件：

1. [references/shipmore-api.md](references/shipmore-api.md)
2. [references/status-mapping.md](references/status-mapping.md)
3. [references/worker-loop.md](references/worker-loop.md)
4. [references/browser-control-routing.md](references/browser-control-routing.md)
5. [references/account-authentication.md](references/account-authentication.md)

## 事实来源规则

1. 在打开或修改目录提交流程前，必须先执行 `claim`。
2. 将成功 claim 返回的 `data.id` 视为 `runItemId`。
3. 将 claim 载荷视为已验证的任务信封。不要用猜测替换其中的 Product、Directory 或既有 Submission 字段，也不要在 Skill 中重新实现 Shipmore 内部的默认值/覆盖值逻辑。
4. 优先使用明确的 Product 事实（`productTagline`、`productPricingModel`、`productTwitterUrl`、`productGithubRepoUrl`）和有效提交身份（`productContactEmail`、`productCompanyName`、`productFounderName`、`productLinkedinUrl`、`productFounderGithubUrl`），再从 `productDescription` 或 `productMarkdown` 推导内容。
5. `productGithubRepoUrl` 是 Product 仓库地址；`productFounderGithubUrl` 是个人资料地址。绝不能互相替换。旧字段 `productGithubUrl` 仅用于兼容，并表示创始人的 GitHub 地址。
6. 仅凭 GitHub 仓库地址不能证明开源状态、许可证或 OSS 资格。
7. 可以概括或缩短已支持的产品文案，但不得虚构邮箱、创始人、公司、法律身份、价格、社交账号或开源状态等独立事实。
8. `reason=claimed` 表示新任务已租给本 worker；`reason=reused` 表示本 worker 已经持有一个有效任务，应恢复该任务，不得推进队列。
9. 租约过期后绝不能继续操作 Run Item。有任何疑问时先发送 heartbeat。
10. 本 Skill 绝不能通过直接访问数据库改变 Shipmore 状态。必须使用 Queue API 和已授权的 outbound-link endpoint。
11. 当前 Run Item 被跳过时，不得仅因为跳过就把此前真实的 `published` 或 `awaiting_approval` 状态改成 `not_attempted`。

## Worker 生命周期

每个任务按以下顺序执行：

1. 从指定 Run claim 一个任务。
2. 如果 Run 已暂停、已结束或为空，按照 API 参考中的说明停止或等待。
3. 在浏览器操作前检查返回的既有 Submission 快照。
4. 如果快照已经证明不应进行新的表单操作，则将 Run Item 以 `skipped` 完成，同时保留当前 submission status。
5. 在任何可变浏览器操作前发送 heartbeat；在重要导航、验证、用户交接或长时间推理后再次发送。300 秒租约通常应每 60–120 秒发送一次 heartbeat；较长的浏览器操作可在 API 限制内申请更长租约。
6. 按 [references/worker-loop.md](references/worker-loop.md) 的强制预检顺序执行：不可用 → 仅付费 → 必需 backlink 注册与验证 → 其他不符合资格 → 既有生命周期/重复项 → 已授权的账号登录/注册/邮箱验证 → 缺少已验证资料 → 其他验证 → 可变表单操作。
7. 只执行真实且已授权的表单操作。可选的未知字段保持为空；只有在前置的终止性资格/政策检查通过后，才因必填未知字段阻塞任务。
8. 记录准确的页面/服务器结果，并在有证据时记录不透明的 evidence reference。
9. 使用 [references/status-mapping.md](references/status-mapping.md) 对结果分类。
10. 第一次尝试 `complete` 前选择一个稳定的 `eventId`。如果 HTTP 响应丢失或请求需要重试，重复使用同一个 event ID。
11. 完成该任务。同一个逻辑完成操作绝不能生成新的 event ID。
12. 只有在前一个任务得到终止性 Run Item 结果后，才能 claim 下一个任务。

## 浏览器执行规则

- 优先使用提供的 `submitUrl`；如果站点发生重定向，先检查并规范化目标地址再导航。
- 有可用的已授权会话时优先复用。不要检查 Cookie、已保存密码、本地存储、恢复码或隐藏的身份验证材料。
- 目录需要身份验证时，遵循 [references/account-authentication.md](references/account-authentication.md)。使用 claim 载荷中的有效 `productContactEmail` 作为账号邮箱，并按以下顺序尝试已授权方式：已有 Google 会话、已有 GitHub 会话、站点原生邮箱验证码或 magic link（对于 Google 托管邮箱，优先使用已授权的 `gws`；仅当 `gws` 不可用时，才使用 `https://mail.google.com` 上现有且匹配的 Gmail 会话），最后才使用邮箱/密码。只有站点明确报告该邮箱没有账号时，才创建一个普通免费账号；身份验证成功后继续原始提交。
- 绝不要在 Shipmore evidence 中打印、持久化、截图或写入凭据、OTP、magic link 或邮箱内容。运行时凭据位于配置的仓库外部敏感文件中。
- 绝不要绕过 CAPTCHA、Turnstile、邮箱验证、浏览器安全警告或站点访问控制。允许使用已授权邮箱完成站点正常的邮箱验证；不允许绕过或削弱验证。
- 不得订阅 newsletter、接受可选推广、支付费用、手动修改 Product 网站、修改 DNS 或创建无关公开内容。必需的 backlink/badge 只能通过 Shipmore 已授权的 outbound-link endpoint 及下方验证流程处理。
- 当目录要求 backlink 或 badge 时，先发送 heartbeat，再使用租约中的 `runItemId` 和同一个 `workerId` 调用 `POST /api/outbound-links`，然后在执行任何目录表单操作前验证 Product 首页。不要立即将其分类为 `ineligible`。
- 每 20 秒轮询一次 `productUrl` 首页 HTML，最多 6 次。注册前和每次尝试前都发送 heartbeat；一旦失去租约所有权立即停止。只有在首页 HTML（或客户端渲染 HTML 时的最终浏览器 DOM）中看到与 `directoryUrl` 完全匹配的已解析 `<a href>` 后，才能继续原始目录提交。
- 链接比较使用解析后的 hostname 和 path：scheme 以及 query/fragment 不参与身份判断，开头的 `www.` 和结尾斜杠会被规范化；除此之外 hostname 和 path 必须完全匹配。绝不能使用子字符串匹配。不要绕过 CAPTCHA、WAF 或访问控制来验证页面。
- 如果 6 次检查全部失败，不得提交。使用最接近事实的 blocked/ineligible 状态完成任务，并在 exact result/error 中包含 `backlink verification timeout`。
- 不得虚构创始人、公司、地址、上线时间、价格、联系方式、法律身份、所有权或开源事实。
- 使用返回的已验证 Product 字段作为表单主要输入。`productDescription` 和 `productMarkdown` 可以用于生成符合长度限制的真实文案，但不得用来捏造独立的身份或联系方式事实。
- 将 `productContactEmail` 视为表单输入，而不是日志材料。不要仅因为提交过它，就把它复制到 `exactResult`、证据标签或可分享的尝试记录中。
- 点击、导航、清空表单、按钮禁用或普通感谢页本身都不能证明提交成功。
- `submitted` 不等于 `published`。
- 最终动作结果不明时必须改为 `submission_outcome_unknown`；绝不能盲目再次点击 Submit。

## 既有状态保护

表单操作前，检查 claim 载荷中的 `submissionStatus`。

以下状态存在时，不得自动重新提交：

```text
submitted
submission_outcome_unknown
awaiting_approval
awaiting_email_verification
published
```

对于这些状态，只执行适当的验证/跟进操作，或者跳过并保留当前状态。此前的最终动作结果不明时，必须先通过可用的账号/后端、已授权邮箱或公开页面证据进行检查，之后才能考虑重试。对于 `awaiting_email_verification`，使用 `account-authentication.md` 中的已授权 Gmail 邮箱流程：优先使用 `gws`；只有 `gws` 不可用时，才使用现有的匹配 Gmail 浏览器会话。

## CLI 辅助工具

使用随附的标准库客户端：

```bash
python3 scripts/shipmore_queue_client.py claim --run-id <runId>
python3 scripts/shipmore_queue_client.py heartbeat --run-item-id <runItemId>
python3 scripts/shipmore_queue_client.py add-outbound-link \
  --run-item-id <runItemId> \
  --product-url <productUrl> \
  --directory-url <directoryUrl>
python3 scripts/shipmore_queue_client.py recover --run-id <runId>
```

在 Windows 上，环境支持时可以使用 `python` 或 `py -3`。

完成示例：

```bash
python3 scripts/shipmore_queue_client.py complete \
  --run-item-id <runItemId> \
  --event-id <stableEventId> \
  --status completed \
  --submission-status awaiting_approval \
  --verification-status no_verification_presented \
  --exact-result "Submission accepted and queued for review"
```

环境变量可用时，不要把 `BACKLINK_AGENT_TOKEN` 放在命令行中。

## 停止条件

出现以下情况时，停止浏览器执行并保留真实状态：

- 租约缺失、已过期或归属于其他 worker；
- Run 已暂停、取消或完成；
- 路由仅付费且没有支付授权；
- 必需 backlink 注册被拒绝、轮询期间失去租约，或首页验证 6 次超时；
- 在前置资格/政策检查通过后仍缺少必需的已验证 Product 资料；
- 无法安全继续手动验证或身份验证；
- 账号/邮箱政策要求执行 `account-authentication.md` 当前授权范围之外的操作；
- 最终提交结果不明确；
- 执行后端无法安全控制所需的已认证界面。

使用 status mapping 中最接近事实的 submission status，并将 Run Item 结果设为 blocked、failed 或 skipped。

## 随附资源

- [references/shipmore-api.md](references/shipmore-api.md)：API 契约和响应语义。
- [references/status-mapping.md](references/status-mapping.md)：规范的 Shipmore 状态映射。
- [references/worker-loop.md](references/worker-loop.md)：确定性的 worker 流程、Product 字段映射、预检顺序和重试规则。
- [references/browser-control-routing.md](references/browser-control-routing.md)：与后端无关的浏览器选择和验证规则。
- [references/account-authentication.md](references/account-authentication.md)：默认账号的授权登录、免费注册、安全运行时凭据，以及优先使用 `gws`、不可用时回退 Gmail 的验证流程。
- `scripts/shipmore_queue_client.py`：无第三方依赖的 Queue/outbound-link API 客户端和首页 backlink 验证器。
