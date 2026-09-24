# 入口发现、站内去重与内容面分类

本规则用于浏览器 worker 在进入任何可变表单操作前，确认当前页面到底是什么入口。它只产生浏览器侧观察结果和现有 Shipmore evidence，不创建本地队列，也不替代 Shipmore 的生命周期状态。

## 入口发现顺序

每个 Directory 从规范首页或 claim 返回的官方 `submitUrl` 开始：

1. 读取首页、导航、页脚、登录后区域和站内搜索；
2. 只把真实链接或按钮发现的当前入口作为候选；
3. 如果 `submitUrl` 发生重定向，记录最终官方路由并重新检查入口类型；
4. 已保存的深链只能作为线索，不能直接证明它仍是有效提交路由；
5. 只有常规导航、搜索和真实控件都找不到可验证入口时，才使用视觉检查页面首、中、尾三段；
6. 视觉发现的候选仍必须通过真实链接、按钮、表单或最终路由核验。

不得因为页面出现 `Submit`、`Post`、`Add` 或类似文字就直接进入表单。必须先确认它对应的业务入口和目标对象。

## 入口类型

将观察到的入口归为以下一种：

```text
directory_listing
product_profile
claim_listing
short_note
long_post
unknown_content_editor
official_contact_email
```

### 可执行入口

- `directory_listing`：目录收录表单，目标是公开展示产品规范 URL；
- `product_profile`：产品/工具资料页表单，目标是创建或更新产品资料；
- `claim_listing`：认领已有产品列表，必须另行确认认领动作授权；
- `official_contact_email`：目标站官方 Contact、投稿、资源推荐或合作页面提供的一对一联系邮箱。

### 禁止自动执行的内容入口

以下入口只做分类和证据记录，不得填写、预填、保存草稿、提交、发布或自动交给人工继续写作：

```text
short note — no action
long post — no action
unknown — no action
```

- `short_note`：短贴、简短动态或短消息编辑器；
- `long_post`：文章、博客、Guest Post 或长文编辑器；
- `unknown_content_editor`：无法确认是目录资料页还是内容编辑器的入口。

只有内容编辑器的站点，结果分类为 `ineligible`，不能分类为 `unavailable` 或 `submission_failed`。页面上的 `Post`、`Publish` 或 `Submit` 按钮不构成例外。

## 站内重复检查

在填写任何产品字段或执行认领前，使用站点真实的搜索控件完成以下查询：

1. 规范 Product URL；
2. 带和不带尾部斜杠的 URL 变体；
3. 裸域名；
4. 官方品牌名或产品名；
5. 从候选标题发现的词序、空格、连字符和大小写变体。

还要检查可用的账号后台、近期列表和分类列表。每个候选结果都必须打开或读取实际出站 URL，再与规范 URL 和域名进行归一化比对。标题相同或不同都不能单独作为重复结论。

### 观察结果

使用现有 `evidenceReference` 保存查询词、触发方式、结果 URL、结果数量、候选标题和实际出站 URL。`exactResult` 只保留摘要，例如：

```text
duplicate check cleared: 5 queries, 0 matching outbound URLs
duplicate confirmed: existing listing points to the canonical product URL
```

如果命中规范 URL 或规范域名，停止当前 Directory，使用 `duplicate_no_action`。不得继续登录、填写或提交。

如果站内没有搜索能力，或无法完整核验候选结果，不得静默当作已清除。只有当前批次明确授权时，才允许一次直接尝试，并记录具体缺口、已完成检查和授权引用。

## 结果与执行边界

入口发现和站内去重必须发生在以下动作之前：

- 登录或注册（仅为目录认证而必需的登录除外）；
- 填写产品字段；
- 上传素材；
- 保存草稿；
- 接受非必需协议或订阅；
- Submit、Publish、Claim 或发送官方邮件。

站内搜索已确认重复、入口属于 no-action 内容编辑器或入口类型无法安全确认时，停止该站并保留当前页面和 evidence reference。不要为了获得更清晰的结果而反复提交或创建第二个账号。
