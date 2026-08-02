"""报告渲染：把三层归因结果渲染为 Markdown 与 JSON。

格式契约见 references/report-format.md。
"""
from __future__ import annotations

import datetime

from attribution.base import LayerResult


def _fmt(x, nd=4):
    if x is None:
        return "—"
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    return f"{f:.{nd}f}"


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _recon_line(label: str, residual: float | None) -> str:
    if residual is None:
        return f"- 对账 {label}：—"
    ok = abs(residual) < 1e-6
    return f"- 对账 {label}：{_fmt(residual)}{' ✅' if ok else ' ⚠️ 未对账'}"


def render_markdown(layers: dict[str, LayerResult], ctx, generated_at: str) -> str:
    lines = ["# 绩效归因报告", ""]
    lines.append(f"> 生成：{generated_at}　口径：算术超额、无风险利率 0、日频 252 年化")
    lines.append("")

    l1 = layers.get("alpha_beta")
    l2 = layers.get("brinson")
    l3 = layers.get("factor_attribution")

    lines.append("## 0. 口径声明")
    lines.append("")
    lines.append(f"- 基准：`{ctx.benchmark_label or '未指定'}`　归因范围：`{ctx.scope}`")
    lines.append(f"- 行业映射：{'有' if ctx.industry_map else '缺（Brinson 退化为单层）'}　因子模型：{'有' if (ctx.factor_exposures is not None) else '缺（层3 降级）'}")
    lines.append("")

    # 层1
    lines.append("## 1. 总体表现（Alpha/Beta/择时）")
    lines.append("")
    if l1 and not l1.degraded:
        d = l1.data
        lines.append("| 指标 | 值 |")
        lines.append("|---|---|")
        lines.append(f"| 组合收益 r_p | {_fmt(d.get('r_p'))} |")
        lines.append(f"| 基准收益 r_b | {_fmt(d.get('r_b'))} |")
        lines.append(f"| 超额 | {_fmt(d.get('excess'))} |")
        lines.append(f"| β | {_fmt(d.get('beta'))} |")
        lines.append(f"| 年化 Jensen's Alpha | {_fmt(d.get('alpha_ann'))} |")
        lines.append(f"| 择时项（Treynor-Mazuy γ） | {_fmt(d.get('timing_gamma'))} |")
        lines.append("")
    else:
        lines.append(f"_（降级：{l1.note if l1 else '缺数据'}）_")
        lines.append("")

    # 层2
    lines.append("## 2. Brinson 归因")
    lines.append("")
    if l2 and not l2.degraded:
        d = l2.data
        lines.append("| 行业 | 组合权重 | 基准权重 | 配置 | 选择 | 交互 | 合计 |")
        lines.append("|---|---|---|---|---|---|---|")
        for row in d.get("industries", []):
            lines.append(f"| {row['industry']} | {_fmt(row['w_p'])} | {_fmt(row['w_b'])} | {_fmt(row['allocation'])} | "
                         f"{_fmt(row['selection'])} | {_fmt(row['interaction'])} | {_fmt(row['total'])} |")
        t = d.get("total", {})
        lines.append(f"| **总计** | | | {_fmt(t.get('allocation'))} | {_fmt(t.get('selection'))} | "
                     f"{_fmt(t.get('interaction'))} | {_fmt(t.get('excess'))} |")
        lines.append("")
        lines.append(_recon_line("Brinson（Σ效应 − 超额）", l2.recon_residual))
        lines.append("")
        lines.append(f"_口径：{d.get('basis', '')}_")
    else:
        lines.append(f"_（降级：{l2.note if l2 else '缺数据'}）_")
    lines.append("")

    # 层3
    lines.append("## 3. 因子收益归因")
    lines.append("")
    if l3 and not l3.degraded:
        d = l3.data
        lines.append("| 因子 | 收益贡献 |")
        lines.append("|---|---|")
        for row in d.get("factors", []):
            lines.append(f"| {row['factor']} | {_fmt(row['contribution'])} |")
        lines.append(f"| **Alpha 残差** | {_fmt(d.get('alpha_residual'))} |")
        lines.append(f"| **超额合计** | {_fmt(d.get('excess_total'))} |")
        lines.append("")
        lines.append(_recon_line("因子归因（Σ贡献 + Alpha − 超额）", l3.recon_residual))
        lines.append("")
        lines.append(f"_因子收益来源：{d.get('factor_return_source', '')}；口径：{d.get('basis', '')}_")
    else:
        lines.append(f"_（降级：{l3.note if l3 else '缺数据'}）_")
    lines.append("")

    lines.append("## 4. 结论")
    lines.append("")
    summary_parts = []
    if l1 and not l1.degraded:
        summary_parts.append(f"超额 {_fmt(l1.data.get('excess'))}，β={_fmt(l1.data.get('beta'))}，年化 Alpha={_fmt(l1.data.get('alpha_ann'))}")
    if l2 and not l2.degraded:
        t = l2.data.get("total", {})
        summary_parts.append(f"Brinson：配置 {_fmt(t.get('allocation'))} / 选择 {_fmt(t.get('selection'))} / 交互 {_fmt(t.get('interaction'))}")
    if l3 and not l3.degraded:
        summary_parts.append(f"因子归因：Σ贡献 {_fmt(sum(r['contribution'] for r in l3.data.get('factors', [])))} / Alpha残差 {_fmt(l3.data.get('alpha_residual'))}")
    lines.append("；".join(summary_parts) if summary_parts else "_各层均降级，无结论。_")
    lines.append("")
    lines.append("## 5. 合规声明")
    lines.append("")
    lines.append("仅供量化研究、教育与方法论参考，不构成投资建议。归因结果仅反映对给定材料 + 历史数据的统计分解，不代表未来表现。")
    lines.append("")
    return "\n".join(lines)


def render_json(layers: dict[str, LayerResult], ctx, generated_at: str) -> dict:
    return {
        "schema": "performance-attribution/1",
        "generated_at": generated_at,
        "scope": {"benchmark": ctx.benchmark_label, "attribution_scope": ctx.scope},
        "layer1": (layers.get("alpha_beta").to_dict() if layers.get("alpha_beta") else None),
        "layer2": (layers.get("brinson").to_dict() if layers.get("brinson") else None),
        "layer3": (layers.get("factor_attribution").to_dict() if layers.get("factor_attribution") else None),
        "reconciled": all(
            (not l.degraded) and (l.recon_residual is not None) and abs(l.recon_residual) < 1e-6
            for l in layers.values() if l is not None
        ),
    }
