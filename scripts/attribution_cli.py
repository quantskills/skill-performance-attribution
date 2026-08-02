#!/usr/bin/env python3
"""A 股量化策略绩效归因 CLI（协议 + 可运行脚本的入口）。

用法：
  python scripts/attribution_cli.py \
    --portfolio portfolio_ret.csv --benchmark benchmark_ret.csv \
    --weights weights.csv --benchmark-weights bench_weights.csv \
    --symbol-returns symbol_ret.csv --industry-map industry_map.csv \
    --factor-exposures exposures.csv --benchmark-exposures bench_exposures.csv \
    --factor-returns factor_ret.csv --out out/

输入约定见 attribution/base.py。缺输入 → 对应层降级，绝不臆测。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "attribution"))

from attribution import compute_alpha_beta, compute_brinson, compute_factor
from attribution.base import Context, load_returns, load_weights, load_map, load_exposures
from report import render_markdown, render_json, timestamp


def load_benchmark_weights(path: str | None) -> pd.Series | None:
    """symbol,weight 两列，或宽表 date×symbol（取均值）→ Series。"""
    if not path:
        return None
    df = pd.read_csv(path) if path.endswith((".csv", ".txt")) else pd.read_parquet(path)
    if "symbol" in df.columns:
        wcol = "weight" if "weight" in df.columns else df.columns[1]
        return pd.Series(df[wcol].to_numpy(dtype=float), index=df["symbol"].astype(str))
    # 宽表：均值
    df = df.copy()
    first = str(df.columns[0])
    col = "date" if "date" in df.columns else (df.columns[0] if first in ("", "Unnamed: 0") else None)
    if col:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.set_index(col)
    return df.mean(axis=0)


def main() -> int:
    ap = argparse.ArgumentParser(description="A股量化策略绩效归因")
    ap.add_argument("--portfolio", help="组合日收益（date,ret）")
    ap.add_argument("--benchmark", help="基准日收益（date,ret）")
    ap.add_argument("--weights", help="组合权重（date×symbol 或 date,symbol,weight）")
    ap.add_argument("--benchmark-weights", help="基准权重（symbol,weight）")
    ap.add_argument("--symbol-returns", help="个股收益面板（date×symbol）")
    ap.add_argument("--industry-map", help="行业映射（symbol,industry）")
    ap.add_argument("--factor-exposures", help="组合因子暴露（date×factor）")
    ap.add_argument("--benchmark-exposures", help="基准因子暴露（date×factor，缺省按 0）")
    ap.add_argument("--factor-returns", help="因子收益（date×factor，可来自 skill-risk-model）")
    ap.add_argument("--symbol-exposures", help="个股因子暴露长表（date,symbol,factor,value）")
    ap.add_argument("--cap-weights", help="市值权重（date×symbol）")
    ap.add_argument("--scope", default="all", choices=["all", "brinson", "factor", "alpha_beta"], help="归因范围")
    ap.add_argument("--benchmark-label", default="自定义", help="基准显示名")
    ap.add_argument("--out", default="out", help="输出目录")
    args = ap.parse_args()

    ctx = Context(
        portfolio_ret=load_returns(args.portfolio),
        benchmark_ret=load_returns(args.benchmark),
        weights=load_weights(args.weights),
        benchmark_weights=load_benchmark_weights(args.benchmark_weights),
        symbol_returns=load_weights(args.symbol_returns),  # date×symbol 宽表
        industry_map=load_map(args.industry_map),
        factor_exposures=load_exposures(args.factor_exposures),
        benchmark_exposures=load_exposures(args.benchmark_exposures),
        factor_returns=load_exposures(args.factor_returns),
        symbol_exposures=load_exposures(args.symbol_exposures),
        cap_weights=load_weights(args.cap_weights),
        scope=args.scope,
        benchmark_label=args.benchmark_label,
    )

    layers = {}
    if args.scope in ("all", "alpha_beta"):
        layers["alpha_beta"] = compute_alpha_beta(ctx)
    if args.scope in ("all", "brinson"):
        layers["brinson"] = compute_brinson(ctx)
    if args.scope in ("all", "factor"):
        layers["factor_attribution"] = compute_factor(ctx)

    os.makedirs(args.out, exist_ok=True)
    ts = timestamp()
    md = render_markdown(layers, ctx, ts)
    js = render_json(layers, ctx, ts)

    md_path = os.path.join(args.out, "attribution_report.md")
    js_path = os.path.join(args.out, "attribution_report.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(js_path, "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, indent=2)

    status = [f"{k}=[OK]" if (v is not None and not v.degraded) else f"{k}=[degraded]" for k, v in layers.items()]
    print(f"[ok] 归因完成：{', '.join(status)} -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
