---
name: performance-attribution
description: Use when an agent needs to attribute the returns of an A-share quant strategy or portfolio — decompose performance into Alpha/Beta/timing, Brinson allocation/selection/interaction effects by industry, and factor-return contributions (style factors, industry, residual Alpha). Outputs a unified AttributionReport (Markdown + JSON) with reconciliation checks.
quantSkills:
  organization: https://github.com/quantskills
  repository: wangofcong/skill-performance-attribution
  repository_url: https://github.com/wangofcong/skill-performance-attribution
  project_type: skill
  collection: 策略回测与交易工具
  license: GPL-3.0
  category: tooling
  tags:
  - performance-attribution
  - brinson
  - factor-attribution
  - alpha-beta
  - portfolio-analysis
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  language: zh-en
  status: stable
  validation_level: listed
  maintainer_type: community
  requires: []
  summary_zh: A股量化策略绩效归因：三层综合归因（Alpha/Beta/择时 + Brinson 配置/选择/交互 + 因子收益归因含风格行业与 Alpha 残差），输出统一归因报告并做分解对账。与 skill-risk-model（风险归因）互补。
  summary_en: A-share quant strategy performance attribution across three layers (Alpha/Beta/timing, Brinson allocation/selection/interaction, factor-return attribution with style/industry/Alpha residual), producing a reconciled AttributionReport. Complements skill-risk-model (risk attribution).
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "粘贴组合信息（持仓/收益/权重），或补充归因重点（可选）",
    "required": false
  },
  "fields": [
    {
      "key": "attribution_scope",
      "type": "select",
      "label": "归因范围",
      "default": "all",
      "options": [
        { "value": "all", "label": "三层综合（推荐）" },
        { "value": "brinson", "label": "仅 Brinson 归因" },
        { "value": "factor", "label": "仅因子收益归因" },
        { "value": "alpha_beta", "label": "仅 Alpha/Beta/择时" }
      ]
    },
    {
      "key": "benchmark",
      "type": "select",
      "label": "基准",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "000852.SH", "label": "中证1000" },
        { "value": "custom", "label": "自定义" }
      ]
    },
    {
      "key": "industry_map_path",
      "type": "textarea",
      "label": "行业映射 / 因子暴露文件路径",
      "placeholder": "可选：symbol→行业 或 因子暴露 X 的文件路径",
      "help": "缺省时 Brinson 退化为全市场一层、因子归因需提供因子收益"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请对组合做 A 股量化策略绩效归因（{{attribution_scope}}），基准 {{benchmark}}{{#industry_map_path}}，行业/因子材料见 {{industry_map_path}}{{/industry_map_path}}：完整计算 Alpha/Beta/择时、Brinson 配置/选择/交互、因子收益贡献与 Alpha 残差，做分解对账，输出统一归因报告，中文输出。"
}
```

# Performance Attribution

> 对 A 股量化策略 / 组合做**三层综合绩效归因（收益归因）**：把组合收益拆解为「Alpha / Beta / 择时」+「Brinson 配置 / 选择 / 交互」+「风格与行业因子收益贡献 + Alpha 残差」，输出统一报告并做**分解对账**。

## 核心规则

1. **三层全覆盖**：默认三层都算（层1 Alpha/Beta/择时、层2 Brinson、层3 因子收益归因），可按 `attribution_scope` 收敛
2. **分解对账**：每层分解之和必须 ≈ 实际超额（数值误差 < 1e-6），对不上就是 bug
3. **口径声明**：基准、行业映射、因子模型、成本口径必须先声明再计算
4. **归因≠荐股**：输出结构与事实归纳，不构成投资建议
5. **基准可比**：基准与策略标的错配时降级提示，不硬算

## 三层归因

| 层 | 方法 | 输出 | 数据验证脚本 |
|---|---|---|---|
| 1 | Alpha/Beta/择时 | β、Jensen's Alpha、市场超额、择时项（Treynor-Mazuy） | `alpha_beta` |
| 2 | Brinson-Fachler | 每行业 配置/选择/交互 贡献 + 对账 | `brinson` |
| 3 | 因子收益归因 | 每风格/行业因子收益贡献 + Alpha 残差 + 对账 | `factor_attribution` |

公式与口径见 `references/attribution-layers.md`（心脏文档）及各层专文。

## 工作流（标准 6 步）

```
1. 明确审计对象：组合收益 / 权重 + 基准收益，选定归因范围与基准
2. 声明口径：行业映射、因子模型、成本（无映射时 Brinson 退化为单层）
3. 层1 Alpha/Beta/择时：OLS 回归基准收益
4. 层2 Brinson：按行业算配置/选择/交互，做对账
5. 层3 因子归因：估因子收益（或读 skill-risk-model 输出）→ 暴露差×因子收益 → Alpha 残差，做对账
6. 输出统一归因报告（Markdown + JSON）
```

## 脚本用法（可运行归因）

```bash
# 三层综合归因
python scripts/attribution_cli.py \
  --portfolio portfolio_ret.csv --benchmark benchmark_ret.csv \
  --weights weights.csv --industry-map industry_map.csv \
  --factor-exposures exposures.csv --factor-returns factor_ret.csv --out out/

# 合成数据自检（含对账校验）
python scripts/self_test.py
```

**缺输入不臆测**：无行业映射 → Brinson 退化为全市场一层；无因子暴露 → 层3 降级提示，绝不用编造的暴露硬算。

## 接口映射

| 本 skill 概念 | 你的项目对应 |
|---|---|
| 组合收益 | `[date]` 日频组合净值/收益序列 |
| 基准收益 | `[date]` 基准收益序列 |
| `weights`（可选） | `[date × symbol]` 组合权重 |
| `industry-map` | `symbol → 行业` 两列 |
| `factor-exposures`（可选） | `[date × factor]` 组合暴露，或 symbol 级暴露 |
| `factor-returns`（可选） | `[date × factor]` 因子收益（可来自 skill-risk-model） |

## 按需加载

| 何时读 | 文件 |
|---|---|
| 三层方法与选型 | `references/attribution-layers.md` |
| Brinson 公式 / 交互口径 | `references/brinson.md` |
| 截面 WLS / Alpha 残差 / risk-model 互操作 | `references/factor-attribution.md` |
| Alpha/Beta/择时回归 | `references/alpha-beta-timing.md` |
| 报告输出格式 | `references/report-format.md` |
| 数据来源与边界 | `references/source_boundary.md` |

## QA 检查清单

- [ ] 层1 是否回归出 β 与 Jensen's Alpha？
- [ ] 层2 Brinson 是否给出配置/选择/交互，且三者和 ≈ 超额（对账通过）？
- [ ] 层3 因子归因 Σ贡献 + Alpha ≈ 实际超额（对账通过）？
- [ ] 基准、行业映射、因子模型口径是否已声明？
- [ ] 输出是否为统一归因报告（Markdown + JSON），不是散装数字？

## 跨工具适配

- OpenAI Codex / Assistants → `agents/openai.yaml`
- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制 → `agents/portable-loader.md`

---

## 项目边界（量化研究合规声明）

- **数据来源**：本 skill 不附带任何市场数据；组合/基准/权重/行业映射由使用者提供（可经 pandadata 导出），数据合法性与许可由使用者负责。
- **假设与参数**：归因口径（基准、行业映射、因子模型、成本）由使用者声明或取默认；结果依赖输入完整度。
- **已知限制**：不自动重跑回测；Brinson 依赖行业映射完整；因子归因依赖暴露与因子收益口径一致（缺则降级）。
- **风险边界**：归因结果仅反映对给定材料 + 历史数据的统计分解，不代表未来表现。
- **用途定位**：**仅供量化研究、教育与方法论参考**。不构成任何形式的投资建议、交易信号或获利保证。
