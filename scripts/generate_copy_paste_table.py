import sys
import time
import shutil
import subprocess
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from wifi7_pipeline.reporting.table_export import run_table_export

def main():
    print("=== Wi-Fi 7 Table Generator (Keyboard Hijack) ===")
    base_dir = (ROOT_DIR / "compiled_data").resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Error: Base directory '{base_dir}' does not exist.")
        sys.exit(1)
        
    scenarios = [d for d in base_dir.iterdir() if d.is_dir()]
    if not scenarios:
        print("No scenarios found in ./compiled_data/")
        sys.exit(1)
        
    print("\nAvailable scenarios:")
    for i, s in enumerate(scenarios):
        print(f"  {i+1}. {s.name}")
        
    choice = input("\nSelect a scenario by number: ").strip()
    try:
        scenario_idx = int(choice)
        selected_scenario = scenarios[scenario_idx - 1]
    except (ValueError, IndexError):
        print("Invalid selection. Quitting.")
        sys.exit(1)

    tp_source = input("\nCalculate throughput from:\n  1. iPerf logs\n  2. Wireshark pcap (summed packet sizes)\nSelection [1/2]: ").strip()

    print("\nSelect columns to output:")
    print("  1. Default (Legacy layout: TP LOS, tabs, DBM LOS, tabs, TP Prop, Deg, tabs, DBM Prop, Deg)")
    print("  2. Custom columns")
    col_choice = input("Selection [1/2]: ").strip()
    
    columns = None
    if col_choice == '2':
        print("\nAvailable columns:")
        print("  tp_los     : LOS Throughput (Min, Q1, Mean, Med, Q3, Max) [6 cols]")
        print("  dbm_los    : LOS RSSI (Min, Q1, Mean, Med, Q3, Max) [6 cols]")
        print("  noise_los  : LOS Noise rate (pkts/s) [1 col]")
        print("  tp_prop    : Scenario Throughput (Min, Q1, Mean, Med, Q3, Max) [6 cols]")
        print("  deg_tp     : Throughput Degradation % [1 col]")
        print("  dbm_prop   : Scenario RSSI (Min, Q1, Mean, Med, Q3, Max) [6 cols]")
        print("  deg_dbm    : RSSI Degradation dB [1 col]")
        print("  noise_prop : Scenario Noise rate (pkts/s) [1 col]")
        print("  tab        : Insert a single blank Tab space")
        
        print("\nEnter columns separated by commas (e.g. tp_los, noise_los, tp_prop, noise_prop, deg_tp):")
        cols_input = input("Columns: ").strip()
        if cols_input:
            columns = [c.strip() for c in cols_input.split(',')]

    while True:
        print("\nSelect frequency to auto-type into Word table:")
        print("  1. 2.4 GHz")
        print("  2. 5 GHz")
        print("  3. 6 GHz")
        print("  4. MLO")
        print("  5. All frequencies (2.4 -> 5 -> 6 -> MLO)")
        print("  0. Exit")
        
        freq_choice = input("Selection: ").strip()
        if freq_choice == '0':
            break
            
        run_table_export(selected_scenario, tp_source, freq_choice, columns)

if __name__ == "__main__":
    main()