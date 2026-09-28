# Production hardening backlog

本文记录 `submit-product-directories-shipmore` 的上线前缺陷审计、风险级别、当前处理状态和仍需要 Shipmore 服务端配合的边界。

## 总览

| 优先级 | 问题 | 风险 | 当前状态 |
| --- | --- | --- | --- |
| P0 | heartbeat 依赖 Codex 主动调用 | 长推理/OAuth/邮件等待期间 lease 过期后仍继续操作 | **已实现客户端 LeaseKeeper + mutation gate** |
| P0 | Final Action 只执行一次主要靠 prompt | Submit 已到达站点但进程崩溃时可能重复点击 | **已实现本机 durable final-action journal；跨主机强一致仍需服务端 fencing** |
| P1 | 缺少真正长驻 worker runtime | pool 只会启动进程，不负责完整 claim → execute → complete 周期 | **已实现 `shipmore_worker.py` managed runtime** |
| P1 | worker ID 可能跨机器冲突 | 两台机器可被 Shipmore 误认为同一 worker | **已实现持久化随机 worker instance ID** |
| P1 | 跨主机 recover 没有浏览器/session affinity | deterministic session ID 相同但 state 不共享 | **部分处理：稳定 host identity + same-host recovery 规则；服务端 affinity 仍缺失** |
| P2 | state cleanup 只按年龄 | 长等待任务可能丢失浏览器 state | **已实现：只有真正终止性的 Submission lifecycle 才登记 cleanup；等待/blocked/unknown 状态保留 session** |
| P2 | worker pool 顺序 wait 子进程 | 后面的 slot 崩溃可能很久才被发现 | **已实现 wait-any supervisor；非 0 slot 立即使 pool fail-fast** |
| P2 | diagnostics 原始 console/network 可能含秘密 | 敏感 header、邮箱、请求体可能进入日志 | **已实现 adapter 内递归结构化脱敏** |
| P2 | `fresh_task` 仍信任调用方 | 调用错误可能把 seed load 到恢复任务 | **已实现 runtime 自校验 restore state / active session / recovery / journal** |
| P2 | Windows 真浏览器 E2E 目前非阻塞 | Windows 浏览器链回归可能不阻塞 merge | 待上游 Windows 稳定后改为 blocking |
| P3 | 缺少完整 Shipmore worker integration E2E | claim/heartbeat/lease-loss/final-action/recover 未端到端覆盖 | 待处理 |

## P0-A：自动 LeaseKeeper

Managed runtime 在 claim 成功后立刻启动 `LeaseKeeper`：

```text
claim
  |
  +--> LeaseKeeper ---- heartbeat every 60s
  |         |
  |         +--> lease guard JSON
  |
  +--> item processor / Codex
             |
             +--> Browser Adapter
                     |
                     +--> every mutation checks lease guard
```

默认：

```text
leaseSeconds = 300
heartbeatInterval = 60
```

LeaseKeeper 每次成功 heartbeat 会原子更新本地 guard；任何 heartbeat 网络错误、409、租约归属异常或 guard 超时都会让 guard 进入 invalid。Managed worker 中以下动作在执行前都必须通过 guard：

- open / bootstrap；
- fill / select / check / upload；
-普通 click；
- final action click。

因此即使 Codex 还在运行，只要 lease 不再可信，Browser Adapter 会拒绝继续可变操作。

相关实现：

- `scripts/lease_keeper.py`
- `SHIPMORE_MANAGED_LEASE=1`
- `SHIPMORE_LEASE_GUARD_PATH=<runtime path>`

## P0-B：Final Action durable journal

不可逆动作：

```text
submit
publish
claim
gmail_send
```

必须使用 Browser Adapter 的 `final-click`，不能使用普通 `click`。

执行顺序：

```text
确认按钮 visible/enabled
        ↓
同步 heartbeat
        ↓
lease guard PASS
        ↓
O_EXCL 原子创建 final-action journal
        ↓
state = attempting
        ↓
真正 click 一次
        ↓
成功返回 → state = dispatched
异常/timeout → state = outcome_unknown
```

Journal 在真正 click **之前**持久化，因此进程在 click 后、结果检查前崩溃时，恢复进程会看到已有 journal 并拒绝第二次 final click。

Journal 同时保存一个稳定 `completionEventId`，后续 Complete 超时应复用该 ID。

### 仍未解决的服务端边界

当前 Queue API 只有：

```text
claim
heartbeat
complete
recover
```

没有服务器侧：

```text
prepare_final_action
finalActionId
fenceToken
final_action_observed
```

所以本地 journal 能保证**同一宿主机/同一持久化 runtime 目录**不会重复 final action，但不能在以下灾难恢复场景提供数学意义上的 exactly-once：

```text
Host A click Submit
↓
Host A 磁盘永久损坏
↓
Shipmore recover
↓
Host B 无法读取 Host A 本地 journal
```

要解决该边界，需要 Shipmore 服务端增加 final-action fencing。建议后续协议：

```json
{
  "operation": "prepare_final_action",
  "runItemId": "...",
  "workerId": "...",
  "actionId": "...",
  "actionType": "submit"
}
```

服务端原子确认 lease + actionId 后返回 fence token；同一个 Product×Directory/final action 已存在时拒绝第二次 prepare。

在服务端接口落地前，生产恢复策略必须优先 same-host recovery；跨主机接管遇到任何“最终动作可能已发生”的证据时使用 `submission_outcome_unknown`，不得重新点击。

## P1-A：长驻 managed worker runtime

新增：

```text
scripts/shipmore_worker.py
```

它是 Queue/lease 层的长驻 runtime，不替代 Codex 的页面语义判断。

生命周期：

```text
claim
↓
start LeaseKeeper
↓
spawn one-item processor
↓
processor 使用同 workerId 再 claim → reason=reused → 获取完整 task envelope
↓
processor 按 Skill 完成一个 Run Item 并退出
↓
runtime 再 claim
   ├─ same item + reused → 认为未 terminal，停止，绝不自动再执行
   ├─ next claimed item → 继续
   └─ paused/terminal/empty → 退出
```

这样 Python runtime 自己长驻，而每次 Codex invocation 只处理一个 Run Item，降低一个模型会话跨很多网站后上下文漂移的风险。

## P1-B：全局唯一 worker identity

不再使用生产默认值：

```text
shipmore-worker-01
```

新增：

```text
scripts/worker_identity.py
```

首次启动在仓库外持久化：

```text
~/.shipmore/worker-instance-id
```

格式示例：

```text
shipmore-build01-a8f03172bc94de10
```

Pool slot：

```text
shipmore-build01-a8f03172bc94de10-01
shipmore-build01-a8f03172bc94de10-02
```

同一宿主机重启保持稳定；不同宿主机因随机 instance ID 不会碰撞。

`shipmore_worker.py` 还会对最终 `BACKLINK_WORKER_ID` 获取跨平台 advisory file lock。同一台机器如果误启动两个相同 slot，第二个进程会立即失败，而不是与第一个进程共享 Shipmore lease 身份。worker identity 文件和 lock 目录都属于宿主机运行时数据，不应烘焙进镜像或复制到另一台机器。

## P1-C：Host affinity

当前 agent-browser restore state、lease guard 和 final-action journal 都是本机持久状态。

因此：

```text
same runItemId
→ same deterministic session name
≠ same browser state across hosts
```

当前策略：

1. active lease 的恢复优先使用相同 persistent worker instance；
2. 同机进程重启使用相同 worker ID，可获得 `reason=reused`；
3. 不主动从另一台主机 recover 一个可能已经进行到 final action 的任务；
4. 必须跨主机时先检查 Shipmore lifecycle、账号后台、邮箱和公开页；
5. 无法证明未执行 final action 时使用 outcome unknown。

真正的跨主机 affinity/fencing 仍需要 Shipmore 服务端记录 worker instance / finalActionId。

## Managed runtime 启动

单 worker：

```bash
python3 scripts/shipmore_worker.py \
  --run-id <runId> \
  -- <one-item-codex-command>
```

并发：

```bash
python3 scripts/shipmore_worker_pool.py \
  --run-id <runId> \
  --concurrency 4 \
  -- python3 scripts/shipmore_worker.py \
       --run-id <runId> \
       -- <one-item-codex-command>
```

one-item processor 必须加载本 Skill。Managed runtime 会设置：

```text
SHIPMORE_MANAGED_LEASE=1
SHIPMORE_RUN_ITEM_ID=<id>
SHIPMORE_CLAIM_REASON=claimed|reused
SHIPMORE_RECOVERY_MODE=0|1
SHIPMORE_LEASE_GUARD_PATH=<path>
BACKLINK_WORKER_ID=<stable unique worker id>
```

processor 仍应调用 claim 获取完整 task envelope；因为使用相同 worker ID，API 返回 `reason=reused`。

## P2-A：Lifecycle-aware browser state cleanup

纯年龄清理已移除。Shipmore `complete` 明确成功后，只有 Submission 进入真正终止性的状态才登记 cleanup：`published`、`unavailable`、`paid_only`、`ineligible`、`duplicate_no_action`、`terminated_by_user`、`rejected`。默认保留 7 天，随后只执行 `state clear <sessionId>`。仍在等待审批/邮箱验证、blocked、结果不明或其他可恢复状态的 session 不自动删除。

agent-browser 自身的 `AGENT_BROWSER_STATE_EXPIRE_DAYS` 设为 36500，仅作为极高 safety ceiling，避免其默认年龄策略绕过 Shipmore lifecycle。

## P2-B：Wait-any supervisor

`shipmore_worker_pool.py` 不再按 slot 顺序阻塞 `wait()`。Supervisor 持续检查所有 worker；任意 slot 非 0 退出会立即被发现并终止剩余 slot，让外层调度及时告警/恢复。不会自动 restart 失败 slot，以免掩盖 Final Action 结果不明。

## P2-C：Diagnostics sanitization

Browser Adapter 的 diagnostics 在返回前递归处理：

- 敏感认证 header/字段；
- request/response body；
- 邮箱；
- URL query / fragment；
- Console 文本中的常见 credential 形态。

截图仍属于视觉证据，敏感认证页面继续遵守“不截图”的原有规则。

## P2-D：fresh_task self-verification

`fresh_task` 现在同时检查：

1. `SHIPMORE_RECOVERY_MODE`；
2. claim reason 是否 `reused`；
3. `agent-browser state list` 中是否已有 deterministic restore state；
4. `session list` 中是否已有活跃 session；
5. 是否已有任何 final-action journal。

任一命中都会拒绝 auth seed bootstrap。该检查是 defense-in-depth；Shipmore submission lifecycle 仍是是否 fresh 的第一事实来源。

## 仍待处理

1. 服务端 final-action fencing；
2. Windows 真浏览器 E2E 在 agent-browser 上游稳定后改为 blocking；
3. Queue + browser + crash/recovery integration E2E（P3）。
