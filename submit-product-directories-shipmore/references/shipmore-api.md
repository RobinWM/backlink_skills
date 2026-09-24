# Shipmore Queue API 契约

## 端点

Queue 的 claim/heartbeat/complete/recover 使用以下认证端点：

```text
POST {BACKLINK_APP_URL}/api/backlinks/agent/queue
Authorization: Bearer {BACKLINK_AGENT_TOKEN}
Content-Type: application/json
```

不得在 campaign record、证据、截图或 completion metadata 中记录 bearer token。

必需 backlink 注册使用独立端点：

```text
POST {BACKLINK_APP_URL}/api/outbound-links
Authorization: Bearer {BACKLINK_AGENT_TOKEN}
Content-Type: application/json
```

请求体：

```json
{
  "runItemId": "<leased-run-item-id>",
  "workerId": "<same-worker-id-used-to-claim>"
}
```

调用前发送 heartbeat。非成功响应或租约丢失/归属异常/过期都是本 worker 尝试的终止条件：停止，不要继续提交目录。

随附的 `add-outbound-link` 命令会完成注册和验证：只抓取 Product 首页，跟随普通 HTTP 重定向，解析 `<a href>`，每 20 秒轮询，最多 6 次。hostname/path 必须精确匹配；`http/https`、开头 `www.` 和结尾斜杠可不同。超时输出 `backlink verification timeout` 并以非零状态退出。

## Claim

请求：

```json
{
  "operation": "claim",
  "runId": "<run-id>",
  "workerId": "<stable-worker-id>",
  "leaseSeconds": 300
}
```

成功的 claim 会返回 `data.id`，将其作为后续 heartbeat 和 complete 的 `runItemId`。载荷还包含既有提交元数据、目录属性、Product 资料、资源、`productMarkdown` 和 `productTemplate`（若有）。

`reason` 含义：

- `claimed`：新任务已租给本 worker；
- `reused`：同一 `runId + workerId` 已持有活跃任务，应恢复返回的任务；
- `run_paused`：Run 暂停，不得执行可变浏览器操作；
- `run_terminal`：Run 已完成或取消，停止；
- `queue_empty`：没有排队任务，停止 worker loop；
- `run_not_found`：Run 无效，视为配置/错误状态。

响应可能丢失时，用相同 `runId` 和 `workerId` 重试 claim，预期返回 `reused`。

## Heartbeat

请求：

```json
{
  "operation": "heartbeat",
  "runItemId": "<run-item-id>",
  "workerId": "<same-worker-id-used-to-claim>",
  "leaseSeconds": 300
}
```

Heartbeat 会将 claimed 任务转为 running，并从 heartbeat 时间延长租约。收到 `409 Lease is missing, expired, or owned by another worker` 时必须停止修改目录，也不得假装仍拥有任务而调用 complete。

## Complete

请求示例：

```json
{
  "operation": "complete",
  "eventId": "<stable-id-for-this-logical-completion>",
  "runItemId": "<run-item-id>",
  "workerId": "<same-worker-id>",
  "status": "completed",
  "submissionStatus": "awaiting_approval",
  "verificationStatus": "no_verification_presented",
  "exactResult": "Submission accepted and queued for review",
  "evidenceReference": "ev-opaque-123",
  "publicListingUrl": null,
  "followUpAt": null,
  "followUpNote": null
}
```

Run Item 的终止状态：

```text
completed
blocked
failed
skipped
```

可选字段：`verificationStatus`、`lastError`、`exactResult`、`evidenceReference`、`publicListingUrl`、`backendCheckedAt`、`mailboxCheckedAt`、`publicPageCheckedAt`、`followUpAt`、`followUpNote`。时间必须是 API 接受的 ISO 8601 日期时间。`failed` 必须有非空 `lastError`；`published` 必须有非空公开列表 URL。

### Complete 幂等

`eventId` 标识一个逻辑完成操作。第一次请求前生成并保留稳定 event ID；响应丢失或不确定时，用相同 event ID 和相同逻辑字段重试。

```text
第一次成功：idempotent = false
同一操作重试：idempotent = true
```

不要仅因网络响应丢失就生成新的 event ID。

## Recover

恢复所有过期租约：

```json
{"operation":"recover"}
```

只恢复一个 Run：

```json
{"operation":"recover","runId":"<run-id>"}
```

恢复会把过期的 claimed/running 任务改回 queued，清除 worker/lease 字段并记录恢复错误。租约过期本身不会立即改写记录，后续 recover 或 claim 才会触发转换。

## 租约策略

API 接受 30–3600 秒租约。交互式浏览器任务使用 300 秒时，目标是每 60–120 秒 heartbeat；可预测的长步骤可使用更长租约，但仍要定期 heartbeat。用户交接前尽可能延长租约；过期后停止作为所有者操作，让 recover/reclaim 建立新租约。

## Claim 载荷是任务信封

worker 必须以返回的 claim 载荷作为契约，不得依赖 Shipmore 内部数据库结构。字段可能来自 Product 事实、用户提交默认值或产品级覆盖值，Shipmore 会在返回任务前完成解析。

### Run Item

```text
id
runId
queueOrder
status
claimedBy
claimedAt
heartbeatAt
leaseExpiresAt
```

### 既有 Submission 快照

```text
productDirectoryId
submissionStatus
verificationStatus
route
accountAlias
submittedAt
exactResult
evidenceReference
publicListingUrl
backendCheckedAt
mailboxCheckedAt
publicPageCheckedAt
lastCheckedAt
followUpAt
followUpNote
```

### Directory

```text
directoryId
directoryName
directoryUrl
submitUrl
directoryPricing
directoryCategory
directoryDofollow
directoryAccountRequired
```

### Product 事实和内容

```text
productId
productName
productUrl
productDescription
productCategoryId
productTagline
productPricingModel
productTwitterUrl
productGithubRepoUrl
productLogo
productOgImage
productMarkdown
productTemplate
```

`productGithubRepoUrl` 是 Product 的官方仓库/源码 URL，仅有该字段不能证明开源。需要 OSS 资格时必须有独立已验证证据。

### 有效提交身份

```text
productContactEmail
productCompanyName
productFounderName
productLinkedinUrl
productFounderGithubUrl
```

这些值已经由 Shipmore 根据账号默认值和产品覆盖值解析完成。不要在 Skill 中重建回退逻辑。优先使用明确字段；`productMarkdown` 只能概括已有事实，不能虚构创始人、公司、邮箱、上线时间、价格、社交账号或开源状态。

如果专用 claim 字段为空，不得从无关文本静默推断。可在运行时清楚验证官方产品站点的当前事实，否则使用 `blocked_missing_verified_data`。`productContactEmail` 只能用于授权表单，不得复制到 exactResult、证据标签、截图或可分享日志。

`directoryDofollow` 只是目录元数据，不能作为操纵排名或索要 followed link 的指令。
