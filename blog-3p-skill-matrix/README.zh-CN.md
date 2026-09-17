# 博客 3P Skill 矩阵

[English](README.md) · 版本 0.9.21 · [MIT 许可证](LICENSE)

这是一个面向高质量、可审计博客生产的开源 Skill 套件。它将文章工作拆解为可恢复的本地流程：建立战役和范围、完成有证据支撑的研究型写作、经过独立审稿与终审，再编译为供人工发布的可视化富文本交付包。它自动化内容质量工作，而不自动化平台发布。

## 一览

| 本矩阵负责 | 本矩阵明确不做 |
| --- | --- |
| 保存用户范围、研究证据、规范文章、独立文章审稿、需求验收，以及可直接复制的富文本交付页。 | 登录、操作平台编辑器、上传媒体、调用发布 API、发布、删除、回滚、定时发布或修改浏览器指纹。 |

它适用于本地优先的内容生产：人工而非自动化拥有最终的平台原生操作。只需 Python 3.9+ 与本地文件系统；网页、Trends、SERP 和公开页检查都是可选的只读证据适配器。

## 项目解决的问题

常见的“写一篇 SEO 文章”流程会将调研、写作、审稿、平台适配和发布混在同一对话里，因而容易出现来源丢失、审稿变自审、编辑器试错占用交付能力，以及读者页与本地稿脱节的问题。

本项目以职责明确的 Skill 分离这些问题，同时始终保持一篇规范文章和一条可追溯的读者可见改动记录。可见的平台匹配调研子会话先在用户候选范围内评估平台，之后用户才冻结映射；机架保存范围和状态；唯一可执行的 W 把调研与成稿结合；可复用的 W–R 内循环做文章质量决策；G 再确认最终交付没有丢失用户冻结任务；最后由人工通过平台原生编辑器完成发布。`blog-writer-merged` 是编辑核心参考，不是第二条 W 工作流。

## 运行模型

- **G 先取得派工资格。** 在任何文章工作树或 W/R 出现前，常驻可见主控必须收集并汇报每篇文章完整的写前调研与写作方案；等待 `OWNER_PREWRITE_PLAN_CONFIRMED`，将报告与结构化清单哈希绑定到任务契约后，才把用户已确认的要求写入 `requirements-contract.md`、维护战役状态与优先级并验收最终交付。它不能变成不可见的 CLI 审稿会话。
- **每篇文章只有一个可执行 W 与一个持续复用的 R。** `blog-3p-writer` 是唯一活跃写稿角色；它和语言审稿人贯穿该文的调研、写作、修复、完整审稿与增量审稿，绝不与其他文章共享。R 负责包括 SEO 在内的文章质量；W 维护 `requirements-traceability.md`。
- **工作树隔离必须显式记录。** 可见子任务不等于 Git 工作树。只有写前方案获确认后，宿主支持项目工作树时，G 才能在 W/R 启动前为每篇就绪的独立文章创建一个可见工作树任务；否则记录 `WORKTREE_UNAVAILABLE`，并且只有文章路径互不重叠时才能使用明确标识的共享工作区降级方案。
- **每个工作树包含完整文章泳道。** 工作树根角色是文章级 G，由它在同一工作树中创建并复用专属 W 与 R，按 `G → W ↔ R → G` 推进。战役级 G 仍是唯一的全局需求、队列和状态控制器，只汇总泳道报告，不重复其编辑判断。
- **质量与用户意图分开判断。** R 决定文章质量是否达标；R 通过后，G 只检查已确认的用户要求是否被遗漏、替换、弱化或扩展，不重复审稿文案或 SEO。
- **常规轮次使用紧凑证据索引。** 派发时，泳道 G 创建不可变、哈希绑定的文章契约；R 维护审稿索引，W 在有限修复时写 delta capsule。常规轮次只读取这些记录与变更工件；只有压缩、哈希漂移、finding 谱系未解或升级时才必须完整重读历史。代理替换和范围冲突属于升级条件。
- **读者价值优先，CTA 必须保留但从属。** 每篇文章都冻结读者价值承诺，并且不依赖 CTA 仍须有用；用户要求的 CTA 必须保留其精确可见锚文本、可识别产品、当前落地页、主张依据、读者任务相关性和适用关系披露。R 判断内容含义与商业平衡；G 只核对声明是否保真落地。
- **配图承载叙事，而不是凑数量。** 对实质性指南、教程、对比、评测和长篇解释文，W 至少规划三张原创、有信息价值的图，分别覆盖 `LEAD`、`MIDDLE`、`CLOSING`。R 必须打开每张图，核对相邻主张、可读性、独立读者作用与非重复性；首图、文件名、尺寸或 alt 均不能单独通过。
- **研究是成文前门槛，不是创意角度标签。** 用户先确认 G 的方向性方案；随后每篇文章须在大纲前记录真实的长尾读者意图及证据，每种目标语言须记录地区 SERP 自然变体。多篇英语稿必须有不同的意图 ID 与读者问题；同一可复用 R 先审批 W 的研究包，W 才能成文。
- **平台样本是建议性画像，不是可照搬的模板。** 一名可复用运营 steward 只能只读检查已授权平台的同语言、同内容类型公开样本；它为交付包生成确定性的格式画像，为读者适配生成非约束性的编辑画像。样本不足即为 `UNVERIFIED`，使用保守通用结构，绝不阻断研究或写作。
- **公开页质检只复用文章泳道 G。** 人工在结构化回执中记录 URL、精确的 `HUMAN_ACCEPTED`／`HUMAN_NEEDS_FIX` 状态和已知限制后，仅由该文章工作树既有的 `ARTICLE_LANE_GATEKEEPER` 接收一份有边界的只读公开页快照，并对照已验收的规范稿/载荷页做一次窄范围比对。它不重启 W/R、不创建 fresh 公开终审角色，也不重做文章 SEO/文案审稿；它只分类为通过、范围化限制下通过、人工传输修复、未核验或明确的规范稿变更请求。
- **标题层级只以公开视觉为准。** 规范稿和载荷页的标签仅服务于写作与复制选择，绝不证明平台传输结果。人工不得编辑平台编辑器的 HTML/DOM；`HUMAN_ACCEPTED` 后，泳道 G 只能依据公开读者页的渲染视觉验收标题、章节和子章节层级。快照可记录视觉证据路径，但绝不能推断层级结论。
- **平台匹配交给子会话，选择交给用户确认。** 冻结人工发布映射前，唯一可见、可复用的 `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` 仅在用户提供候选范围内，按冻结语言、市场和格式需求进行匹配。G 不排序、不选址，只保存报告并取得用户对准确平台/账号的确认。
- **CLI 只做机械工作。** 它可运行确定性的本地校验与编译，但不能替代审稿人或伪造证据。

## 架构

```text
用户任务与有来源边界的候选信息
        │
        ▼
G 的逐篇写前调研与写作方案
        │
        ▼
OWNER_PREWRITE_PLAN_CONFIRMED + 哈希绑定
        │
        ▼
可见文章工作树／泳道 G ──► W 一体化调研 ──► 同一 R：RESEARCH_APPROVED
                                      │
                                      ▼
                            W 规范交付包 ↔ 可复用 R 审稿
                                                   │
                                                   ▼
                                            G 终审决策
                                                   │
                            PASS = HUMAN_RELEASE_READY
                                                   │
                                                   ▼
                               可视化富文本人工交付页
                                                   │
                                                   ▼
       人工原生发布 → 回执 + 只读快照 → 同一泳道 G 的公开页检查
```

`PASS` 从不表示机器已经发布文章；它只表示本地编辑产物已准备好供人工使用。真正完成是另一状态：人工保存 URL／状态回执后，对于 `HUMAN_ACCEPTED`，由该文章既有的泳道 G 利用规范化快照和公开渲染视觉进行有边界的只读读者页契约检查。公开页差异不会重启 W/R：纯传输修复回到人工并由同一 G 复检；只有用户明确要求修改规范稿或载荷页才重开 W/R。

写前方案也不是绕过调研的捷径。它汇报 G 已收集的证据、已知限制与拟定写作路线，让用户能在昂贵的文章泳道启动前纠偏；确认后，W 仍须独立完成完整的来源、长尾词与本地化调研，只有 R 能给出 `RESEARCH_APPROVED`。

## 技能矩阵

| Skill | 职责 | 主要产物 |
| --- | --- | --- |
| `blog-3p-harness` | 初始化独立战役、记录用户确认的写前方案、冻结范围、安全恢复并执行结构校验。 | `campaign.json`、`state.json`、`prewrite-plan.md/json`、确认记录、清单 |
| `blog-3p-platform-matching` | 可见、可复用的子会话：只在用户候选源内调研语言/市场/格式适配，为每篇推荐一个平台。 | 匹配报告与待用户确认的提案 |
| `blog-writer-merged` | 关于证据、本地化、读者价值、图片和标题质量的编辑核心参考；绝不是第二条 W 泳道。 | 可复用编辑标准与参考资料 |
| `blog-3p-writer` | 唯一文章级写稿角色 W：调研、成稿、修复并编译审阅包。 | 文章包、内容指纹、修复记录、delta capsule |
| `blog-3p-review` | 文章级、可复用的语言审稿角色 R，跨该文章审稿轮检查内容、证据、标题/正文交接和稳定 finding。 | `reviews/review-N.md` |
| `blog-3p-gate` | 常驻 G，收集并汇报写前方案、等待用户确认后管理范围、队列、最终契约保真及同一泳道的发布后检查。 | 方案绑定、`requirements-contract.md`、`gate/gate-report-N.md`、`gate/public-qa-report-N.md` |
| `blog-3p-human-handoff` | 编译可在浏览器中打开、可直接复制的富文本交付页，并在人工发布后生成有边界的回传证据。 | `handoff/visual-payload.html`、回传回执、发布卡、公开页快照 |

矩阵刻意保持模块化：团队可以只使用机架和写作引擎，而不生成面向人工发布的包；也可以针对已有规范文章使用 W–R–G 内循环。所有组合仍遵守同一套契约。

## 核心保证

### 一篇规范稿，独立判断

W 只写作；R 只审不改，并对语言、事实、结构、SEO 与交付保真作完整质量判断；G 掌管状态，只验收冻结的用户任务是否完整留在最终交付中，不重做 R 的文章审稿。用户要求用 `REQ-*`，G 的契约缺口用 `REQUIREMENT-*`，文章质量继续用如 `SEO-LOCALIZATION-001` 的稳定 finding ID。

对规范文章或可视化富文本载荷页的读者可见改动都会更新规范内容指纹，并重新进入相应的 R/G 路径。仅由公开读者页发现的不一致由既有泳道 G 处理，不会自动重启 W/R。

### 紧凑且哈希绑定的文章上下文

派发时，泳道 G 写入 `context/article-contract.json`：它投影已确认的文章范围、适用 `REQ-*`、读者价值／CTA 声明、语言／市场、适用发布映射和来源哈希。R 维护 `reviews/review-index.json`，记录当前规范稿／交付包哈希、报告指针、审稿结论和稳定 finding 谱系。这些记录减少重复加载上下文，绝不能改写范围或覆盖源证据。

有限修复时，W 写入 `reviews/review-delta-N.json`，列明已批准的基线哈希、准确变更路径、受影响的主张／需求／finding，以及来源、本地化、标题／元数据、CTA、图片和载荷页的显式变更标记。R-Δ 只检查该胶囊、变更工件和直接依赖；只有压缩、哈希漂移、finding 谱系未解或含混或升级时才必须完整重读历史，代理替换和范围冲突属于升级条件。完整 R 仍会读取完整的当前规范交付包并打开每张最终图片。

### 读者价值优先；透明推荐从属

矩阵的首要产物是对读者任务有高质量、证据受限回答的文章。每篇新的 schema `2.2+` 文章都要冻结 `reader_value_promise`；即使移除 CTA，文章仍必须完整、有用。`cta.mode = NONE` 在新的 schema 2.2 战役中不合法。

每篇 schema 2.2 文章均使用 `cta.mode = SECONDARY_RECOMMENDATION`。当前 schema-2.4 工作流中的 `article-package.json` 使用 schema `1.3`，引用规范证据、视觉与交接清单，同时记录精确可见锚文本、产品身份、当前落地页 URL、主张证据路径、与读者任务的关联，以及关系披露或 `NOT_APPLICABLE`。这些字段只用于追溯推荐，绝不允许声称产品经独立验证、最优、已测试、始终可用或适合所有读者。R 而非 CTA 数量、字数比例、位置或密度规则，判断文章是否仍以读者为中心、平衡且真实；G 只检查冻结声明是否留在最终交付中。schema-2.2/2.3 工作区保留其历史 schema-`1.2` 交付包契约，不能只为采用新流程而改标版本。这能降低可避免的审核／删除风险，不能保证平台一定保留公开页。

### 用户确认的写前方案

在矩阵消耗工作树或启动写作／审稿泳道之前，G 必须维护覆盖每个已配置文章的唯一 schema-`1.3` `prewrite-plan.json`。每张卡明确读者与任务、独立读者价值承诺、必保留的次要 CTA 及其精确可见锚文本、目标链接、主张／来源边界和披露、证据与不确定性、关键词／本地化路线、暂定标题与大纲、图文叙事、运输假设，以及仍需用户决定的事项。G 运行 `harnessctl.py sync-prewrite-plan` 后生成供用户阅读的 `prewrite-plan.md`。该 Markdown 是确定性、只读视图：绝不能双份手填，也不能作为第二个范围事实源。

`OWNER_PREWRITE_PLAN_CONFIRMED` 是硬派发门。其确认 ID、文章集合、报告哈希和清单哈希必须在状态、用户确认记录、需求契约和范围锁中完全一致。方案发生实质改动即失效；在重新确认前，G 不能创建文章工作树、泳道 G、W、R、文章队列或文章代理。这使用户能在并发工作消耗时间和 token 前纠偏，同时不把 G 的方案伪装成 W/R 的正式调研。

### 图文叙事覆盖

战役会与 SEO 和范围一起冻结 `visual_narrative_policy`。标准策略要求适用文章类型以至少三张图片覆盖 `LEAD`、`MIDDLE`、`CLOSING`。图片清单中的每个条目都要将图片关联到章节锚点、相邻主张、读者作用、权利/来源、提示词或视觉简报、本地化 alt、图注与像素审查结果。

若某批次要求所有文章均不得例外，应在派工前设置 `all_articles_required: true`。这会使该战役的每篇文章都必须满足“三张图、三处覆盖”。其他例外也必须由用户确认并让 R 可见；绝不能因为图片缺失而被默认推断。人工交付页的图片卡会显示覆盖区与读者作用，帮助发布者保持正确位置。

### 不伪造本地证据的跨语言 SEO

对于已冻结的多语言目标，术语与关键词必须按以下严格优先级选择：

```text
CURRENT_BRAND_SITE → REGIONAL_SERP → MODEL_TRANSLATION_FALLBACK
```

- **当前品牌站：** 与目标地区、读者意图一致的现行公开品牌页，是最高优先级的用语来源。这能使博客与品牌用语及品牌语义矩阵保持一致。
- **地区 SERP：** 目标地区的搜索结果用于判断读者意图和自然语义变体。无论目标语言为何，Google Trends 都只比较英文种子词/英文候选，并记录英文概念到地区 SERP 用语的映射；它只能发现低基数、高势头的全球话题候选，绝不能被表述为本地需求证据。
- **模型翻译兜底：** 只有在两次独立地区 SERP 核验均记录为没有可用共识变体后才能使用。必须记录候选用语、失败核验、理由与文化/法律风险，且绝不能标注为“SERP 已验证”。

品牌站现有表达也不能无条件照搬：过时、误导、不自然或与本文意图不符时，必须留证拒绝。地区 SERP 只用于理解本地意图和表达，绝不用于复制竞品文本。

### 成文前长尾研究

矩阵不接受空关键词变体、泛化主词、标题文案或编辑创意角度作为研究证据。用户确认 G 的写前方案前，G 只汇报拟定的关键词／本地化路线与不确定性；确认之后、生成大纲或正文之前，W 必须记录候选与淘汰的长尾词、读者问题、查询/日期/证据和选用表达。多篇英语稿还须维护意图登记表：主长尾词和读者问题必须在语义上实质不同。

每个目标语言的记录须包含目标地区 SERP 查询、自然变体、选词来源和拒绝的机械直译。仅英文的 Google Trends 比较只能提供全球势头背景，不能证明目标语言用词。两次独立地区核验均没有可用共识时，才可用 `MODEL_TRANSLATION_FALLBACK`，并须保存两次核验与语言理由。同一 R 先给出 `RESEARCH_APPROVED`，W 才可写正文；终审时还会复核文章没有偏离研究结论。

### 已授权平台的风格画像

G 冻结准确的平台/账号组合后，可复用的战役运营 steward 才能针对同一平台、语言与内容类型的公开样本做尽力而为的只读检查。它必须记录来源、日期、可见信号和不确定性，并产出两份彼此独立的文件：

- `format-profile.md` 是确定性的交付输入：可用标题/元数据字段、标题/正文传递建议、公开视觉层级观察，以及可观察到的列表、链接、图片、商业披露或版式限制。它绝不指示修改编辑器 HTML/DOM；存在时由人工交付包读取。
- `editorial-style-profile.md` 是建议性的写作输入：只记录能够成立的标题语气、开头方式、段落节奏与结构观察；W 仅可用它优化读者适配。

两份画像均不能证明关键词需求、事实主张、平台政策或“热门度”，也不能改变范围、规范事实、本地化长尾/SERP 选词、必保留次要 CTA 的精确锚文本／链接／披露，或图文叙事要求。不得复制样本标题、措辞、论证路径、互动数据或促销模式。样本不可得、不完整或无法证明可比时，标为 `UNVERIFIED` 并使用保守通用结构；仅因缺少画像，R 不得提出 finding。只有通过 `PUBLIC_QA_PASSED` 读者页核验的行为，才能沉淀为长期平台技能；`PUBLIC_QA_PASSED_WITH_LIMITATION` 只能沉淀具备完整范围、日期且不可泛化的限制记录。参见[画像模板](docs/platform-style-profiles.md)。

### 人工原生发布边界

常规发布路径不会登录平台、向编辑器输入、上传媒体、点击发布、删除或回滚内容、调用写 API，或修改浏览器指纹。机器只生成唯一由编译器拥有的 `BLOG_3P_VISUAL_PAYLOAD@2`：所有文章共享同一份刻意简洁的页面壳与自上而下顺序——博客标题、带中文图片注释的正文、SEO title、tags、description。W 只能提供规范标题、来源大纲/正文、图片清单和元数据，不能为单篇文章设计页面壳、CSS、JavaScript 或操作按钮。页面不含按钮、剪贴板代码或复制成功承诺；发布者在浏览器中手动选中可见标题与正文，再粘贴至原生编辑器。编译器会拒绝缺失或改写必保留 CTA 精确可见锚文本、href 或适用披露的包/正文，且绝不自行添加促销文案。发布者不得查看或修改平台编辑器 HTML/DOM 来强制标题标签。每则注释会完整显示本地化 Alt 和图注；Alt 缺失会使编译失败。人工通过平台原生界面发布并验收读者页；若回传 URL 且标注 `HUMAN_ACCEPTED`，只有该文章既有的泳道 G 会依据公开读者页的渲染视觉验收标题层级，而不是依据本地载荷、编辑器、源码或 Feed 标记；它绝不会自行执行平台操作或重开 W/R。

人工回传刻意保持轻量：一份 `public-return-receipt.json`，然后仅在 `HUMAN_ACCEPTED` 时生成一份规范化、有边界的公开页快照。快照记录标题／正文指纹、链接／图片／CTA 观察和获取限制，而不是新稿或语义结论。G 用它写紧凑的公开页 QA 报告：纯平台传输问题生成一份合并人工修复清单并回到同一 G；已记录的平台限制只有在读者可见契约仍满足时才可通过；证据不可得时保持未核验；规范稿／载荷页变更必须有用户明确的请求 ID。

### 严格的平台范围

冻结平台映射前，唯一可见、可复用的 `CAMPAIGN_PLATFORM_MATCHING_RESEARCHER` 是确认前唯一允许的子角色例外。它只在用户提供 XLSX/表格/消息候选内，以语言、市场和内容格式为条件进行只读比较，并把哈希锁定的推荐输入 G 的方案；它绝不能启动文章调研、工作树、W、R、大纲或正文。G 不预筛、不排序、不选平台；它只校验来源与不重复结构，然后取得用户确认。

平台/账号组合随后只能来自引用该匹配提案、用户确认且哈希锁定的 `owner-platform-selection.json`；`platform_scope.allowed_pairs` 只是其机械校验后的投影，绝不能反过来充当授权来源。每个 pair 收据必须指向用户原始 XLSX/表格/消息、其 SHA-256、精确行/单元格或消息定位、平台原文、账号确认原文和用户确认 ID。套件不会发现、推荐、添加、替代或悄悄排队任何其他平台。若源内匹配没有可辩护的推荐，或缺少用户确认，状态只能是 `OWNER_DECISION_REQUIRED`，绝不是 G 替用户选择平台的授权。

官方登录/注册页、平台公告、公开样本、预检/激活记录、会话恢复证据、内部配置和历史战役映射都只能作为适配性或运营证据。它们可以在用户选定**之后**支持单独记录的 `locale_platform_validation`，但绝不能创建允许 pair、成为冻结映射，或反向验证从自身复制出的映射。若授权列表用尽，状态为 `CAPACITY_BLOCKED`，直到用户明确提供并重新确认新的组合。

人工发布批次还必须在确认时冻结一张一对一的 `article_id → platform → account` 表。每篇文章只绑定一个不同的平台，且其平台/账号对不得被另一篇复用；缺失或重复映射只阻塞受影响文章。G 绝不会默认把多种语言分配到一个已验证平台，也不会从另一篇文章借用平台。

确认表还应为每篇文章记录用户确认的文章语言与市场、映射的平台/账号、该平台支持的内容语言及证据。平台语言只决定能否承接，绝不改变文章语言；不兼容时以 `LOCALE_PLATFORM_MISMATCH_RECONFIRM_OWNER` 停住该文章。

标题采用三层契约：字段映射是确定性规则，交付包保真可机械核验，语义质量交给 W/R 判断。它们依据读者任务、清晰度、价值、自然语言和市场适配审题；G 只核对冻结字段是否保真。字面关键词和长度只是不阻断的风险提示。平台标题默认等于规范文章标题，不能暗中采用更短版本。标题/章节层级则在人工发布后单独以公开视觉验收。

## 自动化范围

| 本地自动化 | 可选只读适配器 | 人工负责或明确不在范围内 |
| --- | --- | --- |
| 工作区创建、JSON 校验、来源台账、关键词/主张审计、稳定 findings、规范内容指纹、富文本载荷页编译 | 搜索、Google Trends、公开 SERP 检视、公开页 HTML/Feed/截图比对、外部 SEO 扫描 | 账户创建/登录、CAPTCHA/2FA、编辑器输入、文件上传、发布、删除、回滚、定时发布、写 API、浏览器指纹变更 |

对标题层级，只有公开页的渲染视觉是证据。HTML 或 Feed 可辅助比对正文、链接或元数据，但不能判定标题级别。

不可用的适配器只会记录为 `UNAVAILABLE` 或 `UNVERIFIED`，绝不会伪造成通过。

## 快速开始

环境要求：Python 3.9+ 与本地文件系统。随包脚本仅使用 Python 标准库。

```sh
# 在本仓库目录中执行。
cd blog-3p-skill-matrix

# 请保留完整包：skills/ 和 docs/ 共享同一套契约。
python3 skills/blog-3p-harness/scripts/harnessctl.py init \
  --workspace /absolute/path/to/campaign \
  --campaign-id my-campaign

# 填写 campaign.json 和唯一可编辑的 schema-1.3 prewrite-plan.json，
# 再确定性生成面向用户的 Markdown 视图；绝不能双份手填。
python3 skills/blog-3p-harness/scripts/harnessctl.py sync-prewrite-plan \
  --workspace /absolute/path/to/campaign

# 汇报生成的 prewrite-plan.md，记录 OWNER_PREWRITE_PLAN_CONFIRMED，
# 再校验结构契约。
python3 skills/blog-3p-harness/scripts/harnessctl.py check \
  --workspace /absolute/path/to/campaign

# 对当前 schema-2.4 的文章包（schema 1.3），核对规范工件来源声明
# 与冻结的读者价值／必保留 CTA 映射。
python3 skills/blog-3p-harness/scripts/harnessctl.py check-article-package \
  --workspace /absolute/path/to/campaign \
  --package /absolute/path/to/campaign/article-package.json

# 人工回传 URL／状态回执后，先校验，再交给同一泳道 G 做只读快照检查。
python3 skills/blog-3p-harness/scripts/harnessctl.py check-public-return-receipt \
  --workspace /absolute/path/to/campaign \
  --receipt /absolute/path/to/campaign/handoff/public-return-receipt.json \
  --article-package /absolute/path/to/campaign/article-package.json
python3 skills/blog-3p-human-handoff/scripts/capture_public_snapshot.py \
  --receipt /absolute/path/to/campaign/handoff/public-return-receipt.json \
  --article-package /absolute/path/to/campaign/article-package.json \
  --output /absolute/path/to/campaign/evidence/public-qa/public-snapshot.json
```

随后按以下顺序调用 Skill：

1. `blog-3p-harness` + `blog-3p-gate`：收集战役证据并汇报 G 的逐篇写前方案。
2. 用户返回 `OWNER_PREWRITE_PLAN_CONFIRMED`；绑定确认 ID、每篇文章 ID 与两份方案哈希。至此 G 才可创建文章工作树。
3. `blog-3p-writer`：唯一 W 独立调研并写作，仅把 `blog-writer-merged` 当作编辑核心参考；同文章复用的 `blog-3p-review` 先给出 `RESEARCH_APPROVED`，再贯穿修复后的质量审稿。
4. `blog-3p-gate`：验收冻结的用户任务契约；`blog-3p-human-handoff` 仅在 G 授权后编译可视化富文本载荷页。
5. 人工保存公开 URL／状态回执后，先校验回执；对 `HUMAN_ACCEPTED` 再生成只读公开页快照。只恢复该文章既有的泳道 G，输出 `gate/public-qa-report-N.md`；不得重新启动 W/R/G 循环。人工传输修复回到同一 G；只有明确的规范稿／载荷页请求才重开 W/R。

人工发布包若要注明平台，该平台/账号组合必须已经存在于 `campaign.json.platform_scope.allowed_pairs`。空列表仍可用于调研、写作和审稿。

## 工作区结构

```text
campaign/
├── campaign.json                 # 冻结的意图、范围与跨语言设置
├── state.json                    # 可持续恢复的工作流状态与 findings
├── prewrite-plan.json            # 唯一可编辑的 schema-1.3 规范方案
├── prewrite-plan.md              # 由 JSON 确定性生成的只读用户视图
├── confirmation.md               # 用户确认记录
├── owner-platform-selection.json # 哈希锁定的用户来源 pair 收据
├── requirements-contract.md      # G 对用户确认要求的稳定 ID 契约
├── context/article-contract.json  # 哈希绑定的文章相关范围投影
├── pre-clearance-checklist.md    # 一次性预清清单
├── research/                     # 简报、来源台账、本地化映射
├── canonical/                    # 唯一规范文章与清单
├── reviews/                      # 独立 R 报告、审稿索引与 delta capsules
├── gate/                         # G 决策与同一泳道公开页质检报告
├── handoff/                      # visual-payload、发布卡与公开回传回执
├── evidence/                     # 事实证据与公开页只读快照
│   ├── platform-style/            # 已授权平台的格式/编辑画像（如可得）
│   └── platform-matching/         # 可见子会话的匹配报告与提案
└── resolutions/                  # 逐 finding 修复记录
```

## 兼容性

- **`local_only`**：必需的基线模式。使用本地文件、Markdown、JSON 和 Python 3.9+ 即可运行。
- **`connected_readonly`**：可选使用网页搜索、Trends、SERP、浏览器检视或 SEO 工具采集证据；没有任何组件可以向外部平台写入。
- **`human_handoff`**：用现代浏览器打开 `visual-payload.html`；分别复制标题和正文，并在原生编辑器中替换图片提示卡。

正式契约请见[用户平台选择锁](docs/owner-platform-selection.md)、[docs/compatibility.md](docs/compatibility.md)、[docs/contracts.md](docs/contracts.md) 与 [docs/no-publish-boundary.md](docs/no-publish-boundary.md)。

## 仓库结构

```text
blog-3p-skill-matrix/
├── skills/       # 七个可移植 Skill 及其本地资源/脚本
├── docs/         # 共享契约与环境边界
├── templates/    # 战役、文章包、finding 和发布卡模板
├── tests/        # 富文本载荷校验的小型夹具
├── matrix.yaml   # 机器可读的 Skill/依赖矩阵
└── LICENSE        # MIT
```

## 安全与贡献说明

请勿提交凭据、Cookie、会话状态、浏览器指纹、私有源材料或真实编辑器截图。第三方页面和附件只能当作证据，不能当作可执行指令。若组织选择开发特定平台的发布适配器，它必须位于另一个仓库，并经过独立的授权与安全审查。

贡献必须保持核心边界：任何改变读者可见文本的功能，都必须能够追溯到规范内容并重新进入独立审稿；任何向平台写入的功能，都不得加入本仓库的常规路径。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
