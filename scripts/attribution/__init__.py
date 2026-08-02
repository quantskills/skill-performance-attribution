"""绩效归因计算层：层1 Alpha/Beta/择时、层2 Brinson、层3 因子收益归因。

每个模块暴露 `compute(ctx) -> dict`，返回可渲染的结果字典（见各层专文/report-format.md）。
"""
from __future__ import annotations

from .alpha_beta import compute as compute_alpha_beta
from .brinson import compute as compute_brinson
from .factor_attribution import compute as compute_factor

__all__ = ["compute_alpha_beta", "compute_brinson", "compute_factor"]
