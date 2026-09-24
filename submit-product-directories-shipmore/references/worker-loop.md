# Shipmore worker 流程

## 确定性循环

同一个 Shipmore Run 中，同一个 worker 实例的所有 claim 和 heartbeat 都使用稳定的 worker ID。

```text
while true:
  claim(runId, workerId)

  if run_not_found:
    stop with configuration error

  if run_paused:
    stop mutable work; wait for resume/new instruction

  if run_terminal:
    stop

  if queue_empty:
    stop

  task = claim.data
  runItemId = task.id

  inspect previous submission snapshot

  if no new action is appropriate:
    complete(skipped, preserve current submissionStatus)
    continue

  heartbeat(runItemId)
  browser preflight + legitimacy/authorization checks
  if mandatory backlink/badge:
    register outbound link; poll and verify Product homepage
    if verification fails: complete truthfully; do not submit
  run EXEC-CHECKLIST.md before final action
  perform one verified final action
  heartbeat(runItemId)
  inspect exact final result
  classify result
  run EXEC-CHECKLIST.md after result classification
  complete(stable eventId)
```

## 打开浏览器前

所有浏览器、目录原生验证和 Gmail 操作必须通过 `ego-browser` skill 完成。Queue API/CLI 只负责 Shipmore 的 claim、heartbeat、outbound-link、recover 和 complete，不代替页面点击或填写。

确认：

- `runItemId = claim.data.id`；
- `claimedBy` 与当前 worker 一致；
- 租约尚未过期；
- Product 和 Directory 数据足以支持下一步只读检查；
- 既有 `submissionStatus` 不禁止盲目重投。

优先使用 `submitUrl`。如果它是首页或重定向到其他官方提交路由，必须在任何表单修改前检查目标地址。

## 强制预检顺序

按以下顺序执行只读检查，避免后续较弱的缺失字段掩盖更早的终止性政策结果：

1. **路由/站点不可用**：官方提交路由消失、关闭或不可用时，分类为 `unavailable`。
2. **仅付费**：路由要求未获授权的付款时，分类为 `paid_only` 并停止。
3. **必需 backlink/badge**：不要立即分类为不符合资格。使用下方已授权的 Shipmore outbound-link 注册和首页验证流程；只有验证成功才继续，超时则在提交前停止。
4. **其他不符合资格**：不支持的资格、禁止的非 backlink 站点修改或无关商业/社区动作分类为 `ineligible`。
5. **重复项/既有生命周期保护**：检查既有 Shipmore 状态和明确的现有列表。绝不盲目重投 `submitted`、`submission_outcome_unknown`、`awaiting_approval`、`awaiting_email_verification` 或 `published`。
6. **入口和内容面分类**：按照 [entry-and-content-routing.md](entry-and-content-routing.md) 从首页、导航、页脚、站内搜索和真实控件确认当前入口；在填写字段前完成站内重复查询，并核对候选实际出站 URL。目录表单、产品资料页、claim listing、内容编辑器和官方 Contact 邮件必须分别分类。`short note — no action`、`long post — no action` 和 `unknown — no action` 立即停止该站的内容动作；只有内容编辑器的站点使用 `ineligible`。
7. **账号认证**：`Login Required`、登录墙或登录重定向只表示进入认证阶段，不是立即阻塞。使用 claim 载荷中的有效 `productContactEmail`，遵循 `account-authentication.md` 依次尝试当前 ego-browser 中匹配的现有会话、Google OAuth、GitHub OAuth、原生邮箱验证码/magic link（Google 托管邮箱优先使用已授权 `gws`，不可用时使用匹配 Gmail 会话），之后才使用运行时密码。只有所有安全授权路径都不可用或失败，或站点要求超出授权范围的手机/KYC/付费/人工批准，才使用 `blocked_account_or_email_policy`。认证成功后必须继续原始提交。
8. **必需的已验证 Product 资料**：路由仍符合资格时，将表单必填项与明确的 Shipmore Product 字段比较。缺失的独立事实使用 `blocked_missing_verified_data`。
9. **验证挑战**：暴露 CAPTCHA、Turnstile、邮箱挑战等原生验证。未解决的人工验证使用 `blocked_manual_verification`。
10. **表单执行**：只有现在才能填写可变的产品目录字段并走向最终动作。

最终 Submit、Publish 或 Claim 前，必须按 [../EXEC-CHECKLIST.md](../EXEC-CHECKLIST.md) 完成 `before_final_action` 检查。任一项目失败都不得执行最终动作。动作完成并分类结果后，再执行 `after_result_classification` 检查；检查失败时不得把结果标记为成功。

例如，目录同时要求联系邮箱和 reciprocal badge 时，先注册并验证 badge。验证超时则停止并记录包含 `backlink verification timeout` 的真实 blocked/ineligible 结果，不要改写成缺少邮箱，也不要提交。

## 必需 backlink 注册与验证

确认线上目录确实要求 backlink 或 badge 后：

1. 确认 claim 的 `runItemId`、`workerId`、`productUrl` 和 `directoryUrl`；发送 heartbeat，租约失败立即停止。
2. 运行：

   ```bash
   python3 scripts/shipmore_queue_client.py add-outbound-link --run-item-id <id> --product-url <productUrl> --directory-url <directoryUrl>
   ```

3. 命令向 `POST {BACKLINK_APP_URL}/api/outbound-links` 发送 `{runItemId, workerId}`，然后每 20 秒只抓取 Product 首页，最多 6 次，每次抓取前发送 heartbeat。
4. 只有首页解析出的 `<a href>` hostname/path 与解析后的 `directoryUrl` 完全匹配才算成功。scheme、开头 `www.` 和结尾斜杠可以不同；拒绝子字符串、伪后缀域名和不同路径。
5. 标准 CLI 检查普通重定向后的服务器 HTML。若链接仅由客户端渲染，授权浏览器可检查最终首页 DOM，但必须使用相同的解析锚点规则。不要检查内页，也不要绕过 CAPTCHA/WAF/访问控制。
6. 只有命令返回 `success=true` 且 `reason=backlink_verified`，或在租约有效期间取得等价的最终 DOM 证据，才能继续原始目录表单。
7. 注册失败、租约丢失或 6 次检查都找不到链接时，在提交前停止。6 次超时记录 `backlink verification timeout`，并使用最接近事实的 blocked/ineligible 状态。

### Badge 与反链的等价判断

如果目录页面把 Badge 作为反链存在性的可视化入口，且其验证只检查 Product 首页是否存在指向该站的链接，则 `reason=backlink_verified` 可以直接满足 Badge 验证，不需要额外插入图片或复制 Badge HTML。只有当页面明确要求特定 Badge 图片、HTML 属性、脚本或精确 listing URL 时，才执行额外的原生 Badge 检查。

## Product 字段映射

目录表单优先使用明确的 claim 字段：

| 目录字段 | Shipmore 来源 |
| --- | --- |
| 产品/工具名称 | `productName` |
| 网站 | `productUrl` |
| 标语 | `productTagline`；为空时可从 `productDescription`/`productMarkdown` 真实短化 |
| 描述 | `productDescription`；可用 `productMarkdown` 做长度受限的真实改写 |
| 类别 | `productCategoryId` 加目录自身类别；按语义映射，不得虚构类别 |
| 定价模式 | `productPricingModel`；为空时先从当前官方产品页面验证 |
| 产品 Twitter/X | `productTwitterUrl` |
| GitHub 仓库/源码/仓库 URL | `productGithubRepoUrl` |
| 联系邮箱 | 仅 `productContactEmail`，除非当前官方产品页明确验证了另一个获授权地址 |
| 公司 | `productCompanyName` |
| 创始人 | `productFounderName` |
| LinkedIn | `productLinkedinUrl` |
| 创始人/你的 GitHub 资料 | `productFounderGithubUrl` |
| Logo | `productLogo` |
| 主图 | `productOgImage` |

不要在新逻辑中使用已废弃的 `productGithubUrl` 别名；它只为兼容存在，表示创始人 GitHub，不是仓库。

`productGithubRepoUrl` 可填写 GitHub Repository、Source Code、Source URL、Repository URL 或 Open Source URL；`productFounderGithubUrl` 可填写 Your GitHub、Founder GitHub 或 GitHub Profile。不要因为两个地址都使用 github.com 就互换。

仅凭仓库 URL 不能证明 Product 开源。目录询问开源、OSS 许可证或 OSS 资格时，必须从获授权的当前来源独立验证；无法验证时不要仅凭 `productGithubRepoUrl` 回答 yes。

不得从营销文案推导独立的身份/联系方式事实，尤其不要猜邮箱、创始人、公司、社交账号、上线日期、法律身份或开源状态。符合资格的路由完成预检后，如果必填字段仍缺少且无法从官方来源只读验证，使用 `blocked_missing_verified_data`；可选未知字段保持为空。

## 既有状态处理

### 已发布

不要重投。只有 Run 明确要求跟进时才验证公开列表；否则以 `skipped` 完成并保留 `published`。

### 已提交/等待审核

不要重投。只有 Run 明确要求跟进时才检查授权的跟进界面；否则跳过并保留状态。

### 等待邮箱验证

不要创建新的提交。使用 `account-authentication.md` 中的授权 Gmail 流程查找触发后的匹配验证码/链接：优先 `gws`，不可用时才使用匹配 Gmail 会话。在同一目录浏览器会话中完成原生验证并继续跟进。限定轮询窗口内没有可信匹配邮件时，保留生命周期状态并留下跟进。

## 默认账号认证

目录需要账号时，遵循 `account-authentication.md`，不要直接停止并输出 `account_strategy_required`：

1. 复用已授权会话，否则使用运行时秘密变量尝试一次登录；
2. 只有明确报告没有账号时注册一个普通免费账号；
3. 必填身份字段只使用已验证 Shipmore 字段，绝不虚构；
4. 只通过 `gws`，或在 `gws` 不可用时通过匹配 Gmail 会话获取验证邮件；OTP/magic link 只临时使用，不写入日志/证据；
5. 登录/注册导航和等待邮件期间发送 heartbeat；
6. 认证成功后继续当前 Run Item 和原始目录提交，不要标记为 blocked；
7. CAPTCHA、手机/KYC/passkey/人工审批、付费注册、邮箱匹配不明、缺少必需身份、凭据拒绝且无安全注册路径或租约丢失时停止。

### 最终提交结果不明

不要把再次点击 Submit 作为第一反应。按可用性依次检查：

1. 账号/后端提交历史；
2. 已授权邮箱回执；
3. 公开列表/搜索页面。

仍不明确时保留 `submission_outcome_unknown` 并安排跟进。

## Heartbeat 规则

任何可能修改站点的步骤前，以及任何耗时步骤后，都要发送 heartbeat。300 秒租约目标是每 60–120 秒一次。

以下情况还要发送 heartbeat：

- 登录或账号导航后；
- 改变表单状态的页面刷新/重定向后；
- 人工验证交接后；
- 素材上传后；
- 长文案准备后；
- 用户操作返回后；
- 最终提交前，如果上次 heartbeat 已不够新；
- outbound-link 注册前及每次首页验证前。

heartbeat 返回 409 时停止，不得假装仍拥有租约而执行最终提交或 Complete。

## 最终动作协议

最终动作前立即：

1. 确认当前 Directory 和提交路由；
2. 确认 Product 身份和规范 URL；
3. 检查必填字段是否真实；
4. 确认未选择未授权的 newsletter、推广、付款、法律协议或无关动作，且必需 backlink 已通过授权验证；
5. 重新检查验证/挑战有效性；
6. 必要时发送 heartbeat；
7. 执行一次最终动作；
8. 重新读取结果状态。

不得仅凭点击推断成功。

最终动作前必须完成 [../EXEC-CHECKLIST.md](../EXEC-CHECKLIST.md) 的检查并记录 `checklist PASS/FAIL`、检查时间和 `evidenceReference`。结果分类后再次执行检查；如果 `published` 没有公开列表 URL、重复检查没有证据或租约已失效，必须按事实降级或阻塞，不能继续 Complete 为成功。

## CDP 失败诊断与受控重试

CDP 超时、空响应、找不到元素或页面状态不明时，不得直接重跑。只有下一步与上次操作实质不同，且已经产生新证据，才允许一次受控重试。将以下结构化对象随 Complete 载荷写入 attempt metadata：

```json
{
  "exactError": "精确错误文本",
  "failedAction": "失败动作",
  "targetUrl": "https://example.test/submit",
  "pageState": "页面当前状态",
  "hypothesisA": "可区分的原因一",
  "hypothesisB": "可区分的原因二",
  "minimalReadOnlyCheck": "最小只读判别",
  "nextActionDifference": "下一步与上次的实质差异"
}
```

`Submit`、`Publish`、`Claim` 和 `Gmail Send` 都是零次重试。最终动作可能已经发生时，直接使用 `submission_outcome_unknown` 或对应邮件状态。

## 证据

优先使用当前 runtime/evidence 系统管理的不透明证据引用。不要保存秘密或会话材料。

有效证据包括：准确确认文案、安全可保存的服务器回执标识、公开列表 URL、显示不符合资格/仅付费的政策页、明确拒绝文案、授权用户完成人工步骤的确认。

不得仅因为表单使用过 `productContactEmail` 就把它复制到证据标签、exact-result 摘要或可分享日志。

## 稳定完成事件 ID

一个逻辑 Complete 操作必须使用稳定的 event ID。

建议格式：

```text
shipmore:<runItemId>:complete:<opaque-random-id>
```

第一次 Complete 前生成一次，并保留到收到确定响应。如果发送后 Complete 超时或连接中断，用同一个 event ID 和相同逻辑完成字段重试。

不要在不同 Run Item 或不同结果之间复用 event ID。

## Complete 结果构造

根据观察到的事实构造 Complete 载荷，不要根据期望指标构造。

示例：

### 接受审核

```json
{
  "status": "completed",
  "submissionStatus": "awaiting_approval",
  "verificationStatus": "no_verification_presented",
  "exactResult": "Submission accepted and queued for review"
}
```

### 人工挑战

```json
{
  "status": "blocked",
  "submissionStatus": "blocked_manual_verification",
  "verificationStatus": "awaiting_manual_verification",
  "exactResult": "Turnstile challenge requires user completion"
}
```

### 缺少已验证资料

```json
{
  "status": "blocked",
  "submissionStatus": "blocked_missing_verified_data",
  "exactResult": "Required founder name is not available in verified product data"
}
```

只有在仅付费、必需 backlink 验证、其他资格、既有状态和账号政策检查都完成后才使用。

### 最终动作结果不明

```json
{
  "status": "blocked",
  "submissionStatus": "submission_outcome_unknown",
  "exactResult": "Submit request timed out after final action; acceptance not confirmed",
  "followUpNote": "Check account history, mailbox, and public page before any retry"
}
```

### 表单操作前浏览器/运行时故障

```json
{
  "status": "failed",
  "submissionStatus": "not_attempted",
  "lastError": "No supported authenticated browser control surface is available"
}
```

已有更强的真实生命周期状态时，使用原状态，不要改成 `not_attempted`。

## 恢复

恢复是基础设施层面的队列修复，不代表站点动作失败。

过期租约可以恢复为 `queued`。后续 worker 必须重新读取 claim 载荷和浏览器/站点状态后再继续。不要仅因前一个 worker 租约过期就假设它没有执行任何操作。

如果前一个 worker 可能在租约丢失前执行了最终动作，将站点结果视为可能不明确；重试前检查账号、邮箱和公开页面证据。
