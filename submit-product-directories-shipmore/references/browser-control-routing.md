# Shipmore worker 的浏览器控制路由

## 唯一浏览器执行通道

所有网页、登录、表单、验证码交接、站点原生验证、截图和 Gmail 操作必须通过指定的 `ego-browser` skill 完成：

```text
C:\Program Files\Citro Labs\ego lite\Application\0.5.2.12\ego-skills\ego-browser\SKILL.md
```

先读取该 skill，再使用同一个 ego-browser TaskSpace 和 Page 完成当前站点流程。不得使用 browser-harness、agent-browser、CUA、Playwright、直接启动 Chrome 或其他浏览器自动化通道。Queue API/CLI 只负责 claim、heartbeat、outbound-link 注册、recover 和 complete。

根据 ego-browser skill 的运行时能力执行浏览器操作，不要把浏览器、操作系统、可执行路径、扩展、自动化库、快捷键或显示尺寸写死。

Shipmore 负责持久化提交状态。浏览器/后端诊断属于运行时信息，只有通过不透明 evidence reference 或明确支持的 Shipmore 字段保存。不要为了记录浏览器状态重新创建旧版 Markdown campaign record。

## 能力预检

在任何可变浏览器操作前确认：

- 规范化主机平台：`windows`、`macos`、`linux` 或 `other`；
- UI 环境：desktop、remote desktop、headless 或 unknown；
- 用户指定的浏览器/应用约束；
- 是否已经存在已授权的认证浏览器/应用绑定；
- 可用的 connector、API、CLI、浏览器 runtime、连接扩展和桌面控制能力；
- 每个候选后端是否支持当前平台和所需交互范围。

## 路由顺序

1. 读取并遵守 ego-browser skill；所有浏览器动作固定路由到 ego-browser。
2. 使用同一个 TaskSpace 和 Page 完成登录、验证、表单、Gmail 和结果检查；不要为同一站点创建第二个 TaskSpace。
3. Queue API/CLI 只执行后端任务操作，不代替可见页面交互。
4. ego-browser 无法安全处理目标页面时，保留 Shipmore 状态并交接，不得切换到其他浏览器自动化工具。

具体工具的选择器、确认规则、键盘行为、截图处理和支持平台，以当前 runtime/Skill 文档为准。

## 会话规则

- 创建重复账号前，优先复用已授权现有会话。
- 站点要求连续性时，登录、验证、填写和最终结果检查必须在同一个 ego-browser TaskSpace/Page 会话完成。
- 登录状态以当前 ego-browser 页面实时证据为准：检查账号菜单、可见用户标识、Dashboard/Logout 入口，以及受保护提交页面是否可访问。claim 快照中的历史阻塞文案、另一个浏览器/TaskSpace 的登录状态、公开页面和 URL 本身都不是登录证明。
- 只有当前页面显示的账号身份与 Shipmore 有效提交身份匹配，或该账号已获得当前任务授权时，才可复用会话。无法确认身份时停止在登录墙前，不要读取或复制 Cookie、localStorage、session ID 或隐藏认证材料。
- 浏览器绑定和标签页绑定是分开的；可行时从现有浏览器绑定恢复失效标签页，不要重建整个 runtime。
- 绝不要检查 Cookie、本地存储、已保存密码、profile store、恢复码、原始 session ID、magic link 或隐藏认证材料。
- 不要把浏览器/profile 的不透明标识复制到另一台机器当作可移植凭据。

## 优先使用结构化交互

当前浏览器 runtime 支持时：

1. 读取最新页面/DOM/可访问性状态；
2. 优先使用语义化、结构化控件；
3. 导航、刷新、弹窗、用户介入或意外结果后重新获取控件；
4. 只有 runtime 文档允许且结构化控制不足时，才使用键盘或坐标回退。

状态变化后绝不能复用旧 DOM handle、可访问性索引、菜单项或坐标。

## 桌面控制回退

只有必要且明确支持时才使用桌面 UI 控制。每次回退操作前：

- 确认焦点应用/窗口；
- 通过非敏感可见身份确认目标 profile/workspace/session；
- 读取最新 UI 状态；
- 坐标操作前重新确认布局、显示缩放和缩放比例。

不要假设 macOS、Windows、Linux 快捷键可以互换。除非用户明确要求且当前 runtime 政策允许，不要引入 AppleScript、PowerShell UI 自动化、xdotool、独立自动化服务器或其他 UI 技术。

## 身份验证和挑战

- 绝不绕过、外包、削弱或规避 CAPTCHA、Turnstile、邮箱验证、浏览器安全警告或访问控制。
- 本 Shipmore worker 可按 `account-authentication.md` 使用现有 Google/GitHub OAuth 会话、原生邮箱验证、普通邮箱/密码登录和一次必要的免费注册。使用 claim 载荷中的有效账号邮箱；密码只能从运行时秘密文件读取。
- Google 托管邮箱优先通过已授权 `gws` 完成普通验证；仅当 `gws` 不可用时使用匹配 Gmail 会话。这不是绕过。验证码/链接只能临时使用，并在同一目录浏览器会话中完成。
- 认证成功后继续原始目录任务，不要仅因需要账号就停止。
- 需要用户操作时，租约有效则交接前 heartbeat，并如实保留 Shipmore 状态。
- 用户操作后重新读取页面并检查挑战有效性。交接期间租约过期时，不得继续以原所有者身份操作；按 Queue 协议重新 claim/recover，并在重试前检查站点状态。

## 租约感知的浏览器操作

浏览器执行从属于 Shipmore 租约。每个可变步骤前：

1. 确认当前 Run Item 仍归本 worker 所有；
2. 剩余租约不足以覆盖下一步时先 heartbeat；
3. 收到租约冲突/过期响应后立即停止。

页面仍然打开不代表租约过期后仍有执行权。

## 最终动作安全

以下任一情况都不能单独证明提交成功：点击 Submit、按钮禁用、表单清空、导航、普通感谢页或传输超时/错误。

最终动作后重新读取页面/状态，只报告证据支持的结果。若可能已到达服务器但无法确定：

1. 不要再次点击 Submit；
2. 检查已授权账号/后端历史；
3. 检查已授权邮箱；
4. 适用时检查公开列表/页面；
5. 仍不明确时以 `submission_outcome_unknown` 完成 Shipmore item 并安排跟进。

## Product 数据规则

以 Shipmore claim 载荷返回的 Product 数据作为主要已验证输入。可以按字段长度/类别真实改写 `productDescription` 或 `productMarkdown`，但不得虚构：创始人/公司身份、地址、上线日期、价格或套餐、联系方式、所有权/法律事实，或返回数据及独立验证来源未支持的产品能力。

可选未知字段保持为空；必填未知字段应使用 `blocked_missing_verified_data`。

## 协议、付款、互链和推广

不得自动：支付目录费用、购买链接/排名套餐、直接修改 Product 网站添加互链、修改 DNS/网站内容、接受可选 newsletter/推广、发布无关文章/帖子、请求 dofollow 或精确匹配商业锚文本。

唯一窄范围例外是 Shipmore 的必需 backlink 流程：调用 `POST /api/outbound-links` 并验证 Product 首页，但绝不直接编辑 Product 代码/内容。链接可以出现在 SSR HTML 或首页最终 DOM 中；必须按 `worker-loop.md` 使用精确的 hostname/path 匹配、租约和超时规则，不得绕过 CAPTCHA/WAF。

## 证据和诊断

只持久化 Shipmore API 契约支持的信息：准确结果文本、不透明证据引用、公开列表 URL、后端/邮箱/公开页检查时间、跟进时间/备注，以及规范提交/验证状态。

运行时本地诊断可以临时包含非敏感浏览器/后端别名，但不要为了保存它创建第二个持久队列/状态记录。

绝不能在 Shipmore evidence/result 字段保存密码、token、OTP、Cookie、原始邮箱、电话、认证 URL、本机应用路径、进程参数或 session secret。配置的账号邮箱可作为浏览器表单输入，但不得复制到证据或 exact-result 文本。
