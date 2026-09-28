# agent-browser 运行规范

本文件定义 `submit-product-directories-shipmore` 使用 agent-browser 时的唯一运行约定。业务判断仍由 Codex 和 Shipmore 状态机完成。

## 1. Runtime 基线

部署环境固定使用 `agent-browser 0.38.1`（见 `../runtime/agent-browser.version`）。该版本当前要求 Node.js >= 24。至少需要支持：

- named session；
- `--restore`；
- snapshot / `@ref`；
- fill / type / select / check / uncheck / upload；
- get value / get url / is visible / is enabled；
- tab 管理；
- screenshot；
- console / errors；
- network requests / network request；
- wait。

生产安装：

~~~bash
npm install -g agent-browser@0.38.1
agent-browser install
~~~

Linux worker 安装浏览器系统依赖时使用：

~~~bash
agent-browser install --with-deps
~~~

启动生产 worker 前必须执行：

~~~bash
python3 scripts/agent_browser_adapter.py preflight
~~~

它会检查精确版本、`doctor --offline --quick --json`、auth seed 和 state encryption。不要在 worker 启动时自动跟随 latest。

运行时配置：

~~~text
BACKLINK_AGENT_BROWSER_AUTH_STATE=<optional secure path outside repository>
AGENT_BROWSER_ENCRYPTION_KEY=<required 64 hex chars in production>
AGENT_BROWSER_STATE_EXPIRE_DAYS=7
AGENT_BROWSER_NAMESPACE=shipmore
~~~

`BACKLINK_AGENT_BROWSER_AUTH_STATE` 指向一次性从已授权 Chrome 导出的 auth seed。它是敏感运行时文件，不属于仓库，不得被 Codex 读取、解析、打印或复制到 Shipmore evidence。

## 2. Session ID

成功 claim 后，Session ID 不再由模型临时拼接。统一调用：

~~~bash
python3 scripts/agent_browser_adapter.py session-id --run-item-id <runItemId>
~~~

实现固定为：

~~~text
shipmore-<sha256(runItemId) 前 32 个 hex>
~~~

因此 Windows/Linux/recover 都得到同一个合法 session ID。不得自行改写该算法或使用随机 session id。

## 3. 每条命令都显式指定 session

不要依赖默认 session。概念命令：

~~~bash
agent-browser --session <sessionId> --restore <command...>
~~~

例如：

~~~bash
agent-browser --session <sessionId> --restore open https://directory.example/submit
agent-browser --session <sessionId> --restore snapshot -i --json
agent-browser --session <sessionId> --restore fill @e3 "Product name"
~~~

`--restore` 用于同一 Run Item 的崩溃/daemon 重启恢复。它不是跨 Run Item 共享登录态的理由。

默认生产执行不使用：

~~~text
--cdp
--auto-connect
共享的人类 Chrome
默认 session
~~~

除非后续专门增加经过审计的运行模式。

## 4. Auth seed 与首次 Session 初始化

auth seed 用于解决“每个 Run Item 都是独立 named session，但仍需要复用已有 Google/GitHub/Gmail 登录态”的问题。

### 一次性管理员初始化

只在可信机器上执行，且不属于任何 Shipmore Run Item：

1. 创建专用 Chrome Profile，例如 `Shipmore Worker`；只登录目录提交需要的 Google、GitHub、Gmail 身份，不要复用包含 Cloudflare、Stripe、银行、公司后台等高权限站点的日常 Profile。再以 remote debugging 方式启动该专用 Chrome，由用户人工完成登录；
2. 设置 `AGENT_BROWSER_ENCRYPTION_KEY` 后，通过 agent-browser 连接该 Chrome；
3. 保存 auth state 到 `BACKLINK_AGENT_BROWSER_AUTH_STATE` 指向的仓库外路径：

~~~bash
agent-browser --auto-connect state save "$BACKLINK_AGENT_BROWSER_AUTH_STATE"
~~~

Windows 可使用等价的环境变量语法。Remote Debugging 只用于这次管理员 bootstrap；导出完成后关闭该 Chrome/调试端口。

不得把 state 文件提交到 Git，不得在 Codex 上下文中输出其内容。

### 每个 Run Item 的初始化顺序

成功 claim 后，优先使用 adapter 完成 session 初始化：

~~~bash
python3 scripts/agent_browser_adapter.py bootstrap \
  --run-item-id <runItemId> \
  --url <submitUrl> \
  [--fresh-task] \
  [--restore-check-url <glob>] \
  [--restore-check-text <text>]
~~~

只有 Shipmore 事实确认这是全新、`submissionStatus=not_attempted`、且没有 reused/recover/previous-progress 证据的 Run Item 时才传 `--fresh-task`。任何 form-in-progress、结果不明或恢复路径都不得传。adapter 还会做第二层 runtime 自校验：recovery/reused 模式、已有 restore state、已有 active session 或已有 final-action journal 任一存在时，`fresh_task` 都会直接拒绝。

adapter 的实际顺序：

1. 所有命令使用 deterministic `sessionId`、`AGENT_BROWSER_NAMESPACE=shipmore` 和 `--restore --restore-save auto`；
2. `--fresh-task` 时先检查 `state list`、`session list` 和 final-action journal，确认该 session 真正没有已有进度；通过后且配置了 auth seed 时，才先打开 `about:blank` 再执行 `state load <seed>`；
3. 随后打开 `submitUrl`，并应用调用方提供的 restore validation；
4. 非 fresh 路径绝不加载共享 seed，只恢复该 Run Item 自己的 state；
5. seed 缺失或已过期不等于任务失败；按 [account-authentication.md](account-authentication.md) 继续正常认证流程。

`--fresh-task` 是安全边界，不是“登录失败时再试一次”的开关。

不得对正在恢复的 Run Item 使用：

~~~bash
--state "$BACKLINK_AGENT_BROWSER_AUTH_STATE"
~~~

因为这可能用初始 Chrome 登录态覆盖该 Run Item 已经产生的目录 Cookie、OAuth、草稿或验证状态。

`--auto-connect` 的唯一允许用途是上述管理员 auth-seed 导出。生产 Run Item 不得连接或控制用户正在使用的 Chrome。

## 5. Session 恢复

worker recover 一个已有 Run Item 时：

1. 使用原 runItemId 重新派生同一个 sessionId；
2. 通过 `--restore` 恢复；
3. 只读检查 session info、当前 URL 和 snapshot；
4. 检查页面是否仍属于当前 Directory；
5. 检查当前 Shipmore lease 是否有效；
6. 检查既有 submissionStatus；
7. 未确认事实前不得继续 fill/click/upload 等可变动作。

如果恢复失败，不得自动新建会话后盲目重新提交；先根据账号后台、邮箱、公开页和 Shipmore 状态判断原动作是否可能已经发生。

## 6. Restore validation

`--restore-save auto` 是默认策略。对登录敏感的恢复路径，如果已有可靠的受保护路由、登录后可见文本或 JS 状态，应把它作为 `--restore-check-url`、`--restore-check-text` 或 `--restore-check-fn` 传给 adapter。验证失败时不要继续可变操作，也不要让失败状态覆盖之前的 known-good restore state。

不要为了“总能通过”而使用只验证公共域名的弱检查。无法定义可靠 restore check 时，恢复后必须按 `account-authentication.md` 使用可见身份 + 受保护功能重新确认。

## 7. Snapshot 工作流

默认：

~~~bash
agent-browser --session <sessionId> --restore snapshot -i --json
~~~

必要时可以使用完整/compact snapshot。

Codex 从 snapshot 理解：

- role；
- label；
- accessible name；
- placeholder；
- 当前文本；
- disabled/selected 状态；
- 相邻帮助文本；
- 页面上下文。

页面字段语义由 Codex 判断，不由 agent-browser 自动填充器决定。

页面导航、iframe 变化、tab 切换、dialog/modal 重建、动态表单展开后重新 snapshot。

旧 ref 只有在 runtime 明确仍存活、且页面上下文没有改变时才可继续使用；有疑问就重新 snapshot。

## 8. 安全填写

### 文本输入

标准文本写入必须使用 adapter 的 `safe_fill` / `safe-fill`。它在写入前检查 visible、enabled 和 readonly，写入后强制 `get value` 精确回读。这样可避免 readonly 字段被清空、maxlength/type 校验被 CLI 成功状态掩盖。

如果站点格式化输入导致“预期字符串”和“合法格式化值”不完全相同，不得绕过 safe_fill；应先由 Codex 明确新的可接受比较规则，再扩展 adapter。

### Select

标准 HTML select 使用 adapter `safe_select` / `safe-select`，写入后读取实际 value。

自定义 combobox：

~~~text
click combobox
→ snapshot
→ 找到 option
→ click option
→ snapshot / read-back
~~~

不要把自定义组件强行当作标准 select。

### Checkbox / Radio

仅对业务必需项操作，并使用 adapter `safe_check` / `safe-check` 做 checked read-back。对 Terms 等必要协议要确认其语义确实是完成免费目录提交所必需；newsletter、营销、付费、推广或无关授权保持未选。

### Upload

上传必须使用 adapter 的 `safe_upload` / `safe-upload`。adapter 在调用 agent-browser 前强制检查文件存在、是普通文件、大小 > 0，并转换为绝对路径；上传后还要求 file input 有非空 read-back。之后仍必须通过最新 snapshot、文件名、预览或站点原生 UI 证据确认素材正确挂载。

## 9. Tabs

列出 tabs：

~~~bash
agent-browser --session <sessionId> --restore tab
~~~

新建并标记：

~~~bash
agent-browser --session <sessionId> --restore tab new --label gmail https://mail.google.com
~~~

建议目录主页面使用 label `directory`，Gmail fallback 使用 `gmail`。

切换：

~~~bash
agent-browser --session <sessionId> --restore tab directory
agent-browser --session <sessionId> --restore tab gmail
~~~

每次切换后重新 snapshot。refs 只属于生成它们时的 active tab。

不要用位置整数假设 tab 身份。

## 10. Wait

优先等待能证明业务状态变化的条件，例如：

~~~bash
agent-browser ... wait --text "Submitted"
agent-browser ... wait --url "**/dashboard"
agent-browser ... wait @e8
~~~

只有已知页面最终会安静时才使用：

~~~bash
agent-browser ... wait --load networkidle
~~~

SSE、WebSocket、轮询页面不要依赖 networkidle。

## 11. 登录、OAuth 和邮箱验证

### 已有 session

只能根据当前 named session 的可见页面证据判断已登录。

### OAuth

仅在当前 session 已有匹配授权身份、且页面提供正常 OAuth 流程时使用。不得输入或暴露第三方账号秘密，不得绑定不同身份。

### 邮件 OTP / Magic link

触发邮件前 heartbeat，并记录触发时间。

优先：

~~~text
gws → 搜索匹配邮件 → 临时提取 OTP / verification URL
~~~

仅当 gws 不可用时：

~~~text
同一个 agent-browser named session
→ 新建 gmail tab
→ 读取匹配邮件
→ 回到 directory tab
~~~

OTP / magic link 只在内存和当前动作中临时使用，不写入日志、命令历史、截图或 Shipmore evidence。

Magic link 必须在同一个 named session 内打开，以保持原注册会话的 Cookie/Storage 连续性。

### 官方 Contact 邮件

当 `actionChannel=official_contact_email` 且 Shipmore Run 已明确授权时，可在同一 named session 的 Gmail tab 中执行发送。发送前必须完成邮件渠道的去重、收件路由、主题/正文和空 CC/BCC 检查；Gmail Send 只允许一次。发送结果不明时只读检查 Sent/All Mail/Drafts/Outbox 和当前线程，不得重发。

## 12. 诊断命令

只读诊断按需要使用：

~~~bash
agent-browser --session <sessionId> --restore get url
agent-browser --session <sessionId> --restore snapshot -i --json
agent-browser --session <sessionId> --restore screenshot <safe-output-path>
agent-browser --session <sessionId> --restore console
agent-browser --session <sessionId> --restore errors
agent-browser --session <sessionId> --restore network requests
agent-browser --session <sessionId> --restore network request <requestId>
~~~

截图不得包含邮箱、密码、OTP、magic link、token、个人敏感资料等不应进入证据的内容；敏感认证页面默认不要截图。

Network/Console 可能包含敏感 header、邮箱、请求体或带 query 的 URL。adapter 的 `diagnostics` 会在返回给 Codex 前递归脱敏敏感键、请求/响应 body、邮箱以及 URL query/fragment；调用方仍然只能提炼必要的非敏感事实进入 Shipmore evidence，不得绕过 adapter 直接持久化原始诊断 payload。

## 13. tab_gone

`tab_gone` 不等于可以自动重新打开页面继续写操作。

处理顺序：

1. 检查当前 lease；
2. 列出 tabs；
3. 判断目标 tab 是否真的丢失；
4. 如果最终动作可能已经发生，进入结果核验，不重新提交；
5. 只有能证明尚未执行最终动作、且重新打开页面不会改变外部状态时，才允许新建/恢复目录 tab；
6. 重新 snapshot 后继续。

## 14. Lease mutation gate

Managed runtime 会设置：

~~~text
SHIPMORE_MANAGED_LEASE=1
SHIPMORE_LEASE_GUARD_PATH=<runtime guard file>
~~~

`scripts/lease_keeper.py` 默认每 60 秒 heartbeat 一次，并把最新可信 lease deadline 原子写入 guard。Browser Adapter 的 open/bootstrap/fill/select/check/upload/click 都在执行前检查 guard。

Heartbeat 失败、409、guard invalid 或本地 deadline 超时时，任何可变浏览器动作都必须立即失败。LeaseKeeper 后续 heartbeat 若重新成功可恢复 guard；在 guard 恢复前只能做 Queue/日志层处理，不得修改站点。

## 15. Final action

最终动作包括：

~~~text
Submit
Publish
Claim
Gmail Send
~~~

执行前必须：

- 当前 lease 有效；
- heartbeat 足够新；
- 最新 snapshot；
- 当前按钮语义已确认；
- 关键字段已 read-back；
- EXEC-CHECKLIST before_final_action PASS。

Final Action 不允许使用普通 `click`。必须：

~~~bash
python3 scripts/agent_browser_adapter.py final-click \
  --run-item-id <runItemId> \
  --action-type submit \
  --selector @e17
~~~

可用 action type：`submit`、`publish`、`claim`、`gmail_send`。

final-click 会同步 heartbeat、检查 lease guard，并在真正 click 前用 O_EXCL 原子创建本地 durable journal。如果 journal 已存在则拒绝第二次执行。返回 JSON 中的 `completionEventId` 应作为后续 Complete 的稳定 event ID。

执行后立刻进入只读模式：

~~~text
URL
snapshot
原生页面回执
必要时 Console/Network
账号历史
授权邮箱
公开 listing
~~~

任何 timeout、连接断开、按钮消失或页面跳转都不能成为第二次 click 的理由。确认结果后使用：

~~~bash
python3 scripts/agent_browser_adapter.py final-action-resolve \
  --run-item-id <runItemId> \
  --action-type submit \
  --outcome confirmed|outcome_unknown|rejected
~~~

本地 journal 只能保证同一持久化宿主机的防重；跨主机 exactly-once 仍需要 Shipmore 服务端 final-action fencing，见 [production-hardening.md](production-hardening.md)。

## 16. Close

仅在 Shipmore complete 得到明确成功响应之后：

~~~bash
agent-browser --session <sessionId> --restore close
~~~

如果 complete HTTP 响应丢失：

- 不创建新 eventId；
- 使用同一个 eventId 幂等重试 complete；
- 浏览器 session 暂时保留，直到状态确认或任务进入人工恢复流程。

## 17. 并发

多个 Run Item 可以并发，但每个 Run Item 必须有自己的 named session。标准并发启动器为 `scripts/shipmore_worker_pool.py`，完整规则见 [parallel-execution.md](parallel-execution.md)。

不要用：

~~~text
一个共享 Chrome
+ 多个 tab
+ 多个生产 worker
~~~

作为默认并发模型。

并发大小由 worker manager 配置，默认 4、硬上限 16。出现内存压力、browser crash、lease timeout 或验证码/登录拥塞时降低并发。

## 18. State 生命周期

生产不再按纯年龄删除所有 restore state。配置：

~~~text
AGENT_BROWSER_STATE_EXPIRE_DAYS=36500
SHIPMORE_TERMINAL_STATE_RETENTION_DAYS=7
AGENT_BROWSER_NAMESPACE=shipmore
~~~

`AGENT_BROWSER_STATE_EXPIRE_DAYS` 只保留为 agent-browser 的高位 safety ceiling，避免其默认年龄清理误删长期等待人工验证或恢复中的非 terminal Run Item。

当 Shipmore `complete` 返回明确 `success=true` 时，`shipmore_queue_client.py` 会把该 Run Item 的 deterministic session 登记到本机 terminal registry，并记录 `cleanupAfterEpoch`。worker pool 启动时或单 worker 的定时维护只执行：

~~~bash
python3 scripts/agent_browser_adapter.py cleanup
~~~

该命令只对 registry 中已到保留期的 terminal item 执行：

~~~text
agent-browser --namespace shipmore state clear <sessionId>
~~~

没有 terminal 证据的 orphan/non-terminal state 宁可保留，也不自动删除。Complete 响应丢失时不会登记 cleanup；后续使用同 eventId 得到明确成功响应后才登记。

restore/auth state 必须使用 `AGENT_BROWSER_ENCRYPTION_KEY` 加密。auth seed、terminal registry 和 session state 都不得提交到仓库。