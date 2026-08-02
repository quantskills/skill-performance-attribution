"""层3：因子收益归因。

组合超额 = Σ_k (X_p,k − X_b,k)·f_k + Alpha 残差。
两条因子收益来源：
  1) 直接给 --factor-returns（推荐，可来自 skill-risk-model 输出）
  2) 未提供时，用 --symbol-exposures + --symbol-returns + --cap-weights
     逐日截面 WLS（权重 ∝ √市值，方法同 skill-risk-model）自算 f_t
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import LayerResult


def _wls_factor_returns(sym_exp: pd.DataFrame, ret_wide: pd.DataFrame,
                        cap_wide: pd.DataFrame | None) -> pd.DataFrame:
    """逐日截面 WLS：对每个交易日，f_t = (Xᵀ W X)⁻¹ Xᵀ W y。

    sym_exp 为长表 (date, symbol, factor, value)；ret_wide 为 date×symbol 收益；
    cap_wide 为 date×symbol 市值（权重 ∝ √市值）。
    """
    factors_sorted = sorted(sym_exp["factor"].dropna().unique())
    records = []
    for dt in sorted(sym_exp["date"].drop_duplicates()):
        if dt not in ret_wide.index:
            continue
        piv = sym_exp[sym_exp["date"] == dt].pivot_table(index="symbol", columns="factor", values="value")
        symbols = piv.index.intersection(ret_wide.columns)
        if len(symbols) < len(factors_sorted) + 1:
            continue
        X = piv.loc[symbols, factors_sorted].to_numpy(dtype=float)
        y = ret_wide.loc[dt, symbols].to_numpy(dtype=float)
        w = (np.sqrt(np.abs(cap_wide.loc[dt, symbols]).to_numpy(dtype=float))
             if cap_wide is not None else np.ones(len(symbols)))
        ok = np.isfinite(X).all(axis=1) & np.isfinite(y)
        X, y, w = X[ok], y[ok], w[ok]
        if len(X) < len(factors_sorted) + 1:
            continue
        W = np.diag(w)
        try:
            f = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
        except np.linalg.LinAlgError:
            continue
        records.append([dt] + [float(v) for v in f])
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records, columns=["date"] + factors_sorted).set_index("date").sort_index()


def compute(ctx) -> LayerResult:
    r_p, r_b = ctx.portfolio_ret, ctx.benchmark_ret
    if r_p is None or r_b is None:
        return LayerResult("factor_attribution", degraded=True, note="缺少 portfolio 或 benchmark 收益序列。")

    excess = (r_p - r_b).dropna()
    if len(excess) < 2:
        return LayerResult("factor_attribution", degraded=True, note="超额序列过短。")

    # 因子收益来源
    fr = ctx.factor_returns
    if fr is None:
        if ctx.symbol_exposures is not None and ctx.symbol_returns is not None:
            fr = _wls_factor_returns(ctx.symbol_exposures, ctx.symbol_returns, ctx.cap_weights)
            if fr.empty:
                return LayerResult("factor_attribution", degraded=True,
                                   note="内置截面 WLS 未能估出因子收益（样本不足或秩亏）。")
        else:
            return LayerResult("factor_attribution", degraded=True,
                               note="缺少 factor-returns（或 symbol-exposures + symbol-returns + cap-weights）。")

    if ctx.factor_exposures is None:
        return LayerResult("factor_attribution", degraded=True, note="缺少 factor-exposures（组合暴露）。")

    X_p = ctx.factor_exposures
    X_b = ctx.benchmark_exposures if ctx.benchmark_exposures is not None else pd.DataFrame(0.0, index=X_p.index, columns=X_p.columns)
    fr = fr.reindex(X_p.index).fillna(0.0)

    factors = [c for c in X_p.columns if c in fr.columns]
    if not factors:
        return LayerResult("factor_attribution", degraded=True, note="因子收益与暴露无共同因子列。")

    common = excess.index.intersection(X_p.index)
    if len(common) < 2:
        return LayerResult("factor_attribution", degraded=True, note="超额与暴露日期无交集。")

    contributions = {}
    for k in factors:
        diff = (X_p.loc[common, k].fillna(0.0) - X_b.loc[common, k].fillna(0.0))
        contributions[k] = float((diff * fr.loc[common, k]).sum())

    excess_total = float(excess.loc[common].sum())
    alpha_total = excess_total - sum(contributions.values())
    recon = sum(contributions.values()) + alpha_total - excess_total

    data = {
        "factors": [{"factor": k, "contribution": v} for k, v in contributions.items()],
        "alpha_residual": alpha_total,
        "excess_total": excess_total,
        "n_days": len(common),
        "factor_return_source": "provided" if ctx.factor_returns is not None else "internal WLS",
        "basis": "期间加总：贡献=暴露差×因子收益；Alpha残差=超额−Σ贡献",
    }
    return LayerResult("factor_attribution", data=data, recon_residual=float(recon))
