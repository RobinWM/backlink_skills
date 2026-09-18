# 博客 3P 的执行效率：采用、试验与拒绝

本页记录矩阵对“token 很高、耗时很长”的技术判断。目标不是压缩掉独立 W/R，也不是用更便宜模型替代编辑判断；目标是让模型只花在读者价值、证据判断和语言质量上。

## 已采用的做法

| 做法 | 在本矩阵中的实现 | 为什么可行 |
| --- | --- | --- |
| 最小充分上下文 | `context/article-contract.json`、`reviews/review-index.json` 和发生变化的文件；历史只以路径/哈希按需回读 | 冻结范围、CTA 和 finding 谱系不丢失，同时避免每轮重灌历史日志。 |
| 程序先处理确定性错误 | `check-article-package`、`check-review-ready`、载荷校验、哈希和批量 G 检查 | 路径、hash、精确 CTA、固定载荷顺序不需要占用 R 的编辑推理。脚本通过绝不等于文章通过。 |
| 首次完整审稿，后续按差异审 | 同一 R 的 `FULL_REVIEW`，以及有边界的 `R_DELTA` / `R_VISUAL_DELTA` | 初次独立性保留；已定位、小范围修复不强迫全文重读。 |
| 批量 G | 一次 `BATCH_GATE_ACCEPTANCE` 与按 URL 回传批次的公开页 G | G 只验收范围、哈希和例外，不重做 R 的 SEO/语义审稿。 |
| 只记录异常 | 不生成逐项 PASS 表、重复研究摘要或空泛复盘 | 降低输出与下轮输入，不丢失真正的 finding ID、来源与哈希。 |

`check-review-ready` 是一个节省模型调用的保险丝：它在 R 前运行，但只发现机械不一致。它不写新证据、不做关键词密度或长度打分、不阻断创作，也不把“结构正确”错误升级为“文章优秀”。

## 受控试验，而非默认规则

| 想法 | 结论 | 原因与条件 |
| --- | --- | --- |
| 自动为 W/R 换低价模型 | 不默认采用 | 路由论文多来自问答或代码基准，不能直接外推到跨语言 SEO 文稿。必须先对 3–5 条历史 lane 影子评测，并记录被强模型推翻的比例。 |
| 用模型摘要取代旧来源或冻结契约 | 不采用 | 摘要可能遗漏限定条件或把旧错误固化。摘要只能当导航；冻结字段、URL、来源原文与哈希必须可回源。 |
| 增加辩论/更多审稿代理 | 不默认采用 | 同一篇文章的 W→R 有依赖关系；额外辩论通常增加上下文与协调成本。只有重大来源冲突可临时增加一次盲挑战，且由原 R 依据来源裁决。 |
| 所有主张拆成原子台账 | 不采用 | 机械拆分会让普通背景写作变成填表。仅对价格、日期、比较、性能、易变政策和高后果表述优先建可核验记录。 |
| 缓存整篇文章或所有网页 | 不采用 | 可变内容、平台政策和具体文章证据不能跨任务盲复用；只按已有共享证据规则复用精确、非易变且同语境的材料。 |

## 量什么，而非猜什么

运行 `harnessctl.py summarize-efficiency --workspace <campaign> --output evidence/operations/efficiency-summary.json` 可得到本地只读汇总。它不伪造模型账单：只有运行环境实际提供 `input_tokens`、`output_tokens`、`wall_time_seconds` 或 `tool_calls` 时才累加；否则明确写为 `UNAVAILABLE`。

比较实验必须保持文章、模型、验收标准和人工发布边界一致。建议同时看：

- 每个 `HUMAN_RELEASE_READY` / `PUBLIC_QA_PASSED` 的总阶段数、实际 token 和墙钟时间；
- 首次完整 R 通过率、R-Δ 次数、R-Δ 升级全文的比例；
- 被 R/G 发现的 CTA、事实、范围或交付传递缺陷；
- 人工发布后的 `HUMAN_TRANSPORT_FIX_REQUIRED` 与公开页缺陷。

若成本下降但高风险主张漏检、CTA 漂移、人工返工或公开页问题增加，就视为失败，不扩展到下一批。

## 证据如何被使用

实践来源支持“短契约、按需上下文、程序化确定性检查、选择性并行与可观测性”：

- [OpenAI：Harness engineering](https://openai.com/index/harness-engineering/) 反对用巨型说明文件替代可组合的仓库上下文；
- [GitHub：改进 Copilot Code Review 的工程复盘](https://github.blog/ai-and-ml/github-copilot/better-tools-made-copilot-code-review-worse-heres-how-we-actually-improved-it/) 采用从差异提出问题、收窄读取范围再判定的审查路径；
- [Anthropic：多代理研究系统](https://www.anthropic.com/engineering/multi-agent-research-system) 同时展示独立并行的价值与多代理 token 成本，故本矩阵只跨文章并行；
- [阿里云：云小二 Aivis 的实战经验](https://developer.aliyun.com/article/1687789) 与 [Qoder 团队的 Credits 优化](https://juejin.cn/post/7586482851103195171) 支持中文工程场景中的边界明确、上下文去噪和范围隔离；
- [MetaGPT 中文多智能体通信文档](https://docs.deepwisdom.ai/main/zh/guide/in_depth_guides/agent_communication.html) 与 [Dify 监控文档](https://docs.dify.ai/versions/3-0-x/zh/user-guide/monitoring/analysis) 支持角色按相关输入订阅、对运行指标可观测和把模板工作移出模型。

也交叉查看了不同技术路径，而没有把任何一个产品案例直接移植过来：

- [AWS Bedrock 的缓存案例](https://aws.amazon.com/blogs/machine-learning/how-care-access-achieved-86-data-processing-cost-reductions-and-66-faster-data-processing-with-amazon-bedrock-prompt-caching/)、[Cloudflare Code Mode](https://blog.cloudflare.com/code-mode-mcp/) 与 [Manus 的 Context Engineering 复盘](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)分别涉及缓存、工具执行与文件系统外置上下文；它们支持“稳定信息外置、按需加载”的方向，但其模型、缓存命中率、工具权限和任务类型与本矩阵不同，因此不采用其任何百分比或全局缓存做法。
- [腾讯云开发者社区的工作流讨论](https://developer.cloud.tencent.com/article/2555290) 和 [InfoQ 的行业复盘](https://www.infoq.cn/article/x4PTF8mgDBvtQQYa8B97)补充了中文从业者对规则/模型分工和成本失控的观察；它们属于案例或行业解读，不是受控实验，只用于提出待本地验证的风险假设。

学术来源提供机制上的交叉检验，而非可直接套用的降本承诺：

- [Selective Context](https://aclanthology.org/2023.emnlp-main.391/) 和 [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) 说明冗余长上下文既有成本也会伤及关键信息使用；
- [FActScore](https://aclanthology.org/2023.emnlp-main.741/) 与 [SAFE](https://arxiv.org/abs/2403.18802) 支持优先核验可影响结论的事实，而非把全文粗暴二分为“真/假”；
- [Pride and Prejudice: LLM Amplifies Self-Bias in Self-Refinement](https://aclanthology.org/2024.acl-long.826/) 说明不能以 W 自我修订取代独立 R；
- [MARS](https://openreview.net/forum?id=UWRfA2eWKE) 支持避免无边界的代理讨论，但它仍是审稿中研究，结论只用来限制复杂度；
- [RouteLLM](https://arxiv.org/abs/2406.18665) 支持“路由可降成本”的研究方向，但只有本地校准后才允许改变模型配置；
- [Agentless](https://arxiv.org/abs/2407.01489)说明简单的“定位—修复—验证”链可以避免无谓代理编排，但它研究的是代码修复，不能直接替代博客中的独立语言审稿。

各研究和工程案例的指标均属于它们自己的产品、模型、缓存与数据条件；本矩阵不承诺复制其百分比。
