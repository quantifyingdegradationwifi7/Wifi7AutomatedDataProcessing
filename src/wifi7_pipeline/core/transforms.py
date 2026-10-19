from __future__ import annotations

import numpy as np


def bin_and_aggregate_data(
    data_tuples: list[tuple[float, float]],
    bin_size: float = 0.1,
    method: str = 'mean',
    missing_value: float = 0.0,
    duration: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if not data_tuples and duration is None:
        return np.array([]), np.array([])

    max_time: float = duration if duration is not None else (max((t for t, _ in data_tuples), default=0.0))
    bins: np.ndarray = np.arange(0, max_time + bin_size, bin_size)
    if len(bins) < 2:
        bins = np.array([0.0, bin_size])

    binned_vals: list[list[float]] = [[] for _ in range(len(bins) - 1)]

    for t, v in data_tuples:
        idx = int(t / bin_size)
        if 0 <= idx < len(binned_vals):
            binned_vals[idx].append(v)

    bin_centers: np.ndarray = bins[:-1] + bin_size / 2
    agg_vals: list[float] = []

    for bucket in binned_vals:
        if not bucket:
            agg_vals.append(missing_value)
        elif method == 'median':
            agg_vals.append(np.median(bucket))
        elif method == 'sum_to_mbps':
            agg_vals.append((sum(bucket) * 8) / 1_000_000 / bin_size)
        elif method == 'dbm_mean':
            mw = [10 ** (v / 10.0) for v in bucket]
            agg_vals.append(10.0 * np.log10(np.mean(mw)) if np.mean(mw) > 0 else missing_value)
        else:
            agg_vals.append(np.mean(bucket))

    return bin_centers, np.array(agg_vals)


def apply_smoothing(y_values: np.ndarray, window_size: int = 10) -> np.ndarray:
    smoothed: np.ndarray = np.empty_like(y_values, dtype=float)
    half_win: int = window_size // 2

    for i in range(len(y_values)):
        start: int = max(0, i - half_win)
        end: int = min(len(y_values), i + half_win + 1)
        window: np.ndarray = y_values[start:end]
        valid_vals: np.ndarray = window[~np.isnan(window)]

        if len(valid_vals) > 0:
            smoothed[i] = np.mean(valid_vals)
        else:
            smoothed[i] = np.nan

    return smoothed



