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

本 Skill 只对持有有效租约期间观察和操作浏览器的行为负责。浏览器执行由 `BACKLINK_BROWSER_PROVIDER` 在 Run Item 开始前选择，默认 `ego-browser`，可显式选择 `agent-browser`。同一个 Run Item 一旦锁定 provider，就不得中途切换。所有网页、登录、表单、验证码交接、站点原生验证、截图和已授权 Gmail 网页操作都必须通过已锁定 provider 完成；Google 托管邮箱验证邮件读取仍优先使用已授权的 `gws`。Queue API/CLI 只用于 Shipmore 任务领取、heartbeat、outbound-link 注册和状态回写。

绝不要创建并行 Markdown 队列、本地队列游标或第二份规范提交记录。

## 必需配置

使用非敏感的运行时环境变量。绝不要打印 agent token。

```text
BACKLINK_APP_URL=https://shipmore.app
BACKLINK_AGENT_TOKEN=<secret>
BACKLINK_WORKER_ID=<stable worker alias; managed runtime may generate a persistent unique ID>
BACKLINK_BROWSER_PROVIDER=ego-browser|agent-browser  # default ego-browser
BACKLINK_EGO_BROWSER_SKILL=<optional local ego-browser SKILL.md path>
BACKLINK_AGENT_BROWSER_AUTH_STATE=<optional secure path to Chrome-exported auth seed>
AGENT_BROWSER_ENCRYPTION_KEY=<required 64-hex production key>
AGENT_BROWSER_STATE_EXPIRE_DAYS=36500
AGENT_BROWSER_NAMESPACE=shipmore
SHIPMORE_TERMINAL_STATE_RETENTION_DAYS=7
SHIPMORE_CONCURRENCY=<optional worker-pool size, default 4>
SHIPMORE_DEBUG_IGNORE_HISTORY=0|1  # debug only; default 1
```

完整环境变量模板见 [`example.env`](example.env)。其中包含用户配置项、可选路径覆盖项以及 managed runtime 自动注入的内部变量。

调用方还必须提供 Shipmore `runId`。

在任何可变操作前阅读以下参考文件：

1. [references/shipmore-api.md](references/shipmore-api.md)
2. [references/status-mapping.md](references/status-mapping.md)
3. [references/worker-loop.md](references/worker-loop.md)
4. [references/browser-control-routing.md](references/browser-control-routing.md)
5. [references/account-authentication.md](references/account-authentication.md)
6. [references/entry-and-content-routing.md](references/entry-and-content-routing.md)
7. [EXEC-CHECKLIST.md](EXEC-CHECKLIST.md)
8. [references/parallel-execution.md](references/parallel-execution.md)（仅并发执行时）
9. [references/production-hardening.md](references/production-hardening.md)（生产边界和未解决缺口）

浏览器前置要求：先读取 [references/browser-control-routing.md](references/browser-control-routing.md)，随后按 provider 读取 [references/agent-browser-runtime.md](references/agent-browser-runtime.md) 或 [references/ego-browser-runtime.md](references/ego-browser-runtime.md)。claim 后先用 `scripts/browser_action_guard.py select --run-item-id <id> --provider <provider>` 锁定 provider。`ego-browser` 为默认 provider；`agent-browser` 可显式选择，仍固定为 0.38.1 并执行 adapter preflight。整个 Run Item 不得切换 provider，也不得转到 browser-harness、CUA、Playwright、Chrome DevTools MCP、Browser Use 或共享的人类 Chrome。账号类阻塞若需要换 provider，必须创建新的 Run / Run Item。

## 事实来源规则

1. 在打开或修改目录提交流程前，必须先执行 `claim`。
2. 将成功 claim 返回的 `data.id` 视为 `runItemId`。
3. 将 claim 载荷视为已验证的任务信封。正常模式下保留既有 Submission 字段；当 `SHIPMORE_DEBUG_IGNORE_HISTORY=1` 时，Queue client 会给 worker 返回去历史化视图（`debugHistoryIgnored=true`），此时只把 Product、Directory、有效提交身份和实时网页事实用于业务判断，不得自行找回/使用被屏蔽的历史 Submission 字段。
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
3. 正常模式下，在浏览器操作前检查返回的既有 Submission 快照；调试模式（`debugHistoryIgnored=true`）跳过历史生命周期判断，从当前网站重新观察。
4. 正常模式下，如果快照已经证明不应进行新的表单操作，则将 Run Item 以 `skipped` 完成并保留当前 submission status；调试模式不得因为被屏蔽的历史状态提前跳过，但仍必须执行当前站点的实时重复项检查。
5. Managed runtime（`SHIPMORE_MANAGED_LEASE=1`）必须由 `scripts/lease_keeper.py` 自动维护 heartbeat，并通过 lease guard 阻止失去租约后的浏览器可变操作；direct/manual 模式仍需在任何可变操作前和耗时步骤后显式 heartbeat。300 秒租约默认每 60 秒自动 heartbeat。
6. 按 [references/worker-loop.md](references/worker-loop.md) 的强制预检顺序执行：不可用 → 仅付费 → 必需 backlink 注册与验证 → 其他不符合资格 → 既有生命周期/重复项 → 入口和内容面分类 → 已授权的账号登录/注册/邮箱验证 → 缺少已验证资料 → 其他验证 → 可变表单操作。
7. 只执行真实且已授权的表单操作。可选的未知字段保持为空；只有在前置的终止性资格/政策检查通过后，才因必填未知字段阻塞任务。
8. 按 [EXEC-CHECKLIST.md](EXEC-CHECKLIST.md) 在最终动作前执行检查单；有未通过项目时不得执行 Submit、Publish、Claim 或其他不可逆动作。`agent-browser` provider 使用 adapter `final-click`；`ego-browser` provider 必须使用 `browser_action_guard.py final-begin` 建立 durable fence 后才允许执行一次最终动作，并随后标记 dispatched/resolve。任何 provider 都不得裸执行可重复的最终点击。
9. 记录准确的页面/服务器结果，并在有证据时记录不透明的 evidence reference。
10. 使用 [references/status-mapping.md](references/status-mapping.md) 对结果分类。
11. 结果分类后再次执行检查单；未通过时不得把结果标记为成功。
12. 有 Final Action 时，优先使用 durable final-action journal 返回的 `completionEventId` 作为稳定 Complete `eventId`；没有 Final Action 的 blocked/skipped/failed 路径才生成新的稳定 event ID。HTTP 响应丢失时重复使用同一个 ID。
13. 完成该任务。同一个逻辑完成操作绝不能生成新的 event ID。
14. 只有在前一个任务得到终止性 Run Item 结果后，才能 claim 下一个任务。

## 浏览器执行规则

- 所有浏览器操作必须落在当前 Run Item 已锁定的 provider 上。`agent-browser` 使用 deterministic named session + adapter；`ego-browser` 使用独立 TaskSpace/Page，并在每次可变动作前调用 `scripts/browser_action_guard.py mutation-check --run-item-id <id>`。两种 provider 都必须受同一个 Shipmore lease、final-action journal、字段真实性和结果分类规则约束；浏览器 provider 只执行页面动作，页面字段语义、Shipmore 字段映射和结果分类仍由 Codex 完成。
- 登录状态必须以当前已锁定 provider 的实时页面证据为准：优先检查当前站点的账号菜单、用户标识、Dashboard/Logout 入口和受保护提交页面是否可用。claim 返回的历史 `exactResult`、其他 provider/浏览器会话的登录状态、公开页面或 URL 本身都不能单独证明当前会话已登录。调试模式下历史 `exactResult` 本身会被屏蔽，禁止从其他接口或日志重新补回用于当前决策。
- 如果当前 provider 上下文已显示与有效提交身份匹配的已登录账号，可以复用该会话继续执行。提交入口重定向到登录页或显示 `Login Required` 时，只能视为进入账号认证阶段，必须打开登录页并按 [references/account-authentication.md](references/account-authentication.md) 尝试已授权的现有会话、Google/GitHub OAuth、邮箱验证码或 magic link；只有所有安全授权路径都不可用或失败后，才可回写 `blocked_account_or_email_policy`。不得猜测、导出或复制 Cookie/会话材料。
- 按 [references/entry-and-content-routing.md](references/entry-and-content-routing.md) 从规范首页、导航、页脚、站内搜索和真实控件确认入口；在填写字段前完成站内重复查询并核对候选实际出站 URL。目录表单、产品资料页、claim listing、内容编辑器和官方联系邮件必须分别分类。
- 按 [EXEC-CHECKLIST.md](EXEC-CHECKLIST.md) 在最终动作前和结果判断后各执行一次检查单，并记录检查结果和 evidence reference。
- 优先使用提供的 `submitUrl`；如果站点发生重定向，先检查并规范化目标地址再导航。
- 有可用的已授权会话时优先复用。对于 agent-browser，Chrome 导出的 auth seed 只允许作为不透明运行时输入初始化全新 Run Item session；已有 restore state 永远优先，不能被 seed 覆盖。生产 seed 应来自专用的 “Shipmore Worker” Chrome Profile，而不是日常浏览器 Profile。worker 不得读取、解析、打印或修改 seed 内容。ego-browser 不读取该 auth seed，而使用其自身 provider 会话。生产 restore state 必须设置 `AGENT_BROWSER_ENCRYPTION_KEY`。agent-browser 自带的纯年龄过期设为高 safety ceiling（`AGENT_BROWSER_STATE_EXPIRE_DAYS=36500`）；真正的清理由 Shipmore terminal lifecycle 驱动，默认 terminal 后保留 7 天。
- 目录需要身份验证时，遵循 [references/account-authentication.md](references/account-authentication.md)。使用 claim 载荷中的有效 `productContactEmail` 作为账号邮箱，并按以下顺序尝试已授权方式：已有 Google 会话、已有 GitHub 会话、站点原生邮箱验证码或 magic link（对于 Google 托管邮箱，优先使用已授权的 `gws`；仅当 `gws` 不可用时，才使用 `https://mail.google.com` 上现有且匹配的 Gmail 会话），最后才使用邮箱/密码。只有站点明确报告该邮箱没有账号时，才创建一个普通免费账号；身份验证成功后继续原始提交。
- 绝不要在 Shipmore evidence 中打印、持久化、截图或写入凭据、OTP、magic link 或邮箱内容。运行时凭据位于配置的仓库外部敏感文件中。
- 绝不要绕过 CAPTCHA、Turnstile、邮箱验证、浏览器安全警告或站点访问控制。允许使用已授权邮箱完成站点正常的邮箱验证；不允许绕过或削弱验证。
- 不得订阅 newsletter、接受可选推广、支付费用、手动修改 Product 网站、修改 DNS 或创建无关公开内容。必需的 backlink/badge 只能通过 Shipmore 已授权的 outbound-link endpoint 及下方验证流程处理。
- 当目录出现 `backlink`、`reciprocal link`、`reciprocal backlink`、`permanent backlink`、`badge required` 或同义要求时，**这些文字本身绝不能作为 `ineligible` 依据**。必须先把它们视为 Shipmore outbound-link 候选：发送 heartbeat，使用当前 `runItemId` / `workerId` 调用 `POST /api/outbound-links`，并在任何目录表单操作前验证 Product 首页。
- 如果 outbound-link 注册并验证成功，且目录要求本质上只是“Product 网站存在指向目录的链接”，无论页面使用 backlink、reciprocal、permanent、badge 等措辞，都视为该前置条件已满足，**必须继续原始登录/表单/提交流程**，不得因为“需要互链”再次改判 `ineligible`。
- Badge 与反链验证可等价处理：如果站点的原生 Badge 校验实际只检查 Product 首页是否存在指向该站的链接，则 Shipmore outbound-link 的精确 hostname/path 验证即可作为 Badge 验证依据。只有页面有明确证据证明普通链接不足，并额外强制特定 Badge 图片、指定 HTML/属性/script、指定锚文本且 outbound-link 无法产生、或精确 listing URL 等 Shipmore endpoint 无法满足的站点修改时，才进入“额外站点修改”判断；不要仅根据 `badge`、`permanent`、`reciprocal` 等词推断这一点。
- 每 20 秒轮询一次 `productUrl` 首页 HTML，最多 6 次。注册前和每次尝试前都发送 heartbeat；一旦失去租约所有权立即停止。只有在首页 HTML（或客户端渲染 HTML 时的最终浏览器 DOM）中看到与 `directoryUrl` 完全匹配的已解析 `<a href>` 后，才能继续原始目录提交。
- 链接比较使用解析后的 hostname 和 path：scheme 以及 query/fragment 不参与身份判断，开头的 `www.` 和结尾斜杠会被规范化；除此之外 hostname 和 path 必须完全匹配。绝不能使用子字符串匹配。不要绕过 CAPTCHA、WAF 或访问控制来验证页面。
- 如果 6 次检查全部失败，不得提交。使用最接近事实的 blocked/ineligible 状态完成任务，并在 exact result/error 中包含 `backlink verification timeout`。
- 不得虚构创始人、公司、地址、上线时间、价格、联系方式、法律身份、所有权或开源事实。
- 使用返回的已验证 Product 字段作为表单主要输入。`productDescription` 和 `productMarkdown` 可以用于生成符合长度限制的真实文案，但不得用来捏造独立的身份或联系方式事实。
- 将 `productContactEmail` 视为表单输入，而不是日志材料。不要仅因为提交过它，就把它复制到 `exactResult`、证据标签或可分享的尝试记录中。
- 点击、导航、清空表单、按钮禁用或普通感谢页本身都不能证明提交成功。
- `submitted` 不等于 `published`。
- 最终动作结果不明时必须改为 `submission_outcome_unknown`；绝不能盲目再次点击 Submit。只要本机 final-action journal 已存在，无论状态为 prepared/attempting/dispatched/outcome_unknown，都不得再次执行同一 action type。
- 当前 provider 出现超时、空响应、元素不存在、页面状态不明或写入校验失败时，不得直接重跑；按对应 runtime 文档获取新的只读证据后，只有下一步与上次实质不同才允许一次受控重试。Submit、Publish、Claim 和 Gmail Send 在任何 provider 下均不得重试。
- 不得把原始邮箱、电话、密码、OTP、magic link、Cookie、session ID、token URL、本机路径或进程参数写入 `lastError`、`exactResult`、`evidenceReference`、`followUpNote` 或 retry diagnostic。

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

推荐生产运行方式：

```bash
python3 scripts/shipmore_worker.py --run-id <runId> -- <one-item-agent-command>
```

Managed runtime 会自动启动 LeaseKeeper，并要求 one-item processor 使用相同 worker ID claim（得到 `reason=reused`）取得完整任务信封；processor 完成一个 Run Item 后必须退出。并发时由 `shipmore_worker_pool.py` 启动多个 managed runtime。

低级 Queue 调试仍可使用随附客户端：

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
- [references/agent-browser-runtime.md](references/agent-browser-runtime.md)：`agent-browser` session 生命周期、snapshot/ref、表单写入校验、标签页、诊断、恢复和最终动作规范。
- [references/ego-browser-runtime.md](references/ego-browser-runtime.md)：默认 `ego-browser` provider 的 TaskSpace/Page、lease guard、final-action fence 和认证边界。
- [references/account-authentication.md](references/account-authentication.md)：默认账号的授权登录、免费注册、安全运行时凭据，以及优先使用 `gws`、不可用时回退 Gmail 的验证流程。
- [references/entry-and-content-routing.md](references/entry-and-content-routing.md)：入口发现、站内去重和内容面 no-action 分类。
- [references/parallel-execution.md](references/parallel-execution.md)：多 worker 并发模型、managed worker runtime、唯一 worker identity 和 host affinity。
- [references/production-hardening.md](references/production-hardening.md)：生产缺陷清单、P0/P1 已实现保护和仍需服务端解决的 fencing/affinity 边界。
- [EXEC-CHECKLIST.md](EXEC-CHECKLIST.md)：最终动作前后的执行检查单。
- `scripts/agent_browser_adapter.py`：agent-browser provider 的 deterministic session、safe mutation、durable final-click、diagnostics 和 lifecycle cleanup。
- `scripts/browser_action_guard.py`：跨 provider 的 Run Item provider lock、lease mutation gate 和 ego-browser final-action durable fence。
- `scripts/lease_keeper.py`：自动 heartbeat 和 lease guard。
- `scripts/final_action_guard.py`：Final Action durable 本地 fence 和稳定 completion event ID。
- `scripts/worker_identity.py`：跨重启持久化的唯一 worker instance ID。
- `scripts/shipmore_worker.py`：真正长驻的 managed Queue/lease runtime。
- `scripts/shipmore_worker_pool.py`：跨 Windows/Linux 的 wait-any 并发进程 supervisor。
- `scripts/shipmore_queue_client.py`：Queue/outbound-link API 客户端；Complete 明确成功后登记 terminal session cleanup。
- `scripts/runtime_cleanup.py`：只清理本机已确认 terminal 的 agent-browser restore state。
- `scripts/diagnostic_sanitizer.py`：在 Console/Network/Snapshot diagnostics 离开 adapter 前做结构化脱敏。
- `runtime/agent-browser.version`：生产 agent-browser 精确版本。
