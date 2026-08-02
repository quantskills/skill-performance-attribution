"""层2：Brinson-Fachler 归因。

单期截面近似（样本平均权重 + 期间累计收益，算术口径）：
  配置效应   = Σ_i (w_p,i − w_b,i) × (r_b,i − r_b)
  选择效应   = Σ_i w_b,i × (r_p,i − r_b,i)
  交互效应   = Σ_i (w_p,i − w_b,i) × (r_p,i − r_b,i)
三者和恒等于组合超额 r_p − r_b（Σw_p=Σw_b=1 时）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import LayerResult


def _avg_weights(df: pd.DataFrame) -> pd.Series:
    w = df.mean(axis=0)
    return w / w.sum()


def _industry_rows(w_sym: pd.Series, cumret: pd.Series, ind_map: dict) -> list[tuple[str, float, float]]:
    """按行业聚合：(industry, 权重, 加权期间收益)。"""
    ind = pd.Series(ind_map).reindex(w_sym.index)
    rows = []
    for i in sorted(pd.unique(ind.dropna())):
        m = (ind == i) & w_sym.notna() & cumret.notna()
        if not m.any():
            continue
        wi = float(w_sym[m].sum())
        ri = float((w_sym[m] * cumret[m]).sum() / wi) if wi > 0 else 0.0
        rows.append((i, wi, ri))
    return rows


def _portfolio_return(w_sym: pd.Series, cumret: pd.Series) -> float:
    return float((w_sym * cumret).sum())


def compute(ctx) -> LayerResult:
    weights, sym_ret = ctx.weights, ctx.symbol_returns
    if weights is None or sym_ret is None:
        return LayerResult("brinson", degraded=True, note="缺少 weights 或 symbol-returns，无法做 Brinson 归因。")

    cumret = sym_ret.sum(axis=0)  # 算术期间收益（简单加总），与超额口径一致
    w_p_sym = _avg_weights(weights)

    if ctx.industry_map is None:
        r_p = _portfolio_return(w_p_sym, cumret)
        if ctx.benchmark_weights is None:
            return LayerResult("brinson", degraded=True,
                               note="缺少 industry-map 与 benchmark-weights，无法做 Brinson 拆分。")
        w_b_sym = ctx.benchmark_weights / ctx.benchmark_weights.sum()
        r_b = _portfolio_return(w_b_sym, cumret)
        return LayerResult("brinson", data={
            "industries": [],
            "total": {"allocation": 0.0, "selection": r_p - r_b, "interaction": 0.0,
                      "excess": r_p - r_b, "r_p": r_p, "r_b": r_b},
            "basis": "算术口径、未按行业拆分（缺 industry-map）；仅选择效应 = 组合−基准",
        }, recon_residual=0.0, note="缺少 industry-map，Brinson 退化为单层。")

    if ctx.benchmark_weights is None:
        return LayerResult("brinson", degraded=True,
                           note="缺少 benchmark-weights，无法拆分配置/交互效应；请补充基准权重。")

    w_b_sym = ctx.benchmark_weights / ctx.benchmark_weights.sum()

    rows_p = _industry_rows(w_p_sym, cumret, ctx.industry_map)
    rows_b = _industry_rows(w_b_sym, cumret, ctx.industry_map)
    w_p_by = {i: w for i, w, _ in rows_p}
    r_p_by = {i: r for i, _, r in rows_p}
    w_b_by = {i: w for i, w, _ in rows_b}
    r_b_by = {i: r for i, _, r in rows_b}

    r_p = _portfolio_return(w_p_sym, cumret)
    r_b = _portfolio_return(w_b_sym, cumret)

    industries = []
    alloc = sel = inter = 0.0
    for i in sorted(set(w_p_by) | set(w_b_by)):
        w_p, r_pi = w_p_by.get(i, 0.0), r_p_by.get(i, 0.0)
        w_b, r_bi = w_b_by.get(i, 0.0), r_b_by.get(i, 0.0)
        a = (w_p - w_b) * (r_bi - r_b)
        s = w_b * (r_pi - r_bi)
        x = (w_p - w_b) * (r_pi - r_bi)
        alloc += a; sel += s; inter += x
        industries.append({"industry": i, "w_p": w_p, "w_b": w_b,
                           "allocation": a, "selection": s, "interaction": x, "total": a + s + x})

    excess = r_p - r_b
    total = alloc + sel + inter
    recon = total - excess

    return LayerResult("brinson", data={
        "industries": industries,
        "total": {"allocation": alloc, "selection": sel, "interaction": inter,
                  "excess": excess, "r_p": r_p, "r_b": r_b},
        "basis": "算术口径、样本平均权重、期间简单加总收益；交互单独列示",
    }, recon_residual=float(recon))
