# Shipmore 状态映射

本文件把浏览器观察到的结果映射为 Shipmore 的规范提交状态和本次 Run Item 的终止结果。

## 规范提交状态

```text
not_attempted
form_in_progress
draft_saved
submitted
submission_outcome_unknown
awaiting_approval
awaiting_email_verification
published
blocked_manual_verification
blocked_missing_verified_data
blocked_account_or_email_policy
unavailable
paid_only
ineligible
duplicate_no_action
terminated_by_user
rejected
```

## 验证状态

```text
not_checked
automatic_verification_passed
awaiting_manual_verification
manual_verification_completed
verification_unavailable_before_form
verification_expired_reset
no_verification_presented
deferred_by_user
```

## Run Item 状态

```text
completed
blocked
failed
skipped
```

Run Item 状态描述本次执行尝试的结果；Submission 状态描述 Product × Directory 的生命周期。两者不能混用。

## 映射规则

| 浏览器/站点结果 | Run Item | Submission 状态 | 说明 |
| --- | --- | --- | --- |
| 表单接受但尚未发布 | `completed` | `submitted` | 必须有具体接受证据，不能只凭点击 |
| 站点显示排队/等待审核 | `completed` | `awaiting_approval` | 记录准确的排队/审核文案 |
| 站点要求提交后邮箱验证 | `blocked` | `awaiting_email_verification` | 设置对应验证状态和跟进 |
| 已验证公开列表 | `completed` | `published` | 必须提供 `publicListingUrl` |
| 已执行最终提交但无法确定结果 | `blocked` | `submission_outcome_unknown` | 不得盲目重投，安排检查/跟进 |
| CAPTCHA/Turnstile/人工挑战阻塞 | `blocked` | `blocked_manual_verification` | 通常验证状态为 `awaiting_manual_verification` |
| 缺少必需且真实的 Product 字段 | `blocked` | `blocked_missing_verified_data` | 不能虚构资料 |
| 账号/邮箱政策阻止授权执行 | `blocked` | `blocked_account_or_email_policy` | 保留准确政策/结果 |
| 路由或站点不可用 | `completed` | `unavailable` | 尽可能保留结构化证据 |
| 只有未获授权的付费入口 | `completed` | `paid_only` | 不得付款 |
| 必需 backlink/badge 已注册且 Product 首页验证通过 | 继续当前任务 | 保留当前生命周期 | 不要提前 Complete，继续原始目录提交 |
| 6 次首页检查仍找不到 backlink | `blocked` | `ineligible` | exact result/error 必须包含 `backlink verification timeout` |
| 除已授权 outbound-link 流程外还要求修改站点 | `completed` | `ineligible` | 不执行该修改 |
| Product 不符合目录资格 | `completed` | `ineligible` | 记录原因 |
| 目录确认已有列表且无需操作 | `completed` 或 `skipped` | `duplicate_no_action` | 只有实际确认重复时使用 |
| 用户明确停止该任务 | `skipped` | `terminated_by_user` | 没有新 Run/action 不得继续 |
| 目录明确拒绝提交 | `completed` | `rejected` | 保留准确拒绝原因 |
| 有意义表单操作前发生浏览器/后端故障 | `failed` | 保留当前真实状态，通常为 `not_attempted` | 必须提供 `lastError` |
| 已填写字段但最终动作前发生故障 | `failed` | `form_in_progress` 或真实保存后的 `draft_saved` | 不得标记为 submitted |

## 内容编辑器 no-action

以下入口只记录观察结果，不得填写、预填、保存草稿、提交、发布或自动交给人工继续写作：

```text
short note — no action
long post — no action
unknown — no action
```

只有内容编辑器的站点使用：

```text
Run Item status  = completed
submissionStatus = ineligible
exactResult      = content surface classified as no-action
```

页面显示 `Post`、`Publish` 或 `Submit` 不会改变该规则。不要将内容编辑器误分类为 `unavailable` 或 `submission_failed`。

## 站内去重证据

执行表单、Claim 或任何最终动作前，必须在现有 `evidenceReference` 中保存站内去重证据。最低内容包括：

```text
规范 URL查询
裸域名查询
品牌/产品名查询
标题变体查询
候选数量
候选实际出站 URL核验结果
检查时间
```

命中规范 URL 或规范域名时，使用 `duplicate_no_action`，停止该站，不得继续登录、填写或提交。只有当前批次明确授权时，才允许使用未完成检查的直接尝试结果；这种结果最多允许一次最终提交尝试，并且必须在 evidence 中记录缺口和授权引用。

## 预检优先级

多个条件同时存在时，按以下顺序使用第一个决定性条件：

```text
unavailable
→ paid_only
→ 必需 backlink 注册与验证（成功后继续）
→ 其他不符合资格
→ 重复项或既有生命周期保护
→ blocked_account_or_email_policy
→ blocked_missing_verified_data
→ blocked_manual_verification
→ 表单执行
```

## 必需 backlink 结果

注册 API 成功不等于验证成功。只有 Product 首页 HTML 或最终 DOM 中的 `<a href>` 解析后 hostname/path 与目录 URL 完全匹配，才允许继续表单。允许 scheme、开头 `www.` 和结尾斜杠不同；不允许子字符串、伪后缀域名或不同路径。

轮询期间每次检查前都发送 heartbeat。若收到 409 或证明租约已过期/归属他人，立即停止，不得继续提交或 Complete。

6 次超时的标准结果：

```text
Run Item status     = blocked
submissionStatus    = ineligible
exactResult         = backlink verification timeout: directory link not found on product homepage after 6 attempts
```

这只表示本次执行被阻塞，不代表注册 API 失败或目录拒绝 Product。如果注册或运行时在验证前失败，应保留最强的既有生命周期状态，并根据事实使用 `blocked` 或 `failed`。

## 跳过时保留既有生命周期

当前 Run Item 没有新动作时，`status=skipped` 不代表 `submissionStatus=not_attempted`。例如，既有 `published` 或 `awaiting_approval` 状态都必须原样保留。

## submitted 不等于 published

只有验证公开列表 URL 后才能使用 `published`。表单接受、审核队列、邮箱回执、后台记录或待审核状态都不代表发布。

## 最终动作结果不明

最终动作可能已到达站点、worker 无法证明成功或失败、重试可能造成重复申请时，使用 `submission_outcome_unknown`。设置 Run Item 为 `blocked`，保留准确结果/错误，记录后端、邮箱和公开页检查，并安排跟进。不要把结果不明改成 `failed` 来美化队列。

## 手动验证

通常映射为：

```text
Run Item status     = blocked
submissionStatus    = blocked_manual_verification
verificationStatus  = awaiting_manual_verification
```

用户完成正常挑战后，后续授权执行可以继续；提交前必须重新检查挑战有效期。

## 缺少 Product 资料

使用：

```text
Run Item status     = blocked
submissionStatus    = blocked_missing_verified_data
```

只有在资格、政策、backlink、既有状态和账号检查完成后才能使用。可选未知字段留空，不要因此阻塞。

## 运行时故障

浏览器崩溃、不支持的控制后端、临时网络故障或工具异常不等于目录拒绝。Run Item 使用 `failed`，Submission 保留最接近事实的状态，并始终发送 `lastError`。已知 `published`、`awaiting_approval` 等强状态不能因本次 worker 失败被覆盖为 `not_attempted`。
