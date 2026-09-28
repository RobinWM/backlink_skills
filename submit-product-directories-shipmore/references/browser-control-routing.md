# Shipmore worker 的浏览器控制路由

## 唯一浏览器执行通道

所有目录网页、登录、表单、验证码交接、站点原生验证、截图，以及 Gmail 网页操作（验证邮件读取回退与已授权 Contact 邮件发送）必须通过 `agent-browser` 完成。

浏览器执行前先读取：

- [agent-browser-runtime.md](agent-browser-runtime.md)
- [account-authentication.md](account-authentication.md)
- [../EXEC-CHECKLIST.md](../EXEC-CHECKLIST.md)

Queue API/CLI 只负责 claim、heartbeat、outbound-link 注册、recover 和 complete，不代替可见页面交互。

同一个 Run Item 一旦开始浏览器执行，就不得切换到 browser-harness、CUA、Playwright、Chrome DevTools MCP、Browser Use、共享的人类 Chrome 或其他浏览器自动化通道。若 `agent-browser` 无法安全完成当前页面，保留真实 Shipmore 状态并交接，不得为了继续任务而换后端。

## 角色边界

Codex 是唯一业务决策 Agent。

Codex 负责：

- 理解页面字段语义；
- 将页面字段映射到 Shipmore Product 数据；
- 判断入口类型、重复项、资格条件和必填资料是否充分；
- 决定是否允许执行可变动作和最终动作；
- 根据页面、账号、邮箱和公开证据分类最终结果。

`agent-browser` 只负责：

- 导航和标签页管理；
- snapshot 和页面状态读取；
- click / fill / type / select / check / upload；
- screenshot、Console、Errors、Network 等只读诊断；
- 在 Codex 已经决定动作后执行该动作。

不得把 Product 事实、字段业务含义、提交状态或重试决策交给浏览器后端自行推断。

## Session 绑定

1. 成功 claim 后，以当前 `runItemId` 派生一个稳定、唯一且符合 agent-browser 命名规则的 named session。
2. 整个 Run Item 必须复用同一个 named session，并启用 `--restore`。
3. 不得使用 agent-browser 默认 session。
4. 正常生产 Run Item 不得使用 `--cdp`、`--auto-connect` 或当前用户正在操作的人类 Chrome；`--auto-connect` 仅允许在 Run Item 之外由管理员执行一次 auth-seed 导出。
5. 同一个 Run Item 的登录、OAuth、邮箱验证输入、表单、上传、最终动作和结果检查必须保持在同一个 named session 中。
6. 同一 session 可以使用多个 tab；tab 切换后必须重新 snapshot，绝不能复用另一个 tab 的 `@ref`。
7. worker 恢复任务时，先恢复同一个 session，再执行只读检查；未确认页面和服务器事实前不得继续可变操作。
8. 只有 Shipmore complete 已明确成功后，才关闭该 Run Item 的 browser session。complete 超时或响应丢失时先使用同一个 eventId 完成幂等重试，不要提前销毁浏览器证据。

## 能力预检

任何可变浏览器操作前确认：

- `agent-browser` CLI 可执行；
- runtime 支持 named session、`--restore`、snapshot、标准表单交互、tabs、screenshot、Console 和 Network 诊断；
- 当前 session 与 runItemId 对应；
- 若配置了 `BACKLINK_AGENT_BROWSER_AUTH_STATE`，它只作为新 session 的不透明 bootstrap 输入；已有 restore state 优先且不可被 seed 覆盖；
- 当前页面属于预期 Directory / Product；
- 当前租约仍归本 worker 所有；
- 当前 tab 没有意外切换或恢复到无关页面。

部署可以固定经过验证的 agent-browser 版本；升级后应先跑回归测试，再进入生产 worker。

## 页面读取与 refs

页面操作默认顺序：

1. 读取当前 URL；
2. 获取最新 snapshot，优先 interactive JSON；
3. Codex 根据 role、label、placeholder、accessible name、帮助文本和上下文理解页面；
4. 使用 snapshot 的 `@ref` 或语义 locator 操作；
5. 页面发生导航、iframe 切换、modal 重建、tab 切换或明显 DOM 替换后重新 snapshot；
6. 状态变化后不得假设旧 ref 仍然有效。

选择器优先级：

1. 最新 snapshot 的 `@ref`；
2. role / label / placeholder / text 等语义 locator；
3. 必要时使用稳定 CSS selector；
4. JavaScript 仅用于只读诊断或 runtime 文档明确允许且结构化交互不足的场景；
5. 坐标操作不是默认路径。

## 表单写入规则

所有重要字段必须执行“写入后回读”，不能把 CLI 的成功退出等同于表单值已经正确落地。

文本字段：

1. 确认元素可见且 enabled；
2. 使用 `fill`；
3. 使用 `get value` 回读；
4. Codex 比较预期值与实际值；
5. 不一致时不得继续最终提交，必须重新 snapshot 并诊断。

标准 select 使用 `select`。自定义 combobox/dropdown 使用：

1. click 打开；
2. 重新 snapshot；
3. 找到真实 option；
4. click 目标 option；
5. 再次读取页面确认选中状态。

checkbox/radio 必须只选择业务必需选项。不得勾选可选 newsletter、推广、合作、付费试用或无关协议。

文件上传：

- 上传前确认本地文件真实存在；
- 使用绝对路径；
- 上传后重新读取页面；
- 只有页面明确显示目标文件/预览或其他可靠 UI 证据时才认为素材已挂载；
- 不得仅凭 upload 命令返回成功判断文件有效。

## 导航与等待

可变动作后优先等待“任务真正需要的状态”：

- URL 变化；
- 指定文本出现；
- 特定控件出现/消失；
- 明确 DOM/JS 条件；
- 站点已知会静默完成时才使用 network idle。

对存在 SSE、WebSocket、轮询或 long-polling 的站点，不得把 network idle 当作通用完成条件。

## 登录与认证

认证业务顺序由 [account-authentication.md](account-authentication.md) 决定。

- 只复用当前 named session 中可由页面证据确认的授权登录状态。
- 不读取、复制、导出或打印 Cookie、localStorage、session ID、密码、OTP、magic link 或其他隐藏认证材料。
- Google/GitHub OAuth 只有在当前 session 已明确存在匹配的授权身份时才使用。
- 邮箱验证码或 magic link 的邮件读取优先通过 `gws`；仅当 `gws` 不可用时，才在同一个 named session 里新开 Gmail tab。
- 当 `actionChannel=official_contact_email` 且当前 Run 明确授权发送时，Gmail Web 发送也必须在同一 named session 中执行；Gmail Send 属于最终动作，只能执行一次。
- Gmail 网页回退建议给目录页和 Gmail 页使用固定 tab label，例如 `directory` 和 `gmail`；每次切换后重新 snapshot。
- CAPTCHA、Turnstile、手机验证、KYC、passkey、安全密钥或人工审批不得绕过，按业务规则交接或阻塞。

## 租约感知

浏览器执行从属于 Shipmore 租约。每个可变步骤前：

1. 确认当前 Run Item 仍归本 worker；
2. 剩余租约不足以覆盖下一步时先 heartbeat；
3. heartbeat 返回冲突或租约过期后立即停止所有可变网页动作；
4. 页面仍然打开不代表 worker 仍有操作权。

长时间等待 OAuth、邮箱、用户介入、上传或页面计算时，继续按 worker-loop 的频率 heartbeat。

## 诊断与受控重试

发生以下情况时先只读诊断，不得直接重跑：

- 命令 timeout；
- 空响应；
- `tab_gone`；
- 元素不存在或失效；
- fill 后 value 与预期不一致；
- 上传后没有可靠 UI 证据；
- 页面状态与预期不一致；
- 最终动作后结果不明确。

最小诊断集按需包含：

- 当前 URL；
- 最新 snapshot；
- screenshot；
- Console / Errors；
- Network requests；
- 对关键 request 的 request/response detail。

只有产生了新证据、且下一步与失败动作实质不同，才允许一次受控重试，并记录结构化 `retryDiagnostic`。普通读取可以重复；会改变外部状态的动作必须遵守更严格规则。

## 最终动作安全

Submit、Publish、Claim 和 Gmail Send 都属于最终动作。

最终动作前：

1. heartbeat；
2. 获取最新 snapshot；
3. 确认按钮/控件确实对应当前 Product 和 Directory 的预期最终动作；
4. 所有关键字段已经 read-back 验证；
5. 执行 EXEC-CHECKLIST 的 before-final-action；
6. 最终动作只执行一次。

最终动作后：

1. 不再次点击；
2. 读取当前 URL 和最新 snapshot；
3. 获取站点原生正向/负向回执；
4. 必要时检查 Console/Network、账号后台、授权邮箱或公开 listing；
5. 仍无法判断时使用 `submission_outcome_unknown` 或邮件专用 unknown 状态。

按钮禁用、表单清空、普通跳转、感谢页或 CLI timeout 都不能单独证明提交成功。

## Product 数据和字段语义

以 Shipmore claim 载荷为主要已验证输入。

Codex 可以：

- 根据页面字段语义选择正确的 Shipmore 字段；
- 对 productDescription / productMarkdown 做真实的长度调整；
- 按目录语义映射类别。

Codex 不得：

- 从营销文案猜邮箱、创始人、公司、地址、价格、社交账号、法律身份或开源状态；
- 混淆 productGithubRepoUrl 与 productFounderGithubUrl；
- 用未知可选字段阻塞整个任务；
- 为满足必填项捏造值。

## 并发规则

允许多个 Run Item 并行，但必须：

- 一个 Run Item 对应一个独立 named session；
- 每个 worker 有独立 heartbeat 循环；
- 不共享默认 session；
- 不让多个 worker 通过同一个共享 CDP Chrome 承载生产提交；
- 并发上限由 worker manager 根据 CPU、内存、页面复杂度和 lease 稳定性配置，不在 Skill 内硬编码。

## 证据和隐私

只持久化 Shipmore 契约允许的证据。

不得把以下内容写入 exactResult、lastError、evidenceReference、followUpNote 或 retryDiagnostic：

- 密码；
- OTP；
- magic link；
- Cookie / session ID；
- token URL；
- 原始邮箱和电话；
- 本机浏览器 profile 路径；
- 进程参数；
- agent-browser 的敏感 state 文件内容。

本地运行时诊断可以临时存在，但必须避免把秘密复制到持久化字段。