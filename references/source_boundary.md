# 数据来源与边界

> 对齐 QUANTSKILLS 社区规则 §8：**本 skill 不附带任何市场数据**，归因基于使用者提供的材料。

## 数据从哪来

| 材料 | 来源 | 说明 |
|---|---|---|
| 组合收益 / 权重 | 使用者提供（回测/实盘导出），或经 pandadata | 归因对象 |
| 基准收益 | 使用者提供，或 pandadata 指数行情 | 可选 |
| 行业映射 | pandadata 行业分类接口 / 使用者文件（symbol→行业） | Brinson 必需 |
| 因子暴露 / 因子收益 | 使用者提供，或 `skill-risk-model` 输出 | 层3 必需 |
| 收益面板（自算因子收益用） | pandadata `get_stock_daily` 导出 | 内置 WLS 路径需要 |

## Pandadata 如何供数（推荐路径）

- 组合与基准日收益：导出为 `date, ret` CSV。
- 行业分类：pandadata 行业字段（`sector_code_name` 等）→ `symbol, industry` CSV。
- 因子暴露：组合暴露矩阵（date × factor）导出；因子收益可直接用 `skill-risk-model` 的 `model.json` / `factor_returns.csv`。
- 收益面板：`panda_data.get_stock_daily(...)` 导出长表（date, symbol, close...）。

## 边界声明

- **本 skill 不做行情拉取、不做回测重跑**：只有使用者给数据时才能做归因。
- **数据合法性与许可由使用者负责**。
- **缺输入 → 对应层降级**：无行业映射 → Brinson 退化为单层；无因子暴露/收益 → 层3 降级 INFO；绝不编造暴露硬算。
- **合成数据自检**（`scripts/self_test.py`）仅用于演示与验证 skill 能力，不代表任何真实市场结论。
