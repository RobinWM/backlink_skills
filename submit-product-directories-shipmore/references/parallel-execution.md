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

- 使用唯一、稳定的 `BACKLINK_WORKER_ID`；
- 自己维护 claim / heartbeat / complete；
- 一次只持有一个 Run Item；
- 为该 Run Item 使用 deterministic agent-browser session；
- 完成、阻塞或跳过当前 Run Item 后再 claim 下一个；
- Run 暂停、终止或 queue empty 时退出。

## 启动器

`scripts/shipmore_worker_pool.py` 只做进程调度，不读取 Product/Directory，不替代 Queue 状态机，也不执行浏览器业务决策。

```bash
python3 scripts/shipmore_worker_pool.py \
  --run-id <runId> \
  --concurrency 4 \
  --worker-id-prefix codex-linux \
  -- <long-lived-worker-command>
```

Windows 可以使用 `python` 或 `py -3`。

启动器给每个子进程注入：

```text
SHIPMORE_RUN_ID=<runId>
SHIPMORE_POOL_SLOT=1..N
SHIPMORE_POOL_SIZE=N
SHIPMORE_CONCURRENCY=N
BACKLINK_WORKER_ID=<prefix>-01..N
```

`<long-lived-worker-command>` 必须加载本 Skill 并持续执行 `worker-loop.md`，直到 Run 暂停、终止或 queue empty。Pool 不会自动重启失败 worker，因为无条件进程重启可能掩盖最终动作结果不明；由 Shipmore recover 和外层调度决定是否重新启动。

## 并发上限

默认 4，硬上限 16。实际值根据 CPU、RAM、browser crash、lease timeout、OAuth/Gmail 拥塞和页面平均耗时调节。

不允许多个生产 worker 共用默认 agent-browser session，也不使用共享人类 Chrome + 多 tab 作为主并发模型。

## Pool 启动预检

默认启动前执行：

1. agent-browser 精确版本检查；
2. `doctor --offline --quick --json`；
3. 生产 state encryption 检查；
4. `state clean --older-than N`。

预检失败时整个 pool 不启动。`--skip-preflight` 只用于调试。

## 终止

Ctrl+C 时 pool 先 terminate 子 worker，短暂等待后再 kill。worker 被终止不等于站点动作失败；后续恢复仍遵循 Shipmore lease 和最终动作不明规则。
