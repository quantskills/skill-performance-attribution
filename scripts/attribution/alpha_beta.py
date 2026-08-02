"""层1：Alpha / Beta / 择时分解。

组合收益对基准收益做 OLS（CAPM 式），输出 β、Jensen's Alpha（年化）、
超额；可选 Treynor-Mazuy 二次项估算择时贡献。
"""
from __future__ import annotations

import pandas as pd

from .base import LayerResult, align, ols

ANN = 252


def _annualize(mean_daily: float) -> float:
    return mean_daily * ANN


def compute(ctx) -> LayerResult:
    r_p = ctx.portfolio_ret
    r_b = ctx.benchmark_ret
    if r_p is None or r_b is None:
        return LayerResult("alpha_beta", degraded=True, note="缺少 portfolio 或 benchmark 收益序列。")

    frame = align(r_p.rename("rp"), r_b.rename("rb"))
    if len(frame) < 30:
        return LayerResult("alpha_beta", degraded=True, note=f"对齐后样本仅 {len(frame)} 天，不足 30。")

    res = ols(frame["rp"], frame[["rb"]])
    alpha_d = res["coef"].get("const", float("nan"))
    beta = res["coef"].get("rb", float("nan"))

    # 择时（Treynor-Mazuy）：加 rb² 项
    frame2 = frame.copy()
    frame2["rb2"] = frame2["rb"] ** 2
    res2 = ols(frame2["rp"], frame2[["rb", "rb2"]])
    gamma = res2["coef"].get("rb2", float("nan"))

    r_p_tot = float((1 + frame["rp"]).prod() - 1)   # 几何累计收益（报告用）
    r_b_tot = float((1 + frame["rb"]).prod() - 1)
    excess = float((frame["rp"] - frame["rb"]).sum())  # 算术超额：日超额加总（归因对账口径）

    data = {
        "r_p": r_p_tot,
        "r_b": r_b_tot,
        "excess": excess,
        "beta": beta,
        "alpha_ann": _annualize(alpha_d),
        "timing_gamma": gamma,
        "r2": res["r2"],
        "n_days": len(frame),
        "cost_basis": "几何累计收益(报告用) + 算术超额(对账口径)、无风险利率 0、日频 252 年化",
    }
    return LayerResult("alpha_beta", data=data, recon_residual=0.0, note="")
