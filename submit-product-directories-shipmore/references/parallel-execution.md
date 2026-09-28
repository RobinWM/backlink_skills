# 并行执行与 Worker Pool

本 Skill 的并发单位是完整 worker，不是“一个 Codex 会话里同时维护多个 tab”。

## 模型

```text
Shipmore Run
    |
Worker Pool (N)
    |
    +-- worker-01 -> claim -> RunItem A -> named session A -> complete
    +-- worker-02 -> claim -> RunItem B -> named session B -> complete
    +-- worker-03 -> claim -> RunItem C -> named session C -> complete
```

每个 worker 必须：

- 使用 `scripts/worker_identity.py` 持久化的全局唯一 worker instance ID；pool slot 在其后追加 `-01`、`-02` 等，不再使用通用默认 `shipmore-worker-01`；
- 自己维护 claim / heartbeat / complete；
- 一次只持有一个 Run Item；
- 为该 Run Item 使用 deterministic agent-browser session；
- 完成、阻塞或跳过当前 Run Item 后再 claim 下一个；
- Run 暂停、终止或 queue empty 时退出。

## 启动器

`scripts/shipmore_worker_pool.py` 只做并发进程调度；每个 slot 应运行 `scripts/shipmore_worker.py`，由它负责长驻 claim + LeaseKeeper + one-item processor 生命周期。

```bash
python3 scripts/shipmore_worker_pool.py \
  --run-id <runId> \
  --concurrency 4 \
  -- python3 scripts/shipmore_worker.py \
       --run-id <runId> \
       -- <one-item-agent-command>
```

如果不显式传 `--worker-id-prefix`，pool 使用仓库外持久化的唯一 `SHIPMORE_WORKER_INSTANCE_ID`。若显式覆盖 prefix，调用方必须保证它在所有宿主机之间全局唯一；否则会破坏 Shipmore 的 worker ownership 语义。

Windows 可以使用 `python` 或 `py -3`。

启动器给每个子进程注入：

```text
SHIPMORE_RUN_ID=<runId>
SHIPMORE_POOL_SLOT=1..N
SHIPMORE_POOL_SIZE=N
SHIPMORE_CONCURRENCY=N
BACKLINK_WORKER_ID=<prefix>-01..N
```

`<one-item-agent-command>` 只处理当前 leased Run Item 并退出；长驻循环由 `shipmore_worker.py` 负责。processor 使用相同 worker ID 再 claim，得到 `reason=reused` 和完整 task envelope。若 processor 退出后同一 item 仍返回 reused，managed runtime 会停止并拒绝自动执行第二次，避免 crash 后重复 Final Action。

Pool 不会自动重启失败 worker，因为无条件 restart 可能掩盖最终动作结果不明。

## 并发上限

默认 4，硬上限 16。实际值根据 CPU、RAM、browser crash、lease timeout、OAuth/Gmail 拥塞和页面平均耗时调节。

不允许多个生产 worker 共用默认 agent-browser session，也不使用共享人类 Chrome + 多 tab 作为主并发模型。

## Pool 启动预检

默认启动前执行：

1. agent-browser 精确版本检查；
2. `doctor --offline --quick --json`；
3. 生产 state encryption 检查；
4. 在 `AGENT_BROWSER_NAMESPACE=shipmore` 内执行 `state clean --older-than N`，不清理其他项目 state。

预检失败时整个 pool 不启动。`--skip-preflight` 只用于调试。

## 终止

Ctrl+C 时 pool 先 terminate 子 worker，短暂等待后再 kill。worker 被终止不等于站点动作失败；后续恢复仍遵循 Shipmore lease 和最终动作不明规则。


## Host affinity

agent-browser restore state、lease guard 和 final-action journal 都是宿主机本地持久状态。相同 deterministic session name 不代表另一台机器拥有相同 session state。

生产恢复顺序：

1. 优先重启原宿主机上的相同 persistent worker instance；
2. active lease 使用相同 worker ID claim 时应得到 `reason=reused`；
3. 不要因为另一台主机可以 `recover` 就假设可以安全重新 Final Action；
4. 跨主机接管前必须检查 Shipmore lifecycle、账号后台、邮箱和公开页；有任何可能已提交的证据时使用 outcome unknown。

真正的跨主机 affinity/final-action fencing 需要 Shipmore 服务端支持，见 [production-hardening.md](production-hardening.md)。
