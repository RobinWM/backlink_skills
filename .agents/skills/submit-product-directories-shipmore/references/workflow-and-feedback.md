# Worker 工作流与反馈回路

每个 Run Item 使用下面的检查单。在工作记录中复制检查项，并在有证据引用时记录关口通过或失败所依据的不透明引用值。

## 0. 分流

- [ ] 确认 `runId`、worker ID 和执行模式。
- [ ] `SHIPMORE_MANAGED_LEASE=1` 时只处理当前已租用的 Run Item，由 managed worker 维护 heartbeat；否则使用 direct/manual 循环。
- [ ] 浏览器操作前锁定唯一 provider，只读取该 provider 对应的 runtime 参考文件。
- [ ] 读取 API、状态映射、worker loop、浏览器路由和 `EXEC-CHECKLIST.md`。
- [ ] 仅在需要时读取认证、入口与内容路由、并发执行或生产加固的参考文件。

## 1. 领取并建立任务事实

- [ ] 打开或修改目录页面前先 claim。
- [ ] 设置 `runItemId = claim.data.id`，记录 `reason=claimed|reused`。
- [ ] 核对所有权、租约、provider lock、Product 事实、Directory 路由和已有 Submission 快照。
- [ ] 若 `debugHistoryIgnored=true`，只使用当前 Product、Directory、有效提交身份及实时网站证据；不得恢复被屏蔽的历史 Submission 字段。

## 2. 按顺序通过关口

依 [worker-loop.md](worker-loop.md) 的详细规则执行，并在第一个有决定性证据的失败处停止：

1. 路由是否可用，以及是否仅有未经授权的付费路径；
2. 目录要求 backlink、reciprocal、permanent 或 badge 时，注册 outbound link 并验证首页链接或精确 listing URL；
3. 检查重复记录和已有提交生命周期；
4. 确认入口及内容类型；
5. 遇到登录要求时执行账户认证预检；
6. 核对必填字段是否有已验证的 Product 数据；
7. 检查 CAPTCHA、Turnstile 等人工验证边界；
8. 准备安全、可逆的表单内容；
9. 若站点提供原生 badge/backlink verifier，在可执行时完成验证；
10. 执行 `EXEC-CHECKLIST.md` 的 `before_final_action` 阶段。

不要让后面的缺失字段覆盖更早的决定性终止原因。verifier 暂时 disabled 时，继续完成安全且可逆的表单准备，再到最终动作边界重新检查；不能直接判为 `ineligible`。

## 3. 最终动作与结果

- [ ] 通过 provider 对应的最终动作 guard，对选定的 `submit`、`publish`、`claim` 或 `gmail_send` 只执行一次。
- [ ] 重新读取页面、服务端或邮箱的精确结果。点击成功或收到 HTTP 响应本身都不能证明已发布。
- [ ] 执行 `EXEC-CHECKLIST.md` 的 `after_result_classification` 阶段。
- [ ] 根据已观察到的事实完成 Run Item；最终动作已发生时复用 journal 的 `completionEventId`。

## 反馈回路

每个关口以及结果分类后都按下列步骤复核：

1. 将实际证据与该关口的通过条件对照。
2. 失败时记录精确错误、页面状态和证据引用。
3. 仅在对应参考文件允许时，做安全、实质不同且可逆的检查或修正；遵守认证尝试和 backlink 轮询各自的次数限制。
4. 重新执行失败关口及其依赖的检查单。
5. 没有获准的下一种安全路径、租约丢失或最终动作可能已发生时停止可变操作。

最终动作尝试后不得重复点击。只能通过账户历史、邮箱、服务端回执或公开列表等只读证据核验；无法证明是否被接受时，分类为 `submission_outcome_unknown`。

## 完成条件

终态记录须包含真实的 Run Item 状态、submission status、已观察到的精确结果、检查单阶段与结果；有可用证据引用时记录不透明引用值。不得为了通过检查而虚构 Product 事实、凭据、公开 URL 或成功状态。
