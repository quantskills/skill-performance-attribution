# skill-performance-attribution

[简体中文](./README.md) | [English](./README.en.md)

**A股量化策略绩效归因**：把组合收益拆解为「Alpha/Beta/择时 + Brinson 配置/选择/交互 + 风格与行业因子收益贡献 + Alpha 残差」，输出统一归因报告并做分解对账。

`role: skill` `output: AttributionReport` `paradigm: portfolio-level attribution` `license: GPL-3.0`

---

`skill-performance-attribution` 是 PandaAI Quant Skills（QUANTSKILLS 组织）提供的**绩效归因（收益归因）Skill**。给定组合收益/权重与基准，它做**三层综合归因**，回答「收益到底从哪来」——是市场、行业配置、个股选择，还是风格因子暴露。

它**不是风险归因**：`skill-risk-model` 已把组合**波动**拆成因子风险 vs 特异风险（Σ = XFXᵀ+Δ），本 skill 拆的是**收益**，两者互补，且本 skill 可直接复用其截面 WLS 估出的因子收益。

## 🎯 这个 Skill 解决什么问题

- 超额是行业配置带来的，还是个股选择带来的？→ **Brinson 归因**
- 超额来自哪个风格因子暴露？还剩多少 Alpha？→ **因子收益归因**
- 组合有多大的市场暴露？主动 Alpha 是多少？→ **Alpha/Beta/择时分解**

## 三层归因

| 层 | 方法 | 输出 | 脚本 |
|---|---|---|---|
| 1 | Alpha/Beta/择时 | β、Jensen's Alpha、市场超额、择时项（Treynor-Mazuy） | `alpha_beta` |
| 2 | Brinson-Fachler | 每行业 配置/选择/交互 贡献 + 对账 | `brinson` |
| 3 | 因子收益归因 | 每风格/行业因子收益贡献 + Alpha 残差 + 对账 | `factor_attribution` |

每层输出都附**对账残差**（分解之和 vs 实际超额，< 1e-6 标记 ✅）。

## ⚡ 归因流程（标准 6 步）

```
1. 明确对象：组合收益/权重 + 基准收益，选定范围与基准
2. 声明口径：行业映射、因子模型、成本
3. 层1 Alpha/Beta/择时：OLS 回归基准收益
4. 层2 Brinson：按行业拆配置/选择/交互，对账
5. 层3 因子归因：估因子收益（或读 skill-risk-model 输出）→ 暴露差×因子收益 → Alpha 残差，对账
6. 输出统一归因报告（Markdown + JSON）
```

## 🚀 快速开始

```bash
# 安装（Claude Code / OpenClaw / Codex 等支持 skills 目录的平台）
cp -r skill-performance-attribution ~/.claude/skills/skill-performance-attribution

# 运行归因（可选，需 pandas + numpy）
python -m pip install -r scripts/requirements.txt
python scripts/attribution_cli.py \
  --portfolio portfolio_ret.csv --benchmark benchmark_ret.csv \
  --weights weights.csv --benchmark-weights bench_weights.csv \
  --symbol-returns symbol_ret.csv --industry-map industry_map.csv \
  --factor-exposures exposures.csv --factor-returns factor_ret.csv --out out/
```

```text
触发示例 prompt 1：这个组合跑赢沪深300，帮我归因一下超额来自行业配置还是选股。
触发示例 prompt 2：把我的策略收益拆成 Alpha 和因子暴露贡献，输出归因报告。
触发示例 prompt 3：分析组合相对中证500的超额，做 Brinson 归因。
```

## 🗃️ 输入要求

| 输入 | 必填 | 格式 |
|---|---|---|
| `--portfolio` / `--benchmark` | ✅ | 日收益 `date, ret` |
| `--weights` / `--benchmark-weights` | 层2 | 组合/基准权重 |
| `--symbol-returns` | 层2/3 | 个股收益面板 `date×symbol` |
| `--industry-map` | 层2 | `symbol, industry` |
| `--factor-exposures` / `--factor-returns` | 层3 | 组合暴露 / 因子收益（可来自 skill-risk-model） |
| `--symbol-exposures` + `--cap-weights` | 层3 自算 | 缺因子收益时内置截面 WLS 自算 |

**缺输入不臆测**：无行业映射 → Brinson 退化为单层；无因子暴露/收益 → 层3 降级提示。

## 📦 目录结构

```text
skill-performance-attribution/
├── SKILL.md                        # 核心协议（三层归因 + 6 步工作流）
├── references/                     # attribution-layers / brinson / factor / alpha-beta / report / source_boundary
├── scripts/
│   ├── attribution_cli.py          # 归因 CLI 入口
│   ├── self_test.py                # 合成数据自检（含对账校验）
│   ├── report.py                   # Markdown / JSON 报告渲染
│   └── attribution/                # alpha_beta / brinson / factor_attribution / base
└── agents/                         # openai.yaml / cursor-rule.mdc / portable-loader
```

## 与既有 skill 的关系（互补不重复）

| 既有 skill | 它的边界 | 本 skill 补什么 |
|---|---|---|
| `skill-risk-model`（05） | **风险**归因（波动从哪来） | **收益**归因（收益从哪来）；复用其因子收益输出 |
| `skill-backtest`（05） | 定义回测协议 | 分析回测结果的来源 |
| `skill-portfolio-checkup`（03） | 组合静态体检快照 | 收益的动态分解 |
| `skill-backtest-assumption-audit`（07） | 审计回测假设质量 | 对合格结果做归因解释 |

## 📐 核心约束

| 约束 | 说明 |
|---|---|
| 🧮 分解对账 | 每层分解之和必须 ≈ 实际超额（< 1e-6），对不上就是 bug |
| 🎯 口径先行 | 基准、行业映射、因子模型、成本口径先声明再计算 |
| 📉 缺料降级 | 缺输入 → 对应层降级，绝不编造暴露硬算 |
| 🚫 只述不荐 | 输出归因结构，不构成投资建议 |

## ⚠️ 免责声明

本仓库仅作量化研究方法层面的归因工具。不附带任何市场数据；组合/基准/权重/行业映射由使用者提供，数据合法性与许可由使用者负责。归因结果仅反映对给定材料 + 历史数据的统计分解，不代表未来表现，不构成任何投资建议。

## 📜 License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
