#!/usr/bin/env python3

import sys
import csv
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
from src.wifi7_pipeline.core import (
    calc_rssi_degradation,
    calc_stats,
    calc_throughput_degradation,
    format_sig_figs,
    load_scenario_data,
    ordered_stats,
)

from src.wifi7_pipeline.reporting.csv_export import generate_summary_csv


def natural_sort_key(p: Path):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', p.name)]


def main():
    print("=== Wi-Fi 7 Full Summary CSV Generator ===")
    base_dir = (ROOT_DIR / "compiled_data").resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Error: Base directory '{base_dir}' does not exist.")
        sys.exit(1)

    scenarios = [d for d in base_dir.iterdir() if d.is_dir()]
    if not scenarios:
        print("No scenarios found in ./compiled_data/")
        sys.exit(1)

    scenarios = sorted(scenarios, key=natural_sort_key)

    tp_source = input(
        "\nCalculate throughput from:\n  1. iPerf logs\n  2. Wireshark pcap (summed packet sizes)\nSelection [1/2]: "
    ).strip()

    out_input = input("\nEnter output CSV path [default: ./wifi7_summary_table.csv]: ").strip()
    default_out = ROOT_DIR / "wifi7_summary_table.csv"
    out_path = Path(out_input).resolve() if out_input else default_out.resolve()

    generate_summary_csv(scenarios, tp_source, out_path)


if __name__ == "__main__":
    main()