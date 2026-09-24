# 目录账号身份验证

所有登录、OAuth、邮箱验证码、Gmail 读取和目录会话操作必须通过指定的 `ego-browser` skill 完成。先读取：

```text
C:\Program Files\Citro Labs\ego lite\Application\0.5.2.12\ego-skills\ego-browser\SKILL.md
```

使用同一个 ego-browser TaskSpace/Page 完成目录认证和原始提交；不要改用其他浏览器自动化工具或直接读取浏览器 Cookie/存储。

## 账号身份来源

使用 Shipmore claim 载荷中的 `productContactEmail` 作为目录账号邮箱。它是 Shipmore 解析出的有效提交身份：

1. Product 存在 `productSubmissionOverride.contactEmail` 时使用它；
2. 否则使用 Product 所有者的 `userSubmissionProfile.contactEmail`。

不得从产品文案、站点域名、创始人资料或浏览器账号推导、猜测或替换邮箱。不要把它写入证据、exact result、截图或日志。站点显示的其他邮箱账号不能视为同一身份，除非 Shipmore 后续明确返回该邮箱。

## 登录状态判断

登录状态必须在当前 ego-browser TaskSpace/Page 中重新确认。至少检查一项可见身份和一项受保护功能：

- 账号菜单中的可见用户标识、邮箱别名或头像菜单；
- 页面提供 `Dashboard`、`Logout`、账号设置等已登录入口；
- 受保护的目录提交页可以直接打开并显示表单，而不是重定向到登录/注册页；
- 目录账号页面显示与有效提交身份一致的账号信息。

claim 载荷中的历史 `exactResult`、其他浏览器中的登录状态、公开页面或地址栏 URL 不能单独证明当前 ego-browser 已登录。无法确认身份时，不得输入密码、复制会话材料或继续可变提交。

## 授权范围

当前授权允许 worker 使用上述有效目录账号邮箱，为合法产品收录完成身份验证，并在确实需要时创建一个普通免费账号。认证顺序如下：

1. 已授权浏览器会话中的 Google OAuth；
2. 已授权浏览器会话中的 GitHub OAuth；
3. 站点原生邮箱验证码或 magic link；Google 托管邮箱优先使用已授权 `gws`，不可用时才使用匹配的 Gmail 浏览器会话；
4. 普通邮箱/密码登录。

认证成功后可以继续原始提交。只有站点明确报告该邮箱没有账号时，才允许创建一个普通免费账号。

授权不包括付费、付费试用、手机验证、身份/KYC、passkey/安全密钥、绑定其他 Google/GitHub 身份、可选 newsletter/推广、无关公开发帖、多账号创建或绕过 CAPTCHA、Turnstile、访问控制。

## 运行时凭据

邮箱来自 claim 载荷，不从本地秘密文件读取。可选密码是运行时秘密，不能写入仓库，可从以下位置读取：

```text
/root/.config/backlink-skills/directory-account.env
```

可选变量：

```text
DIRECTORY_ACCOUNT_PASSWORD
```

只有第四种认证方式确实需要密码时才读取，且不得打印。不要运行 `env`、`set`、`printenv`、`set -x` 或任何会回显密码的命令。不得把有效邮箱或密码放入命令参数、备注、截图、Shipmore 载荷或证据。不要提交运行时文件。

## 登录与注册决策树

1. 有明确授权的现有目录会话时优先复用。
2. 站点提供 Google 登录时，仅当现有 Google 会话明确对应有效邮箱才使用；不要输入 Google 凭据、选择其他账号、授予额外权限或创建/绑定新身份。成功后发送 heartbeat 并继续提交。
3. 否则，站点提供 GitHub 登录时，仅当现有 GitHub 会话对应有效邮箱才使用；不要输入凭据、选择其他账号或授权超出普通登录的权限。成功后发送 heartbeat 并继续。
4. 否则，站点提供邮箱验证码或 magic link 时，输入有效邮箱并只触发一次验证消息，然后使用下方 Gmail 流程。
5. 否则，站点支持邮箱/密码且存在 `DIRECTORY_ACCOUNT_PASSWORD` 时，用有效邮箱和运行时密码尝试一次普通登录。
6. 只有站点明确表示该邮箱没有账号时，才用有效邮箱和可用方式注册一个普通免费账号；姓名、公司等字段只能使用已验证的 Shipmore Product 字段，未知可选字段留空。
7. 只接受创建普通免费账号和目录提交必需的协议；不要勾选 newsletter、推广、合作方、试用或无关同意项。
8. 不得因一般登录失败推断“没有账号”。除非站点明确报告前一次已过期或未完成，否则不要重试认证、邮件、密码或注册流程。
9. 注册提示邮箱已存在时，不得创建第二个账号；返回一次受支持的登录方式，仍失败则如实记录阻塞原因。
10. 每个提供商最多一次尝试、邮箱验证邮件最多发送一次、密码登录一次、注册一次、注册后认证一次；站点自身的正常重定向不算重复动作。

## Gmail 验证（优先 `gws`，否则 Gmail 网页）

Google 托管邮箱只能使用已经授权的 Gmail 账号。`gws` 可用时优先使用它；不可用时才可使用 `https://mail.google.com` 上现有且明确匹配 `productContactEmail` 的 Gmail 会话。只读取匹配验证邮件，不发送、回复、删除、归档、修改邮箱设置或使用其他账号。

1. 先确认授权邮箱与 `productContactEmail` 一致；无法确认时，不要触发验证码。触发前记录 UTC 时间；租约存在时先 heartbeat。
2. 只触发一次站点原生邮箱验证。除非站点明确报告验证码已过期或未发送，否则不要重复请求。
3. 使用 `gws` 时，只搜索该站品牌/域名和常见验证词的近期邮件，例如：

   ```bash
   gws gmail users messages list --params '{"userId":"me","q":"newer_than:1d (verification OR verify OR code OR OTP)","maxResults":20}'
   ```

4. 只读取候选邮件：

   ```bash
   gws gmail +read --id <message-id> --headers --format json
   ```

5. Gmail 网页回退时，只搜索匹配邮箱中该站近期候选邮件，不要读取无关邮件。
6. 选择触发时间之后、发件人/主题/正文都明确匹配当前目录的最新邮件，不得使用其他服务的验证码或链接。
7. 只提取所需的一次性验证码或验证 URL；不得打印、持久化、写入证据或日志，也不得复制其他邮箱内容。
8. 在同一个已授权目录浏览器会话中输入验证码或打开验证 URL，再重新读取页面确认成功。
9. 每 10 秒轮询一次，最多 2 分钟，并按需 heartbeat。未收到匹配邮件时，保留 `awaiting_email_verification` 或最接近事实的阻塞/跟进状态，不要重新注册。
10. OTP 和 magic link 都是临时秘密，绝不能保存到 Shipmore、仓库文件、截图、持久备注或命令历史。

## 停止和分类

出现以下情况时停止自动认证并如实分类：

- 需要 CAPTCHA、Turnstile、手机验证、KYC、安全密钥/passkey 或人工审批；
- 唯一注册方式需要付费或付费试用；
- Google/GitHub 会话不存在、身份不匹配，或要求超出普通登录的凭据/绑定；
- 已验证 Product 字段缺少注册所需身份资料；
- 无法有把握地把邮箱消息匹配到当前目录；
- 凭据被拒绝且没有明确安全的注册路径；
- 站点禁止或技术上阻止可用自动化界面；
- 租约丢失或过期。

超出上述授权范围的认证步骤使用 `blocked_account_or_email_policy`。不要因为普通邮箱/密码登录或免费注册是必需步骤就直接输出 `account_strategy_required`，应先执行本授权流程。
