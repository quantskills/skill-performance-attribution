# Alpha / Beta / 择时分解（层1）

> 组合收益对基准收益回归，把表现拆成市场暴露（β）、主动超额（Alpha）与择时贡献。

## 方法

**CAPM 式 OLS**（日频）：

```
R_p,t − r_f,t = α + β·(R_m,t − r_f,t) + ε_t
```

- `β`：市场暴露（回归斜率）
- `α`：Jensen's Alpha（日频截距，年化输出）
- 超额 = `R_p − R_m`（无风险利率可设 0，A 股常用年化近似）

**择时（可选，Treynor-Mazuy）**：

```
R_p,t = α' + β·R_m,t + γ·R_m,t² + ε_t
```

- `γ > 0` 表示在市场上涨时暴露更大（择时贡献为正）

## 输出（脚本 `attribution/alpha_beta.py`）

| 指标 | 说明 |
|---|---|
| `beta` | 市场暴露 |
| `alpha_ann` | 年化 Jensen's Alpha |
| `r_p` / `r_b` | 区间总收益（算术） |
| `excess` | 超额收益 |
| `timing` | Treynor-Mazuy 择时项（可选） |
| `r2` | 回归拟合优度 |

## 数据要求

- `--portfolio`：组合日收益序列（`date, ret`）
- `--benchmark`：基准日收益序列（`date, ret`）
- 缺一 → 层1 降级 INFO。

## 对账

`α + β·mean(R_m) ≈ mean(R_p)`；年化输出标注口径（252 日复利/算术）。

## 口径说明

- 超额收益：**算术**（`R_p − R_m`）为默认；如用几何需标注。
- 无风险利率默认 0，A 股短期研究常用；如有实际 rf 序列可传入。
