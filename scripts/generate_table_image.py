#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib.pyplot as plt
from wifi7_pipeline.core.scenario_io import load_scenario_data
from wifi7_pipeline.reporting.csv_export import get_freq_stats

def main():
    print("=== Wi-Fi 7 Table Image Generator ===")
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

    freqs_input = input("\nWhich frequencies to include? (comma separated, e.g. 2.4, 5, 6, mlo, all) [all]: ").strip().lower()
    if not freqs_input or freqs_input == 'all':
        freq_list = ['24', '5', '6', 'mlo']
    else:
        freq_list = []
        for f in freqs_input.split(','):
            f = f.strip()
            if f == '2.4': f = '24'
            freq_list.append(f)

    print("\nSelect columns to include in the table image (comma separated):")
    print("  tp       : Throughput (Min, Q1, Mean, Med, Q3, Max)")
    print("  dbm      : RSSI (Min, Q1, Mean, Med, Q3, Max)")
    print("  noise    : Noise rate (pkts/s)")
    print("  deg      : Degradations (Throughput % and RSSI dB)")
    cols_input = input("Columns [tp, dbm, noise, deg]: ").strip()
    
    if not cols_input:
        selected_metrics = ['tp', 'dbm', 'noise', 'deg']
    else:
        selected_metrics = [c.strip() for c in cols_input.split(',')]

    show_los = input("\nInclude LOS data? (y/n) [y]: ").strip().lower() != 'n'
    show_prop = input("Include Scenario/Experiment data? (y/n) [y]: ").strip().lower() != 'n'

    print(f"\nLoading data for {selected_scenario.name}...")
    raw_data = load_scenario_data(selected_scenario)
    if not raw_data:
        print(f"No valid data found for {selected_scenario.name}. Exiting.")
        return

    if tp_source == '2':
        for d in raw_data:
            d['throughput'] = d.get('wireshark_throughput', [])

    # Build the table data
    headers = ["Frequency"]
    
    stat_cols = ["Min", "Q1", "Mean", "Med", "Q3", "Max"]
    
    if show_los:
        if 'tp' in selected_metrics:
            headers.extend([f"LOS TP {c}" for c in stat_cols])
        if 'dbm' in selected_metrics:
            headers.extend([f"LOS RSSI {c}" for c in stat_cols])
        if 'noise' in selected_metrics:
            headers.append("LOS Noise")
            
    if show_prop:
        if 'tp' in selected_metrics:
            headers.extend([f"Exp TP {c}" for c in stat_cols])
        if 'dbm' in selected_metrics:
            headers.extend([f"Exp RSSI {c}" for c in stat_cols])
        if 'noise' in selected_metrics:
            headers.append("Exp Noise")
            
    if 'deg' in selected_metrics and show_los and show_prop:
        headers.extend(["Deg TP", "Deg RSSI"])

    rows = []
    
    for f in freq_list:
        stats = get_freq_stats(f, raw_data)
        f_label = "2.4 GHz" if f == '24' else ("MLO" if f == 'mlo' else f"{f} GHz")
        
        row = [f_label]
        
        if show_los:
            if 'tp' in selected_metrics: row.extend(stats['tp_los'])
            if 'dbm' in selected_metrics: row.extend(stats['dbm_los'])
            if 'noise' in selected_metrics: row.append(stats.get('noise_los', '0/s'))
            
        if show_prop:
            if 'tp' in selected_metrics: row.extend(stats['tp_prop'])
            if 'dbm' in selected_metrics: row.extend(stats['dbm_prop'])
            if 'noise' in selected_metrics: row.append(stats.get('noise_prop', '0/s'))
            
        if 'deg' in selected_metrics and show_los and show_prop:
            row.append(stats.get('deg_tp', '0%'))
            row.append(stats.get('deg_dbm', '0 dB'))
            
        rows.append(row)

    # Plot the table using matplotlib
    fig, ax = plt.subplots(figsize=(len(headers) * 1.2, len(rows) * 0.5 + 1.5))
    ax.axis('tight')
    ax.axis('off')
    
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.5)
    
    # Style the table
    for (i, j), cell in table.get_celld().items():
        if i == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#d3d3d3')
    
    out_dir = selected_scenario / "tables"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{selected_scenario.name}_table.png"
    
    plt.title(f"Test Results: {selected_scenario.name}", fontweight="bold", pad=20)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[+] Saved table image to {out_path}")

if __name__ == "__main__":
    main()