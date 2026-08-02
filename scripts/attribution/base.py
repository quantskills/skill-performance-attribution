"""共享基础：输入加载、日频对齐、LayerResult 数据类。

依赖：pandas + numpy（无 scipy/statsmodels；OLS 用最小二乘闭式解）。

输入约定（CSV/parquet/xlsx）：
  portfolio / benchmark : date, ret 两列（日收益）
  weights              : 宽表 date×symbol 或长表 date, symbol, weight
  industry-map         : symbol, industry 两列
  factor-exposures     : 宽表 date×factor（组合暴露）；或长表 date, symbol, factor, value
  factor-returns       : 宽表 date×factor
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd


@dataclass
class LayerResult:
    """单层归因结果。recon_residual 用于对账；degraded 为 True 表示该层降级（证据不足）。"""
    name: str
    data: dict = field(default_factory=dict)
    recon_residual: float | None = None
    degraded: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, **asdict(self)}


@dataclass
class Context:
    """三层归因共享的输入。字段缺省为 None → 对应层降级。"""
    portfolio_ret: pd.Series | None = None
    benchmark_ret: pd.Series | None = None
    weights: pd.DataFrame | None = None           # date×symbol 组合权重
    benchmark_weights: pd.Series | None = None    # symbol 基准权重
    symbol_returns: pd.DataFrame | None = None    # date×symbol 个股收益（复权）
    industry_map: dict | None = None              # {symbol: industry}
    factor_exposures: pd.DataFrame | None = None  # date×factor 组合暴露
    benchmark_exposures: pd.DataFrame | None = None  # date×factor 基准暴露
    factor_returns: pd.DataFrame | None = None    # date×factor 因子收益
    symbol_exposures: pd.DataFrame | None = None  # 长表 date,symbol,factor,value
    cap_weights: pd.DataFrame | None = None       # date×symbol 市值权重
    scope: str = "all"                            # all|brinson|factor|alpha_beta
    benchmark_label: str = "未指定"


# ---------- 输入加载 ----------

def _read(path: str) -> pd.DataFrame:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(path)
    lower = path.lower()
    if lower.endswith((".csv", ".txt")):
        return pd.read_csv(path)
    if lower.endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    raise ValueError(f"不支持的格式: {path}")


def load_returns(path: str | None) -> pd.Series | None:
    """date, ret 两列 → 以 date 为索引的 Series。"""
    if not path:
        return None
    df = _read(path)
    ret_col = "ret" if "ret" in df.columns else (df.columns[1] if df.shape[1] > 1 else df.columns[0])
    df["date"] = pd.to_datetime(df["date"])
    s = df.set_index("date")[ret_col].astype(float)
    return s.sort_index()


def load_weights(path: str | None) -> pd.DataFrame | None:
    """宽表（date×symbol）或长表（date, symbol, weight）→ 宽表。"""
    if not path:
        return None
    df = _read(path)
    if "symbol" in df.columns:
        wcol = "weight" if "weight" in df.columns else ("value" if "value" in df.columns else None)
        if wcol is None:
            raise ValueError("长表 weights 缺少 weight/value 列")
        df["date"] = pd.to_datetime(df["date"])
        return df.pivot(index="date", columns="symbol", values=wcol).sort_index()
    df = df.copy()
    first = str(df.columns[0])
    if "date" in df.columns:
        col = "date"
    elif first in ("", "Unnamed: 0", "date"):
        col = df.columns[0]
    else:
        return df
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.set_index(col).sort_index()


def load_map(path: str | None) -> dict[str, str] | None:
    """symbol, industry 两列 → {symbol: industry}。"""
    if not path:
        return None
    df = _read(path)
    sym_col = "symbol" if "symbol" in df.columns else df.columns[0]
    ind_col = "industry" if "industry" in df.columns else df.columns[1]
    return dict(zip(df[sym_col].astype(str), df[ind_col].astype(str)))


def load_exposures(path: str | None) -> pd.DataFrame | None:
    """因子暴露/收益加载：
      - 长表（含 symbol+factor 列，即个股级暴露）→ 原样返回长表（date,symbol,factor,value），供内置 WLS 用
      - 否则（date×factor 宽表）→ 以 date 为索引返回
    """
    if not path:
        return None
    df = _read(path)
    if "symbol" in df.columns and "factor" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df = df.copy()
    first = str(df.columns[0])
    col = "date" if "date" in df.columns else (df.columns[0] if first in ("", "Unnamed: 0", "date") else None)
    if col:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.set_index(col)
    return df.sort_index()


def align(*series) -> pd.DataFrame:
    """按日期内连接多列收益序列。"""
    frame = pd.concat([s.rename(s.name or f"s{i}") for i, s in enumerate(series)], axis=1)
    return frame.dropna()


# ---------- 工具 ----------

def ols(y: pd.Series, X: pd.DataFrame) -> dict:
    """最小二乘：y = X·b。返回 {coef: dict, intercept_handle}。"""
    X = X.copy()
    if "const" not in X.columns:
        X.insert(0, "const", 1.0)
    Xv = X.to_numpy(dtype=float)
    yv = y.to_numpy(dtype=float)
    try:
        beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    except np.linalg.LinAlgError:
        return {"coef": {c: float("nan") for c in X.columns}, "r2": float("nan"), "error": "rank-deficient"}
    yhat = Xv @ beta
    ss_res = float(np.sum((yv - yhat) ** 2))
    ss_tot = float(np.sum((yv - yv.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"coef": dict(zip(X.columns, [float(b) for b in beta])), "r2": float(r2)}
