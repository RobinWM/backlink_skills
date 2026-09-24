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
- [ ] 租约未过期，必要时已发送 heartbeat；
- [ ] Product、Directory、账号别名和当前提交路由相互匹配；
- [ ] 既有 `submissionStatus` 不属于禁止盲目重投的状态；
- [ ] 入口已经从首页、导航、页脚、站内搜索或真实控件确认；
- [ ] 入口类型已分类为目录表单、产品资料页、claim listing、内容编辑器或官方联系邮件；
- [ ] 站内重复查询已完成，且候选结果已核对实际出站 URL；
- [ ] `evidenceReference` 已引用入口和重复检查证据；
- [ ] 未选择未经授权的付费、推广、互链、DNS、站点编辑或其他法律/财务动作；
- [ ] 必需 backlink 已注册并通过 Product 首页精确 hostname/path 验证；
- [ ] CAPTCHA、Turnstile、邮箱验证等挑战已通过，或已按规则保留人工交接；
- [ ] 表单字段来自已验证 Product 数据，必填字段没有猜测值；
- [ ] 最终动作只计划执行一次。

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

- [ ] 重新读取当前页面、路由和原生文本；
- [ ] 记录与当前动作对应的原生正向或负向回执；
- [ ] 在可用时检查后端/账号历史、授权邮箱或公开页面；
- [ ] 不把点击、跳转、表单清空、草稿或普通感谢页单独当作成功；
- [ ] `submitted` 没有被误标为 `published`；
- [ ] `published` 有公开列表 URL；
- [ ] 结果不明时使用 `submission_outcome_unknown`，不再次点击最终动作；
- [ ] Complete 使用第一次生成的稳定 `eventId`；
- [ ] `exactResult` 和 `evidenceReference` 只记录已观察事实；
- [ ] 发送 `complete` 前租约仍有效，必要时已 heartbeat；
- [ ] 记录 `checklist PASS` 或 `checklist FAIL: <reason>`。

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
