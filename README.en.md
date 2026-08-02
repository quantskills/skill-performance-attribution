# skill-performance-attribution

[简体中文](./README.md) | [English](./README.en.md)

**A-share quant strategy performance attribution**: decomposes portfolio returns into Alpha/Beta/timing, Brinson allocation/selection/interaction, style & industry factor-return contributions, and residual Alpha — emitted as a reconciled AttributionReport.

`role: skill` `output: AttributionReport` `paradigm: portfolio-level attribution` `license: GPL-3.0`

---

`skill-performance-attribution` is a **performance (return) attribution skill** from PandaAI Quant Skills (the QUANTSKILLS org). Given portfolio returns/weights and a benchmark, it performs **three-layer attribution** answering "where do returns actually come from" — market, industry allocation, stock selection, or style factor exposures.

It is **not risk attribution**: `skill-risk-model` decomposes portfolio *volatility* into factor vs specific risk (Σ = XFXᵀ+Δ); this skill decomposes *returns*. The two complement each other, and this skill can directly consume the factor returns estimated by risk-model's cross-sectional WLS.

## 🎯 What problem does this solve

- Is the excess from industry allocation or stock selection? → **Brinson attribution**
- Which style factor exposure drives the excess, and how much Alpha is left? → **Factor-return attribution**
- How much market exposure does the portfolio have? What is the active Alpha? → **Alpha/Beta/timing decomposition**

## Three attribution layers

| Layer | Method | Output | Module |
|---|---|---|---|
| 1 | Alpha/Beta/timing | β, Jensen's Alpha, market excess, timing (Treynor-Mazuy) | `alpha_beta` |
| 2 | Brinson-Fachler | per-industry allocation/selection/interaction + reconciliation | `brinson` |
| 3 | Factor-return attribution | per style/industry factor contribution + residual Alpha + reconciliation | `factor_attribution` |

Every layer reports a **reconciliation residual** (decomposition sum vs actual excess; < 1e-6 marked ✅).

## ⚡ Workflow (standard 6 steps)

```
1. Clarify inputs: portfolio returns/weights + benchmark returns; pick scope & benchmark
2. Declare conventions: industry map, factor model, costs
3. Layer 1 Alpha/Beta/timing: OLS on benchmark returns
4. Layer 2 Brinson: allocation/selection/interaction by industry; reconcile
5. Layer 3 factor attribution: estimate factor returns (or read skill-risk-model output) → exposure diff × factor returns → Alpha residual; reconcile
6. Emit a unified attribution report (Markdown + JSON)
```

## 🚀 Quick start

```bash
# Install (platforms with a skills directory: Claude Code / OpenClaw / Codex)
cp -r skill-performance-attribution ~/.claude/skills/skill-performance-attribution

# Run attribution (optional; needs pandas + numpy)
python -m pip install -r scripts/requirements.txt
python scripts/attribution_cli.py \
  --portfolio portfolio_ret.csv --benchmark benchmark_ret.csv \
  --weights weights.csv --benchmark-weights bench_weights.csv \
  --symbol-returns symbol_ret.csv --industry-map industry_map.csv \
  --factor-exposures exposures.csv --factor-returns factor_ret.csv --out out/
```

```text
Trigger prompt 1: This portfolio beat CSI300 — attribute the excess to allocation vs selection.
Trigger prompt 2: Decompose my strategy returns into Alpha and factor-exposure contributions.
Trigger prompt 3: Analyze excess over CSI500 with a Brinson attribution.
```

## 🗃️ Inputs

| Input | Required | Format |
|---|---|---|
| `--portfolio` / `--benchmark` | ✅ | daily returns `date, ret` |
| `--weights` / `--benchmark-weights` | Layer 2 | portfolio / benchmark weights |
| `--symbol-returns` | Layer 2/3 | per-symbol returns `date×symbol` |
| `--industry-map` | Layer 2 | `symbol, industry` |
| `--factor-exposures` / `--factor-returns` | Layer 3 | portfolio exposures / factor returns (can come from skill-risk-model) |
| `--symbol-exposures` + `--cap-weights` | Layer 3 WLS | internal cross-sectional WLS when factor returns are absent |

**Missing inputs never lead to guessing**: no industry map → Brinson degrades to a single layer; no factor exposures/returns → Layer 3 degrades.

## 📦 Layout

```text
skill-performance-attribution/
├── SKILL.md                        # Core protocol (3 layers + 6-step workflow)
├── references/                     # attribution-layers / brinson / factor / alpha-beta / report / source_boundary
├── scripts/
│   ├── attribution_cli.py          # Attribution CLI entry
│   ├── self_test.py                # Synthetic self-check with reconciliation
│   ├── report.py                   # Markdown / JSON rendering
│   └── attribution/                # alpha_beta / brinson / factor_attribution / base
└── agents/                         # openai.yaml / cursor-rule.mdc / portable-loader
```

## Relationship to existing skills (complementary)

| Existing skill | Its boundary | What this adds |
|---|---|---|
| `skill-risk-model` (05) | **Risk** attribution (where volatility comes from) | **Return** attribution; consumes its factor returns |
| `skill-backtest` (05) | Defines the backtest protocol | Analyzes the sources of backtest results |
| `skill-portfolio-checkup` (03) | Static portfolio health snapshot | Dynamic return decomposition |
| `skill-backtest-assumption-audit` (07) | Audits backtest assumption quality | Explains results that pass the audit |

## 📐 Core constraints

| Constraint | Note |
|---|---|
| 🧮 Reconciliation | Every layer's decomposition must sum ≈ actual excess (< 1e-6); otherwise it is a bug |
| 🎯 Conventions first | Benchmark, industry map, factor model, costs must be declared before computing |
| 📉 Degrade, don't guess | Missing inputs → that layer degrades; never invent exposures |
| 🚫 Facts, not advice | Outputs attribution structure; no investment advice |

## ⚠️ Disclaimer

Research/education only. This repository ships no market data; portfolios/benchmarks/weights/industry maps are user-provided, and the user is responsible for data legality and licensing. Attribution results reflect only statistical decomposition over the given materials + historical data, do not represent future performance, and do not constitute investment advice.

## 📜 License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS Community

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI community QR code" width="220">
  <br>
  <sub>Scan to join the PandaAI community for QUANTSKILLS skills, agent workflows, and quant research.</sub>
</div>
