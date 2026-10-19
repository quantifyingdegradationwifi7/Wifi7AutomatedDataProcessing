from __future__ import annotations

import csv
import re
from pathlib import Path

from ..core.stats import (
    calc_rssi_degradation,
    calc_stats,
    calc_throughput_degradation,
    format_sig_figs,
    ordered_stats,
)
from ..core.scenario_io import load_scenario_data


def get_freq_stats(f: str, raw_data: list) -> dict[str, list[str] | str]:
    los_tp_f: list[float] = []
    prop_tp_f: list[float] = []
    los_dbm_f: list[float] = []
    prop_dbm_f: list[float] = []
    los_noise_f: list[float] = []
    prop_noise_f: list[float] = []

    for d in raw_data:
        if d['freq'] != f:
            continue
        if d['scenario_type'] == 'los':
            los_tp_f.extend([v for _, v in d['throughput']])
            los_dbm_f.extend([v for _, v in d['dbm']])
            los_noise_f.append(d['noise_rate'])
        elif d['scenario_type'] == 'proper':
            prop_tp_f.extend([v for _, v in d['throughput']])
            prop_dbm_f.extend([v for _, v in d['dbm']])
            prop_noise_f.append(d['noise_rate'])

    tp_los_stats = calc_stats(los_tp_f)
    tp_prop_stats = calc_stats(prop_tp_f)
    dbm_los_stats = calc_stats(los_dbm_f, is_dbm=True)
    dbm_prop_stats = calc_stats(prop_dbm_f, is_dbm=True)

    deg_tp = calc_throughput_degradation(
        tp_los_stats['median'],
        tp_prop_stats['median'],
    )
    deg_dbm = calc_rssi_degradation(
        dbm_los_stats['median'],
        dbm_prop_stats['median'],
    )
    
    import numpy as np
    noise_los = float(np.mean(los_noise_f)) if los_noise_f else 0.0
    noise_prop = float(np.mean(prop_noise_f)) if prop_noise_f else 0.0

    return {
        'tp_los': [format_sig_figs(v, 4) for v in ordered_stats(tp_los_stats)],
        'tp_prop': [format_sig_figs(v, 4) for v in ordered_stats(tp_prop_stats)],
        'deg_tp': f"{format_sig_figs(deg_tp, 2)}%",
        'dbm_los': [format_sig_figs(v, 4) for v in ordered_stats(dbm_los_stats)],
        'dbm_prop': [format_sig_figs(v, 4) for v in ordered_stats(dbm_prop_stats)],
        'deg_dbm': f"{format_sig_figs(deg_dbm, 2)} dB",
        'noise_los': f"{noise_los:.0f}/s",
        'noise_prop': f"{noise_prop:.0f}/s",
    }


def generate_summary_csv(scenarios: list[Path], tp_source: str, out_path: Path) -> None:
    headers = [
        "Scenario",
        "Frequency",
        "LOS Throughput Min (Mbps)",
        "LOS Throughput Q1 (Mbps)",
        "LOS Throughput Mean (Mbps)",
        "LOS Throughput Median (Mbps)",
        "LOS Throughput Q3 (Mbps)",
        "LOS Throughput Max (Mbps)",
        "LOS RSSI Min (dBm)",
        "LOS RSSI Q1 (dBm)",
        "LOS RSSI Mean (dBm)",
        "LOS RSSI Median (dBm)",
        "LOS RSSI Q3 (dBm)",
        "LOS RSSI Max (dBm)",
        "Scenario Throughput Min (Mbps)",
        "Scenario Throughput Q1 (Mbps)",
        "Scenario Throughput Mean (Mbps)",
        "Scenario Throughput Median (Mbps)",
        "Scenario Throughput Q3 (Mbps)",
        "Scenario Throughput Max (Mbps)",
        "Throughput Degradation (%)",
        "Scenario RSSI Min (dBm)",
        "Scenario RSSI Q1 (dBm)",
        "Scenario RSSI Mean (dBm)",
        "Scenario RSSI Median (dBm)",
        "Scenario RSSI Q3 (dBm)",
        "Scenario RSSI Max (dBm)",
        "RSSI Degradation (dB)",
    ]

    freq_order = [('24', '2.4 GHz'), ('5', '5 GHz'), ('6', '6 GHz'), ('mlo', 'MLO')]
    rows: list[list[str]] = []

    print(f"\nProcessing {len(scenarios)} scenarios...")
    for idx, scenario in enumerate(scenarios, 1):
        print(f"  [{idx}/{len(scenarios)}] Loading {scenario.name}...")
        raw_data = load_scenario_data(scenario)
        if not raw_data:
            print(f"        [!] No valid data found for {scenario.name}. Skipping.")
            continue

        if tp_source == '2':
            for d in raw_data:
                d['throughput'] = d.get('wireshark_throughput', [])

        for f_code, f_label in freq_order:
            if not any(d.get('freq') == f_code for d in raw_data):
                continue

            stats = get_freq_stats(f_code, raw_data)
            rows.append([
                scenario.name,
                f_label,
                *stats['tp_los'],
                *stats['dbm_los'],
                *stats['tp_prop'],
                stats['deg_tp'],
                *stats['dbm_prop'],
                stats['deg_dbm'],
            ])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\n[+] Processing complete!")
    print(f"[+] Total rows written: {len(rows)}")
    print(f"[+] File saved to: {out_path}")