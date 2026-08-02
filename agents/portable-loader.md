# Portable Loader（无原生 skill 机制的平台）

在 OpenAI Assistants / Codex / Cursor / OpenClaw 等未原生支持本 skill 元数据的平台上，直接加载以下内容即可获得同等能力：

1. **读取 `SKILL.md`**：核心协议（三层归因、标准 6 步工作流、对账纪律、合规声明）。这是行为契约，必须完整加载。
2. **按需加载 `references/`**：
   - `attribution-layers.md` — 三层归因总览与方法选型
   - `brinson.md` — Brinson 公式/交互口径/行业映射
   - `factor-attribution.md` — 截面 WLS、Alpha 残差、与 skill-risk-model 互操作
   - `alpha-beta-timing.md` — CAPM 回归、Jensen's Alpha、择时
   - `report-format.md` — 报告输出契约
   - `source_boundary.md` — 数据来源与边界
3. **可选运行 `scripts/`**：`attribution_cli.py` 做归因；`self_test.py` 跑通自检（含对账校验）。依赖 pandas + numpy（见 `scripts/requirements.txt`）。

## 最小加载清单

```
SKILL.md
references/attribution-layers.md
references/report-format.md
```

其余 references 在对应层被触发时再读取。
