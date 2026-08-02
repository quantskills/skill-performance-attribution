# 因子收益归因（层3）

> 把组合超额拆成 **风格因子收益 × 暴露差** 与 **行业贡献** 的加总，剩下的是 **Alpha 残差**。研究视角，方法对齐 `skill-risk-model` 的截面 WLS。

## 模型

多因子模型：

```
r_i,t = Σ_k X_i,k,t·f_k,t + u_i,t        (逐日截面回归，估计因子收益 f_k,t)
```

- `X_i,k,t`：股票 i 在因子 k 的暴露（风格因子 + 行业哑变量）
- `f_k,t`：因子收益（截面 WLS，权重 ∝ √市值，方法同 skill-risk-model 的 `cross_section_reg.py`）
- `u_i,t`：特异收益

## 组合超额分解

```
r_p,t − r_b,t = Σ_k (X_p,k,t − X_b,k,t)·f_k,t + α_t + 特异项
```

- `X_p,k,t`：组合在因子 k 的暴露；`X_b,k,t`：基准暴露
- `α_t`：Alpha 残差（截距/加总残差）
- **贡献** = 暴露差 × 因子收益，逐因子/逐行业累计

## 与 skill-risk-model 的互操作

- **推荐路径**：直接用 `skill-risk-model` 输出的因子收益 `factor_returns.csv`（date × factor）作为本层输入，避免重复回归、口径一致。
- **内置自算**：未提供因子收益时，`attribution/factor_attribution.py` 内置截面 WLS 估因子收益（暴露矩阵 + 收益面板 + 市值权重）。
- 两者结果应可比；混用两套因子收益会破坏对账，需声明用哪套。

## 输入

| 参数 | 内容 | 缺省行为 |
|---|---|---|
| `--factor-exposures` | 组合暴露（date × factor）或 symbol 级暴露 | 层3 降级 INFO |
| `--factor-returns` | 因子收益（date × factor），可来自 risk-model | 无则内置截面 WLS 自算（需收益面板+暴露） |
| 收益面板 | 用于自算因子收益（date × symbol） | 仅内置自算路径需要 |

## 对账

```
Σ_k 贡献_k + Alpha残差 ≈ r_p − r_b      (误差 < 1e-6)
```

对不上 → 报告标「⚠️ 未对账」，列出残差来源（暴露口径/因子收益来源不一致、特异项未计入）。

## Alpha 残差的含义

- Alpha 残差 = 组合收益中未被市场、风格、行业因子解释的部分（选股 alpha + 特异项）。
- 正的 Alpha 残差 ≠ 可持续 alpha，仅反映样本期统计；不做显著性断言（如需显著性，联动 `skill-backtest-overfit` / 数值泄露检查确认无未来函数）。
