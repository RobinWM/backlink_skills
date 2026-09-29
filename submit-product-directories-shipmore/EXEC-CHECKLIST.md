# Shipmore worker 执行检查单

每个 Run Item 在最终动作前和结果判断后各执行一次。检查单本身可以写入运行日志或受控 evidence；不得创建第二份本地队列或新的提交状态源。

## 使用规则

- 所有项目通过时记录 `checklist PASS`；任一项目不通过时记录 `checklist FAIL` 和具体原因。
- 最终动作前出现 FAIL，不得执行 Submit、Publish、Claim 或其他不可逆动作。
- 结果判断后出现 FAIL，不能把结果标记为成功；应保留当前事实并按 status mapping 分类。
- `evidenceReference` 只引用不透明证据 ID，不写密码、邮箱、OTP、Cookie、session ID 或 token URL。

## A. 最终动作前

### 所有任务

- [ ] 当前 Run Item 仍由本 worker 持有；
- [ ] 租约未过期；managed runtime 的 LeaseKeeper 正在运行且 lease guard 为 valid，direct/manual 模式必要时已显式 heartbeat；
- [ ] 当前 Run Item 已通过 `browser_action_guard.py select` 锁定 provider；若为 agent-browser，0.38.1 / doctor preflight 已通过且 deterministic named session 与 `runItemId` 绑定；若为 ego-browser，当前独立 TaskSpace/Page 与本 Run Item 绑定；
- [ ] 当前页面使用最新 provider 页面证据；agent-browser 标准写入已通过 adapter safe 方法和 read-back 校验；ego-browser 的每次可变动作前已通过 `browser_action_guard.py mutation-check`，写入后重新读取页面确认；
- [ ] Product、Directory、账号别名和当前提交路由相互匹配；
- [ ] 既有 `submissionStatus` 不属于禁止盲目重投的状态；
- [ ] 入口已经从首页、导航、页脚、站内搜索或真实控件确认；
- [ ] 入口类型已分类为目录表单、产品资料页、claim listing、内容编辑器或官方联系邮件；
- [ ] 站内重复查询已完成，且候选结果已核对实际出站 URL；
- [ ] `evidenceReference` 已引用入口和重复检查证据；
- [ ] 未选择未经授权的付费、推广、DNS、额外站点编辑或其他法律/财务动作；Shipmore outbound-link endpoint 完成的 reciprocal/backlink 不属于“未经授权互链”；
- [ ] 如果目录出现 backlink/reciprocal/permanent/badge 要求，已先走 Shipmore outbound-link；纯 backlink/reciprocal/permanent 场景在验证通过后没有再错误进入 Badge 安装分支；
- [ ] 必需 backlink 已注册并通过 Product 首页精确 hostname/path 验证；
- [ ] 如果是 badge 场景，已把表单推进到最终动作前的最后安全阶段；verifier 之前 disabled、隐藏或要求先完整填表时，没有因此提前停止；
- [ ] 如果最终动作前出现 Verify Badge / Check Backlink / Verify / Continue 等原生校验控件，已实际执行一次并记录实时结果；若没有执行成功，没有仅凭 badge/permanent/dofollow/install badge 文案、固定尺寸、示例代码或图片预览判 `ineligible`；
- [ ] 当前不存在尚未解决的 Badge 验证 pending 状态；如果 verifier 明确失败，`ineligible` 结论包含具体技术错误证据；
- [ ] CAPTCHA、Turnstile、邮箱验证等挑战已通过，或已按规则保留人工交接；
- [ ] 表单字段来自已验证 Product 数据，必填字段没有猜测值；
- [ ] 最终动作只计划执行一次；agent-browser 将通过 adapter `final-click`，ego-browser 将先执行 `browser_action_guard.py final-begin` 再执行一次最终动作；当前 runItemId + actionType 不存在已有 final-action journal。

### 内容编辑器阻断

如果入口属于以下任一分类，必须停止该站内容动作并记录 no-action：

```text
short note — no action
long post — no action
unknown — no action
```

不得填写内容、保存草稿、提交、发布或自动继续人工写作。只有内容编辑器的站点使用 `ineligible`。

### 站内去重证据最低要求

证据至少包含以下内容：

```text
规范 URL查询
裸域名查询
品牌/产品名查询
标题变体查询
候选数量
候选实际出站 URL核验结果
检查时间
```

如果无法完成查询，只有在当前批次明确授权时才允许一次直接尝试；必须记录缺口和授权引用。

## B. 结果判断后

- [ ] 重新读取当前页面、路由和原生文本，并确认最终动作后的当前 URL 与最新 snapshot；
- [ ] 记录与当前动作对应的原生正向或负向回执；
- [ ] 在可用时检查后端/账号历史、授权邮箱或公开页面；
- [ ] 不把点击、跳转、表单清空、草稿或普通感谢页单独当作成功；
- [ ] `submitted` 没有被误标为 `published`；
- [ ] `published` 有公开列表 URL；
- [ ] 结果不明时使用 `submission_outcome_unknown`，并将 final-action journal resolve 为 `outcome_unknown`；不再次点击最终动作；
- [ ] 有 Final Action 时 Complete 使用 journal 的稳定 `completionEventId`；无 Final Action 时使用第一次生成的稳定 `eventId`；
- [ ] `exactResult` 和 `evidenceReference` 只记录已观察事实；
- [ ] 发送 `complete` 前租约仍有效，必要时已 heartbeat；
- [ ] 记录 `checklist PASS` 或 `checklist FAIL: <reason>`。
- [ ] 如果发生受控重试，已记录唯一的 `retryDiagnostic`，并且下一步操作与上次实质不同；最终 Submit、Publish、Claim 和 Gmail Send 不得重试。

## C. 建议记录格式

```text
checklist: PASS
checklistPhase: before_final_action
checkedAt: 2026-09-24T10:00:00+08:00
evidenceReference: ev-opaque-123
failedChecks: none
```

结果判断后的记录把 `checklistPhase` 改为 `after_result_classification`。如果失败：

```text
checklist: FAIL
checklistPhase: after_result_classification
checkedAt: 2026-09-24T10:05:00+08:00
evidenceReference: ev-opaque-124
failedChecks: public listing URL missing for published status
```
