# Shipmore 借鉴 merged 能力的实施方案

## 1. 目标

Shipmore 继续负责 Run、Run Item、租约、队列顺序、恢复和提交生命周期。浏览器 worker 借鉴 `submit-producti-directories-merged` 在入口识别、站内去重、内容面分类、官方联系邮件、最终动作检查和证据记录方面的规则。

本方案不把 merged 的本地 Markdown 队列搬进 Shipmore，也不复制一套与 Shipmore 并行的提交状态源。

目标是让 Shipmore worker 在执行前更早发现错误入口，在最终动作前降低重复提交风险，并在 Contact 邮件和结果不明场景下保留可恢复证据。

当前进度：阶段一至七已实施。阶段一至三接入浏览器规则、检查单和去重证据；阶段四、五已在 Shipmore 后端增加内容面字段、no-action 校验、官方 Contact 邮件渠道字段、邮件专用状态和 Queue API/Server Action 传递；阶段六增加结构化 CDP 重试诊断；阶段七增加共享字段敏感信息审计和回归测试。

登录状态判断补充：以当前 ego-browser TaskSpace/Page 的实时可见身份和受保护页面访问结果为准，不使用 claim 历史阻塞文案或其他浏览器会话推断当前登录状态。

## 2. 现有能力与缺口

### Shipmore 已有能力

- Queue API 的 `claim`、`heartbeat`、`complete`、`recover`；
- Run Item 租约和 worker 所有权；
- Product × Directory 提交生命周期；
- Product 字段快照和有效提交身份；
- mandatory backlink 注册与 Product 首页验证；
- 账号认证、邮箱验证和 `submission_outcome_unknown` 规则；
- 稳定 `eventId` 的 Complete 幂等机制。

### merged 可借鉴的能力

- 站内固定查询集和实际出站 URL 去重；
- 短贴、长文和未知内容编辑器的 no-action 分类；
- 官方 Contact 邮件作为独立执行渠道；
- 最终动作前后检查单；
- ego-browser 页面失败的假设、最小只读诊断和受控重试；
- Gmail 发送结果与目录收录结果分离；
- 更细的共享记录隐私检查。

### 不直接移植的内容

- merged 的本地队列、队列游标和本地规范提交记录；
- 用 Markdown 文件替代 Shipmore 状态；
- 复制 Shipmore 的 claim/lease/complete API；
- 让 worker 直接访问 Shipmore 数据库；
- 用 Contact 邮件替代目录表单的生命周期状态。

## 3. 目标执行模型

每个 Run Item 仍由 Shipmore 管理。worker 在 claim 后执行以下顺序：

```text
claim
→ 检查既有生命周期
→ 站点可达性
→ 仅付费/强制互链/条款预检
→ mandatory backlink 注册与验证
→ 站内实际去重
→ 内容面分类
→ 账号认证
→ 缺少已验证资料检查
→ CAPTCHA/人工验证
→ 表单或官方 Contact 邮件执行
→ 结果捕获
→ 证据核验
→ 使用稳定 eventId complete
```

如果某个更早阶段已经给出终止性结果，不能继续执行后面的可变动作。例如内容编辑器已经判定为 `short note — no action`，不能继续预填或保存草稿。

## 4. 分阶段实施

### 阶段一：浏览器侧规则，不改后端状态

先在 worker 文档和执行代码中加入以下规则：

1. 首页、导航、页脚、站内搜索和真实按钮优先发现入口；保存的深链只作线索。
2. 目录表单、产品资料页、claim listing、内容编辑器和 Contact 邮件分开分类。
3. 站内重复检查必须覆盖规范 URL、裸域名、品牌/产品名和标题变体。
4. 候选结果必须打开并核对实际出站 URL，不能只凭标题判断重复。
5. 内容编辑器分类为 `short note — no action`、`long post — no action` 或 `unknown — no action` 时，立即停止该站的内容动作。

这一阶段只使用现有 Shipmore 的 `exactResult`、`evidenceReference` 和状态字段，不引入本地队列。

### 阶段二：增加统一的执行检查单

实施状态：已完成文档和 worker 流程接入，使用现有 `exactResult`、`evidenceReference` 和稳定 `eventId`，未新增后端字段。

新增或扩展 Shipmore worker 的执行检查单，在最终动作前和结果判断后各运行一次。

#### 最终动作前

- Run Item 仍归当前 worker，租约未过期；
- Product、Directory 和提交路由匹配；
- 既有生命周期不禁止重投；
- 站内去重已完成并有证据；
- 表单字段来自已验证 Product 数据；
- 没有未经授权的付费、推广、互链或法律承诺；
- mandatory backlink 已完成注册并通过首页验证；
- 验证挑战仍有效；
- 最终动作只允许执行一次。

#### 结果判断后

- 页面状态或路由是否变化；
- 是否出现与当前动作对应的原生正向回执；
- 是否存在后端、邮箱或公开页面的独立确认；
- `submitted` 是否被错误当成 `published`；
- 结果不明时是否阻止重试；
- Complete 使用的 `eventId` 是否稳定。

### 阶段三：扩展站内去重证据

实施状态：已完成证据格式和结果约定，使用现有 `evidenceReference` 保存详细证据，未新增后端字段。

建议在 Shipmore evidence store 中保存结构化但不含敏感信息的去重证据：

```json
{
  "type": "site_duplicate_check",
  "queries": [
    "canonical URL",
    "bare domain",
    "brand or product name",
    "title variants"
  ],
  "candidateCount": 0,
  "candidateEvidence": "ev-opaque-123",
  "result": "cleared",
  "checkedAt": "2026-09-24T10:00:00+08:00"
}
```

推荐结果值：

```text
cleared
duplicate_confirmed
not_available_user_authorized_direct_attempt
inconclusive_user_authorized_direct_attempt
```

`not_available_user_authorized_direct_attempt` 和 `inconclusive_user_authorized_direct_attempt` 只允许当前批次明确授权，并且最多允许一次最终提交尝试。两者都必须记录具体缺口和已完成的检查。

### 阶段四：增加内容面 no-action 分类

实施状态：已完成后端字段和校验。`product_directory.content_surface` 默认 `not_applicable`；no-action 内容面只能以 `ineligible` 完成，不能进入表单或发布流程。

在 Directory 观察结果或 evidence 中增加内容面分类：

```text
directory_listing
product_profile
claim_listing
short_note
long_post
unknown_content_editor
official_contact_email
```

以下分类不得进入产品内容填写或发布：

```text
short note — no action
long post — no action
unknown — no action
```

建议第一版映射为：

```text
Run Item status: completed
submissionStatus: ineligible
exactResult: content surface classified as no-action
```

如果业务需要统计这类入口，再增加单独的 `contentSurfaceOutcome` 字段；不要把它伪装成 `unavailable` 或 `submission_failed`。

### 阶段五：增加官方 Contact 邮件渠道

实施状态：已完成第一版后端契约。已增加 `actionChannel`、官方联系人证据、Gmail 发送次数/回执和两个邮件专用状态；发送动作仍由授权 worker 执行，Shipmore 只保存状态和受控证据引用。

这是唯一需要明显扩展 Shipmore 状态和 API 契约的阶段。

#### 建议字段

```text
actionChannel: web_form | official_contact_email
recipientContactAlias
contactSourceEvidence
mailboxPreSendCheck
mailboxPreSendEvidence
emailSendAttempts
gmailSendReceipt
```

#### 建议邮件状态

```text
email_sent_awaiting_reply
email_send_outcome_unknown
```

#### 执行流程

1. 确认目标站官方 Contact、投稿、资源推荐或合作页面；
2. 确认当前 Run 授权允许发送官方联系邮件；
3. 在 Shipmore 既有记录及 Gmail Sent、Drafts、All Mail 中去重；
4. 确认发件别名、收件路由、主题、正文和空 CC/BCC；
5. Gmail Send 只执行一次；
6. 有明确 Gmail 发送回执时记录 `email_sent_awaiting_reply`；
7. 回执不明时只读检查撰写页/线程、Sent/All Mail、Drafts/Outbox 两到三轮；
8. 仍不明确时记录 `email_send_outcome_unknown`，保留跟进，不得重发；
9. 邮件发送不代表送达、回复、收录、外链或发布。

#### 状态约束

- `web_form` 不得使用邮件专用状态；
- `official_contact_email` 不得使用 `published` 或表单 `submitted` 表示邮件已发送；
- 同一 Product、目标域名和官方联系路由最多发送一封初始邮件；
- 邮件路线的 `Content surface` 必须为 `not applicable`；
- 不得请求 dofollow、排名承诺、强制互链、Guest Post 或内容发布。

### 阶段六：引入 ego-browser 页面失败诊断协议

实施状态：已完成。Queue complete 和 Server Action 接受结构化 `retryDiagnostic`，写入 Complete attempt metadata；所有页面操作统一使用 ego-browser，最终动作保持零次重试。

对于超时、空响应、找不到元素和页面状态不明，不能直接重跑。每次受控重试前记录：

```text
exactError
failedAction
targetUrl
pageState
hypothesisA
hypothesisB
minimalReadOnlyCheck
nextActionDifference
```

只有产生新证据，且下一步与上次操作实质不同，才允许一次受控重试。以下最终动作始终零次重试：

```text
Submit
Publish
Gmail Send
```

如果最终动作可能已经发生，直接使用 `submission_outcome_unknown` 或邮件专用结果，不得为了“确认成功”再次点击。

### 阶段七：增强隐私审计和测试

实施状态：已完成第一版。Shipmore 拒绝在 `lastError`、`exactResult`、`evidenceReference`、`followUpNote` 和 retry diagnostic 中写入原始邮箱、秘密、会话信息或本机路径，并补充类型、Queue 和 worker 回归测试。

审计必须拒绝以下内容进入 Shipmore evidence、exactResult 或 follow-up note：

- 原始邮箱地址；
- 电话号码；
- 密码、OTP、magic link；
- Cookie、session ID、token URL；
- 本机路径、进程参数和浏览器秘密。

需要新增的测试：

1. `web_form` 与邮件状态互斥；
2. 同一 Product/目标域名/Contact 路由不能发送第二封邮件；
3. Gmail 结果不明时不能重发；
4. `short_note`、`long_post` 和未知内容编辑器不进入表单执行；
5. URL 变体和实际出站 URL重复时被识别；
6. 租约失效后不能 Complete；
7. mandatory backlink 只能通过精确 hostname/path 匹配；
8. `published` 必须有公开列表 URL；
9. 跳过既有 `published` 或 `awaiting_approval` 时不能重置为 `not_attempted`；
10. Complete 超时重试必须复用同一个 `eventId`。

## 5. API 和数据迁移建议

### 不兼容变更前的兼容策略

1. 先让 claim/complete 接受可选的新字段；
2. 老的 web form Run Item 继续使用原状态；
3. worker 只在 `actionChannel=official_contact_email` 时启用邮件字段和邮件状态；
4. API 和数据库同时支持旧的下划线状态与新字段，不在 worker 内静默改写历史状态；
5. 完成一轮历史数据迁移和审计后，再把邮件字段设为必填。

### 建议的 Complete 载荷扩展

```json
{
  "eventId": "shipmore:<runItemId>:complete:<opaque-id>",
  "runItemId": "<run-item-id>",
  "workerId": "<worker-id>",
  "status": "completed",
  "submissionStatus": "email_sent_awaiting_reply",
  "actionChannel": "official_contact_email",
  "verificationStatus": "no_verification_presented",
  "exactResult": "Gmail send receipt confirmed; awaiting reply",
  "evidenceReference": "ev-opaque-123"
}
```

原始收件邮箱、邮件正文和 Gmail 页面内容应留在受控证据系统，不能写入可分享的 Complete 载荷。

## 6. 验收标准

实施完成后，至少应满足：

- worker 不再把内容编辑器误当成目录表单；
- 站内已有列表不会仅因后端没有历史记录而重复提交；
- 结果不明时不会再次点击最终动作；
- 租约丢失后不会继续修改站点或 Complete；
- `submitted`、`published`、邮件已发送和邮件结果不明可以区分；
- 每个最终动作都有可追溯的检查单和证据引用；
- Product 身份字段不会从无关文案中猜测；
- mandatory backlink 仍由 Shipmore endpoint 和首页精确匹配流程管理；
- 旧的 web form Run Item 和历史提交状态保持兼容；
- 测试覆盖状态互斥、去重、隐私、租约和 Complete 幂等。

## 7. 推荐落地顺序

```text
1. 浏览器入口/内容面分类
2. 站内去重证据
3. 最终动作检查单
4. ego-browser 页面失败诊断
5. 邮件字段和状态 API
6. 官方 Contact 邮件执行
7. 隐私审计与回归测试
```

先完成前四项可以降低现有目录提交风险；邮件渠道需要数据库和 API 变更，应单独设计、灰度和回滚。

## 8. 风险与回滚

- **状态污染**：新邮件状态不应覆盖既有表单生命周期；通过 `actionChannel` 和状态互斥校验防止。
- **重复联系**：通过 Gmail/Shipmore 双重去重和单邮件上限防止。
- **入口误判**：通过内容面分类和 no-action 终止规则防止。
- **租约失效后误操作**：所有可变步骤前 heartbeat，409 后立即停止。
- **历史数据不兼容**：新字段先可选，先兼容旧 web form 记录，再逐步强制。
- **回滚**：邮件功能应可通过 feature flag 关闭；关闭后保留历史邮件状态，只停止创建新的邮件任务，不将其改写成表单状态。
