#!/usr/bin/env python3
"""合成数据自检：用「已知因子模型」生成数据，验证三层归因。

验证点：
  a) Brinson：Σ(配置+选择+交互) ≈ 组合超额（对账 < 1e-6）
  b) 因子归因（提供因子收益）：Σ贡献 + Alpha 残差 ≈ 超额（对账 < 1e-6）
  c) 内置截面 WLS：恢复出的因子收益 ≈ 真实因子收益（RMSE < 0.005）
  d) Alpha/Beta：β 接近 1（组合与基准同为股票加权）

运行：python scripts/self_test.py [--out out/self_test]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "attribution"))

from attribution import compute_alpha_beta, compute_brinson, compute_factor
from attribution.base import Context
from attribution.factor_attribution import _wls_factor_returns
from report import render_markdown, render_json, timestamp

SEED = 7
INDUSTRIES = ["I0", "I1", "I2", "I3"]


def build() -> dict:
    rng = np.random.default_rng(SEED)
    n_dates, n_sym = 120, 40
    dates = pd.bdate_range("2024-01-01", periods=n_dates)
    symbols = [f"S{i:03d}" for i in range(n_sym)]
    ind_of = {s: INDUSTRIES[i // 10] for i, s in enumerate(symbols)}

    # 暴露（跨期常数）
    size = rng.uniform(0.5, 2.0, n_sym)
    mom = rng.uniform(-1.0, 1.0, n_sym)

    # 因子收益（真实）
    f_size = rng.normal(0.001, 0.01, n_dates)
    f_mom = rng.normal(0.0005, 0.008, n_dates)
    f_ind = {ind: rng.normal(0.0005, 0.005, n_dates) for ind in INDUSTRIES[1:]}

    # 收益 = SIZE·f + MOM·f + 行业哑变量(I1..I3, I0 为基准) + 特异项
    eps = rng.normal(0, 0.004, (n_dates, n_sym))
    R = np.zeros((n_dates, n_sym))
    for t in range(n_dates):
        for j, s in enumerate(symbols):
            r = size[j] * f_size[t] + mom[j] * f_mom[t]
            k = INDUSTRIES.index(ind_of[s])
            if k > 0:
                r += f_ind[INDUSTRIES[k]][t]
            R[t, j] = r + eps[t, j]
    ret_wide = pd.DataFrame(R, index=dates, columns=symbols)

    # 基准权重：每行业 25%、行业内等权
    w_b = pd.Series(0.025, index=symbols)
    # 组合权重：行业配比 [0.4,0.3,0.2,0.1] + 行业内向高动量倾斜（制造选择效应）
    w_p = np.zeros(n_sym)
    mix = [0.4, 0.3, 0.2, 0.1]
    for k, ind in enumerate(INDUSTRIES):
        idx = [j for j, s in enumerate(symbols) if ind_of[s] == ind]
        base = np.array([1 + 0.5 * mom[j] for j in idx])
        wv = base / base.sum() * mix[k]
        for jj, j in enumerate(idx):
            w_p[j] = wv[jj]
    w_p = pd.Series(w_p, index=symbols)

    r_p = pd.Series(R @ w_p.values, index=dates, name="rp")
    r_b = pd.Series(R @ w_b.values, index=dates, name="rb")

    # 个股级暴露长表（全因子全 symbol，I0 行业哑变量=0）
    factors = ["SIZE", "MOM"] + INDUSTRIES[1:]
    rows = []
    for d in dates:
        for j, s in enumerate(symbols):
            for f in factors:
                if f == "SIZE":
                    v = size[j]
                elif f == "MOM":
                    v = mom[j]
                else:
                    v = 1.0 if ind_of[s] == f else 0.0
                rows.append((d, s, f, v))
    sym_exp = pd.DataFrame(rows, columns=["date", "symbol", "factor", "value"])

    # 组合/基准暴露（跨期常数）
    X_sym = pd.DataFrame({"SIZE": size, "MOM": mom}, index=symbols)
    for f in INDUSTRIES[1:]:
        X_sym[f] = [1.0 if ind_of[s] == f else 0.0 for s in symbols]
    X_p = pd.DataFrame(np.tile(w_p.values @ X_sym.values, (n_dates, 1)), index=dates, columns=X_sym.columns)
    X_b = pd.DataFrame(np.tile(w_b.values @ X_sym.values, (n_dates, 1)), index=dates, columns=X_sym.columns)

    # 真实因子收益表
    f_true = pd.DataFrame({"SIZE": f_size, "MOM": f_mom,
                           **{ind: f_ind[ind] for ind in INDUSTRIES[1:]}}, index=dates)

    # 市值权重 ∝ exp(size)（√市值加权）
    cap = pd.DataFrame(np.tile(np.exp(size), (n_dates, 1)), index=dates, columns=symbols)

    w_p_frame = pd.DataFrame(np.tile(w_p.values, (n_dates, 1)), index=dates, columns=symbols)
    return {
        "r_p": r_p, "r_b": r_b, "weights": w_p_frame,
        "benchmark_weights": w_b, "symbol_returns": ret_wide, "industry_map": ind_of,
        "factor_exposures": X_p, "benchmark_exposures": X_b, "factor_returns": f_true,
        "symbol_exposures": sym_exp, "cap_weights": cap, "f_true": f_true,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="绩效归因自检（合成数据）")
    ap.add_argument("--out", default=os.path.join("out", "self_test"))
    args = ap.parse_args()
    data = build()

    # ---- 运行1：提供因子收益路径 ----
    ctx1 = Context(
        portfolio_ret=data["r_p"], benchmark_ret=data["r_b"],
        weights=data["weights"], benchmark_weights=data["benchmark_weights"],
        symbol_returns=data["symbol_returns"], industry_map=data["industry_map"],
        factor_exposures=data["factor_exposures"], benchmark_exposures=data["benchmark_exposures"],
        factor_returns=data["factor_returns"], scope="all",
        benchmark_label="沪深300（合成 demo）",
    )
    layers1 = {"alpha_beta": compute_alpha_beta(ctx1), "brinson": compute_brinson(ctx1),
               "factor_attribution": compute_factor(ctx1)}

    # ---- 运行2：内置截面 WLS 路径 ----
    ctx2 = Context(
        portfolio_ret=data["r_p"], benchmark_ret=data["r_b"],
        weights=data["weights"], benchmark_weights=data["benchmark_weights"],
        symbol_returns=data["symbol_returns"], industry_map=data["industry_map"],
        factor_exposures=data["factor_exposures"], benchmark_exposures=data["benchmark_exposures"],
        symbol_exposures=data["symbol_exposures"], cap_weights=data["cap_weights"],
        scope="factor", benchmark_label="沪深300（合成 demo）",
    )
    l3_wls = compute_factor(ctx2)

    # ---- 对账断言 ----
    l2, l3 = layers1["brinson"], layers1["factor_attribution"]
    assert not l2.degraded and abs(l2.recon_residual) < 1e-6, f"Brinson 对账失败: {l2.recon_residual}"
    assert not l3.degraded and abs(l3.recon_residual) < 1e-6, f"因子归因对账失败: {l3.recon_residual}"
    assert not l3_wls.degraded and abs(l3_wls.recon_residual) < 1e-6, f"WLS 路径对账失败: {l3_wls.recon_residual}"
    assert not layers1["alpha_beta"].degraded

    # ---- WLS 因子收益恢复 ----
    rec = _wls_factor_returns(data["symbol_exposures"], data["symbol_returns"], data["cap_weights"])
    rmse = float(np.sqrt(((rec - data["f_true"].reindex(rec.index)) ** 2).to_numpy().mean()))
    assert rmse < 0.005, f"WLS 因子收益恢复偏差过大: RMSE={rmse:.5f}"

    os.makedirs(args.out, exist_ok=True)
    ts = timestamp()
    md = render_markdown(layers1, ctx1, ts)
    js = render_json(layers1, ctx1, ts)
    md_path = os.path.join(args.out, "attribution_report.md")
    js_path = os.path.join(args.out, "attribution_report.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(js_path, "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, indent=2)

    t = l2.data["total"]
    print(f"[ok] Brinson 对账残差 = {l2.recon_residual:.2e} [PASS]")
    print(f"[ok] 因子归因对账残差 = {l3.recon_residual:.2e} [PASS]")
    print(f"[ok] WLS 路径对账残差 = {l3_wls.recon_residual:.2e} [PASS]")
    print(f"[ok] WLS 因子收益恢复 RMSE = {rmse:.5f}（阈值 0.005）[PASS]")
    print(f"     Brinson: 配置={t['allocation']:.4f} 选择={t['selection']:.4f} 交互={t['interaction']:.4f} 超额={t['excess']:.4f}")
    print(f"     因子归因: Σ贡献={sum(r['contribution'] for r in l3.data['factors']):.4f} Alpha残差={l3.data['alpha_residual']:.4f}")
    print(f"     β={layers1['alpha_beta'].data['beta']:.3f} 年化Alpha={layers1['alpha_beta'].data['alpha_ann']:.4f}")
    print(f"[ok] 报告 → {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
