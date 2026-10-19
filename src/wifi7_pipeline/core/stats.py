from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def calc_stats(vals: Iterable[float], is_dbm: bool = False) -> dict[str, float]:
    values = list(vals)
    if not values:
        return {
            'min': 0.0,
            'q1': 0.0,
            'median': 0.0,
            'mean': 0.0,
            'q3': 0.0,
            'max': 0.0,
        }

    if is_dbm:
        import math
        mw_values = [10 ** (v / 10.0) for v in values]
        mean_val = 10.0 * math.log10(np.mean(mw_values)) if np.mean(mw_values) > 0 else -100.0
    else:
        mean_val = float(np.mean(values))

    return {
        'min': float(np.min(values)),
        'q1': float(np.percentile(values, 25)),
        'median': float(np.median(values)),
        'mean': float(mean_val),
        'q3': float(np.percentile(values, 75)),
        'max': float(np.max(values)),
    }


def ordered_stats(stats: dict[str, float]) -> list[float]:
    return [
        stats['min'],
        stats['q1'],
        stats['mean'],
        stats['median'],
        stats['q3'],
        stats['max'],
    ]


def calc_throughput_degradation(los_median: float, scenario_median: float) -> float:
    if los_median <= 0:
        return float('nan')
    return ((los_median - scenario_median) / los_median) * 100


def calc_rssi_degradation(los_dbm: float, scenario_dbm: float) -> float:
    return los_dbm - scenario_dbm


def format_sig_figs(val: float, n: int = 4) -> str:
    if val is None or np.isnan(val):
        return ""
    if val == 0:
        return "0.0" if n > 2 else "0"

    try:
        abs_val = abs(val)
        mag = int(math.floor(math.log10(abs_val)))
        decimals = n - 1 - mag

        if decimals <= 0:
            rounded = round(val, decimals)
            return f"{int(rounded)}"

        rounded = round(val, decimals)
        if rounded == 0:
            return "0.0" if n > 2 else "0"

        new_mag = int(math.floor(math.log10(abs(rounded))))
        if new_mag > mag:
            decimals = n - 1 - new_mag
            if decimals <= 0:
                return f"{int(round(rounded, decimals))}"

        formatted = f"{rounded:.{decimals}f}"
        if "." in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted
    except (ValueError, OverflowError):
        return f"{val:.1f}"
