# 归因报告输出格式

> 报告是交付物。固定结构，让不同归因之间可比。Markdown 为主（scripts 同时产出 JSON 便于程序消费）。

## 报告结构

```markdown
# 绩效归因报告

## 0. 口径声明
- 基准：沪深300 / 中证500 / ...（可比性确认）
- 行业映射：申万一级（或未提供 → Brinson 退化为单层）
- 因子模型：风格 + 行业（或未提供 → 层3 降级）
- 成本/收益口径：净收益 / 算术超额 / 无风险利率 0

## 1. 总体表现（层1 Alpha/Beta/择时）
| 指标 | 值 |
|---|---|
| 组合收益 r_p | ... |
| 基准收益 r_b | ... |
| 超额 | ... |
| β | ... |
| 年化 Jensen's Alpha | ... |
| 择时项（Treynor-Mazuy） | ... |

## 2. Brinson 归因（层2）
| 行业 | 组合权重 | 基准权重 | 配置效应 | 选择效应 | 交互效应 | 合计 |
|---|---|---|---|---|---|---|
| ... | | | | | | |
| **总计** | | | Σ配置 | Σ选择 | Σ交互 | Σ（应≈超额） |
- 对账：Σ(配置+选择+交互) − 超额 = {residual}（应 < 1e-6）

## 3. 因子收益归因（层3）
| 因子 | 暴露差 | 因子收益累计 | 收益贡献 |
|---|---|---|---|
| SIZE | | | |
| ... | | | |
| **Alpha 残差** | | | |
- 对账：Σ贡献 + Alpha残差 − 超额 = {residual}

## 4. 结论
一句话：超额主要来自哪里（配置/选择/哪个因子/Alpha）→ 限制与口径提醒。

## 5. 合规声明
仅供量化研究、教育与方法论参考，不构成投资建议。
```

## scripts 输出契约

`attribution_cli.py --out out/` 产出：

- `out/attribution_report.md` —— 人类可读（如上结构）
- `out/attribution_report.json` —— 机器可读：

```json
{
  "schema": "performance-attribution/1",
  "generated_at": "2026-08-01",
  "scope": { "benchmark": "...", "industry_map": "...", "factor_model": "..." },
  "layer1": { "r_p": ..., "r_b": ..., "excess": ..., "beta": ..., "alpha_ann": ..., "timing": ... },
  "layer2": { "industries": [{"industry": "...", "allocation": ..., "selection": ..., "interaction": ...}], "total": {...}, "recon_residual": ... },
  "layer3": { "factors": [{"factor": "...", "contribution": ...}], "alpha_residual": ..., "recon_residual": ... },
  "reconciled": true
}
```

## 写作纪律

1. **口径先行**：报告开头必须有 0 口径声明，否则读者无法判断数字含义。
2. **对账必附**：每层给出对账残差，<1e-6 标 ✅，否则标 ⚠️ 并说明原因。
3. **分层结论**：结论把「收益从哪来」讲成 1-2 句话，不堆数字。
4. **合规兜底**：所有报告以合规声明收尾。
