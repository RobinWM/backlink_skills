# ego-browser 实验运行规范

本文件定义 `BACKLINK_BROWSER_PROVIDER=ego-browser` 时的实验执行路径。业务判断仍由 Codex 和 Shipmore 状态机完成；ego-browser 只负责页面观察与动作执行。

## 1. 适用范围

ego-browser provider 用于对账号登录、OAuth、Cloudflare/Vercel 安全检查等 agent-browser 兼容性较差的页面做受控实验。

它不是同一个 Run Item 内的 fallback。一个 Run Item 在第一次浏览器动作前必须锁定 provider，之后直到 Complete 都不得切换。

推荐：

```text
BACKLINK_BROWSER_PROVIDER=agent-browser   # 默认生产路径
BACKLINK_BROWSER_PROVIDER=ego-browser     # 明确实验时使用
```

如果本机 ego-browser skill 不是通过运行时名称直接可用，可额外设置：

```text
BACKLINK_EGO_BROWSER_SKILL=<ego-browser SKILL.md 的本机路径>
```

worker 不得打印该本机路径到 Shipmore evidence。

## 2. Provider 锁定

claim 成功后、打开页面前执行：

```bash
python3 scripts/browser_action_guard.py select   --run-item-id <runItemId>   --provider ego-browser
```

该命令会把当前 Run Item 锁定到 ego-browser。已有 provider lock 时只能继续原 provider；不得把恢复中的 agent-browser Run Item 切到 ego-browser。

账号类阻塞如果要换 provider，应创建新的 Run / Run Item 再选择 ego-browser。

## 3. TaskSpace / Page 约束

读取已安装的 ego-browser skill 后：

1. 每个 Run Item 创建或绑定一个独立 TaskSpace；
2. 整个 Run Item 的目录页面、登录/OAuth、邮箱验证输入、表单、上传、最终动作和结果检查都保持在该 TaskSpace；
3. 不与其他 Run Item 共用 Page；
4. 页面导航、弹窗、OAuth 返回、challenge 完成后重新读取实时页面状态；
5. provider 本身不能决定 Product 字段、资格、submission status 或是否执行最终动作，这些仍由 Codex 决定。

如果 crash/recover 后无法可靠恢复原 TaskSpace/Page，不能切换到 agent-browser 继续。存在最终动作歧义时使用 `submission_outcome_unknown`。

## 4. Lease mutation gate

ego-browser 的可变操作没有 agent-browser adapter 包装，因此**每一次可变动作之前**必须执行：

```bash
python3 scripts/browser_action_guard.py mutation-check   --run-item-id <runItemId>
```

包括但不限于：

- click 会改变页面/服务器状态的控件；
- fill/type/select/check/upload；
- OAuth/登录确认；
- 发送邮箱验证码；
- 保存草稿；
- 最终 Submit/Publish/Claim/Gmail Send。

只读 snapshot、页面文本读取和诊断无需 mutation-check。

guard 失败时立即停止，不得继续操作。

## 5. 最终动作

Submit、Publish、Claim、Gmail Send 仍然只能执行一次。

执行顺序固定为：

```bash
python3 scripts/browser_action_guard.py final-begin   --run-item-id <runItemId>   --action-type submit
```

`final-begin` 会：

1. 检查当前 provider lock；
2. 检查 lease guard；
3. 同步 heartbeat；
4. 再次检查 lease；
5. 原子创建 durable final-action journal；
6. 将 journal 标记为 `attempting`；
7. 返回稳定的 `completionEventId`。

然后才允许 ego-browser 执行**一次**最终点击。

如果 ego-browser 明确返回动作已派发：

```bash
python3 scripts/browser_action_guard.py final-dispatched   --run-item-id <runItemId>   --action-type submit
```

如果最终点击 timeout、崩溃或无法判断是否已触发，不得重试点击，直接：

```bash
python3 scripts/browser_action_guard.py final-resolve   --run-item-id <runItemId>   --action-type submit   --outcome outcome_unknown
```

读取站点结果后再按证据 resolve 为：

```text
confirmed
rejected
outcome_unknown
```

Complete 优先复用 journal 中的 `completionEventId`。

## 6. 认证与真人验证

账号业务规则仍完全遵循 `account-authentication.md`。

ego-browser 可以利用其自己的受控浏览器会话来改善登录/OAuth兼容性，但不得：

- 绕过 CAPTCHA、Turnstile、Cloudflare challenge 或 Vercel Security Checkpoint；
- 伪造真人验证结果；
- 导出 Cookie、session token、OTP 或 magic link 到日志/evidence；
- 通过切 provider 绕过站点访问控制。

如果 challenge 正常呈现且需要人工完成，仍使用 `blocked_manual_verification`。

## 7. 当前定位

ego-browser provider 当前是实验路径：

- agent-browser 仍是默认 provider；
- agent-browser 的 unit / Linux real-browser E2E 仍是主 CI；
- ego-browser 依赖本机已安装 skill，因此仓库 CI 不假设其存在；
- 用于比较账号登录成功率时，应使用新的 Run Item，并记录 provider；
- 只有验证稳定后才考虑扩大默认使用范围。
