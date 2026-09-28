# agent-browser 运行规范

本文件定义 `submit-product-directories-shipmore` 使用 agent-browser 时的唯一运行约定。业务判断仍由 Codex 和 Shipmore 状态机完成。

## 1. Runtime 基线

部署环境必须提供兼容的 `agent-browser` CLI。当前迁移基线按 0.38.x 能力设计，至少需要支持：

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

生产环境应固定并测试具体版本，不要在 worker 启动时自动跟随 latest。

## 2. Session ID

成功 claim 后：

~~~text
runItemId = claim.data.id
sessionId = stable_agent_browser_id(runItemId)
~~~

sessionId 必须：

- 稳定；
- 一个 Run Item 唯一一个；
- 只包含 agent-browser 接受的字母、数字、连字符和下划线；
- worker recover 后能够重新计算得到完全相同的值。

推荐逻辑概念：

~~~text
shipmore-<safe-runItemId>
~~~

如果 runItemId 含不支持字符，使用确定性的安全编码/哈希后缀，不得使用随机 session id。

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

## 4. Session 恢复

worker recover 一个已有 Run Item 时：

1. 使用原 runItemId 重新派生同一个 sessionId；
2. 通过 `--restore` 恢复；
3. 只读检查 session info、当前 URL 和 snapshot；
4. 检查页面是否仍属于当前 Directory；
5. 检查当前 Shipmore lease 是否有效；
6. 检查既有 submissionStatus；
7. 未确认事实前不得继续 fill/click/upload 等可变动作。

如果恢复失败，不得自动新建会话后盲目重新提交；先根据账号后台、邮箱、公开页和 Shipmore 状态判断原动作是否可能已经发生。

## 5. Snapshot 工作流

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

## 6. 安全填写

### 文本输入

概念流程：

~~~bash
agent-browser ... is visible @e3
agent-browser ... is enabled @e3
agent-browser ... fill @e3 "<value>"
agent-browser ... get value @e3
~~~

Codex 必须比较回读值。出现 maxlength 截断、格式化、readonly、disabled、校验器重写等情况时，不得把 fill 的成功退出当作填写成功。

### Select

标准 HTML select：

~~~bash
agent-browser ... select @e5 "Visible Label"
~~~

然后重新读取页面确认实际选择。

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

仅对业务必需项操作。对 Terms 等必要协议要确认其语义确实是完成免费目录提交所必需；newsletter、营销、付费、推广或无关授权保持未选。

### Upload

上传前先确认文件：

- 存在；
- 类型/大小符合页面说明；
- 使用绝对路径。

上传后必须通过最新 snapshot、文件名、预览或站点原生 UI 证据确认目标素材已经挂载。上传命令本身不是最终证据。

## 7. Tabs

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

## 8. Wait

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

## 9. 登录、OAuth 和邮箱验证

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

## 10. 诊断命令

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

Network/Console 可能包含 token、邮箱、请求体或其他秘密。只提炼必要的非敏感事实进入 Shipmore evidence，绝不原样持久化完整敏感 payload。

## 11. tab_gone

`tab_gone` 不等于可以自动重新打开页面继续写操作。

处理顺序：

1. 检查当前 lease；
2. 列出 tabs；
3. 判断目标 tab 是否真的丢失；
4. 如果最终动作可能已经发生，进入结果核验，不重新提交；
5. 只有能证明尚未执行最终动作、且重新打开页面不会改变外部状态时，才允许新建/恢复目录 tab；
6. 重新 snapshot 后继续。

## 12. Final action

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

只执行一次。

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

任何 timeout、连接断开、按钮消失或页面跳转都不能成为第二次 click 的理由。

## 13. Close

仅在 Shipmore complete 得到明确成功响应之后：

~~~bash
agent-browser --session <sessionId> --restore close
~~~

如果 complete HTTP 响应丢失：

- 不创建新 eventId；
- 使用同一个 eventId 幂等重试 complete；
- 浏览器 session 暂时保留，直到状态确认或任务进入人工恢复流程。

## 14. 并发

多个 Run Item 可以并发，但每个 Run Item 必须有自己的 named session。

不要用：

~~~text
一个共享 Chrome
+ 多个 tab
+ 多个生产 worker
~~~

作为默认并发模型。

并发大小由 worker manager 配置。出现内存压力、浏览器 crash、lease timeout 或验证码/登录拥塞时降低并发。