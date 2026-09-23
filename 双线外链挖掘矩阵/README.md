# 双线外链挖掘矩阵

这是一个面向 Codex 的开源外链研究 Skill 套件。它把“大规模候选发现”和“高质量文章投稿”分成两条独立筛选线，再用统一的源表、去重和工作簿规则完成交付。

本项目解决的是候选获取、筛选、去重和制表问题，不是自动群发工具，也不承诺收录、链接属性、流量或排名。

## 两条线路

| 线路 | 主要目标 | 筛选方式 |
|---|---|---|
| 批量提交线 | 尽可能扩大合法、相关、可执行的产品收录候选 | 条件宽松，允许登录、验证码、人工审核和 `nofollow`；排除正式文章、强制回链、强制徽章和明确删除风险 |
| 质量投稿线 | 寻找值得投入内容和沟通成本的编辑型机会 | 综合主题适配、准入难度和预期回报；费用不明不能视为免费 |

## Skill 矩阵

| Skill | 职责 | 主要产物 |
|---|---|---|
| `backlink-expansion-matrix` | 冻结范围、路由阶段、检查交接和验收状态 | 项目路线、阶段边界、验收结论 |
| `backlink-source-prep` | 整理自然搜索竞品、反向链接差异、引荐域名和公开清单 | 源文件登记、合并候选、排除表、优先候选、统计报告 |
| `backlink-batch-expansion` | 筛选工具目录、产品导航、创业项目库、社区资料页和资源推荐页 | 批量线可执行池、备用池、排除表 |
| `backlink-quality-expansion` | 筛选文章投稿、行业媒体、专家贡献和编辑型资源页 | 质量线免费候选、付费或待确认候选、排除表 |
| `backlink-workbook-delivery` | 历史去重、跨线路去重、批次冻结、制表和质量检查 | 免费/付费工作簿、去重记录、质量检查报告 |

## 工作流

```text
目标品牌与交付要求
        │
        ▼
自然搜索竞品与其他参考来源
        │
        ▼
竞品反向链接差异／引荐域名／历史表／公开资源
        │
        ▼
标准化、合并、排除噪声、生成优先候选
        │
        ├───────────────┐
        ▼               ▼
批量提交线          质量投稿线
        │               │
        └───────┬───────┘
                ▼
      历史去重与跨线路去重
                │
                ▼
      免费／付费执行工作簿
```

## 安装

将 `skills/` 下需要的技能目录复制到 Codex 可发现的技能目录。完整流程建议安装全部五个：

```sh
cp -R 双线外链挖掘矩阵/skills/* ~/.codex/skills/
```

安装后可直接调用：

```text
$backlink-expansion-matrix
$backlink-source-prep
$backlink-batch-expansion
$backlink-quality-expansion
$backlink-workbook-delivery
```

## 校验

每个 Skill 都可以使用 Codex 的 `quick_validate.py` 校验。随包脚本仅使用 Python 标准库：

```sh
python3 skills/backlink-source-prep/scripts/audit_semrush_exports.py \
  --input-dir /path/to/semrush-exports \
  --report /path/to/source-audit.json

python3 skills/backlink-batch-expansion/scripts/validate_candidate_pool.py \
  --input /path/to/candidate-pool.csv

python3 skills/backlink-workbook-delivery/scripts/validate_delivery_csv.py \
  --input /path/to/delivery.csv
```

## 数据边界

- 仓库只包含工作流、规则、模板和校验脚本，不包含公司的 Semrush 原始导出、历史投递数据或账号信息。
- Semrush、竞品外链和公开清单只是候选来源，不证明站点可投递。
- 候选表、执行表、表单页面和 HTTP 200 均不证明已经提交或收录。
- 未经明确授权，Skill 不注册、不登录、不付款、不提交，也不联系站方。
- 费用未说明不等于免费；“已导出”不等于“已提交”。

## 目录结构

```text
双线外链挖掘矩阵/
├── README.md
├── LICENSE
├── matrix.yaml
└── skills/
    ├── backlink-expansion-matrix/
    ├── backlink-source-prep/
    ├── backlink-batch-expansion/
    ├── backlink-quality-expansion/
    └── backlink-workbook-delivery/
```

## License

[MIT](LICENSE)
