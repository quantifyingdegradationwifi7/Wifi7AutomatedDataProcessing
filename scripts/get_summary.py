#!/usr/bin/env python3
import sys
import re
import json
import argparse
import textwrap
from pathlib import Path
from typing import Optional, Any, Dict, List

import numpy as np
import matplotlib.pyplot as plt

# Ensure src directory is in the Python search path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from wifi7_pipeline.core.scenario_io import load_scenario_data
    from wifi7_pipeline.reporting.csv_export import get_freq_stats
    from wifi7_pipeline.core import (
        calc_rssi_degradation,
    )
except ImportError:
    try:
        from src.wifi7_pipeline.core.scenario_io import load_scenario_data
        from src.wifi7_pipeline.reporting.csv_export import get_freq_stats
        from src.wifi7_pipeline.core import (
            calc_rssi_degradation,
        )
    except ImportError:
        load_scenario_data = None
        get_freq_stats = None
        calc_rssi_degradation = None


def natural_sort_key(p: Path):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', p.name)]


def to_float(val: Any) -> Optional[float]:
    """Safely parses numbers from float, int, or formatted strings (e.g. '−39*', '27.0%', '-48.4 dBm')."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if np.isnan(val):
            return None
        return float(val)
    
    s = str(val).strip()
    # Normalize unicode minus, degree, asterisks, units, and percentage signs
    s = s.replace('−', '-').replace('*', '').replace('%', '')
    s = s.replace('dBm', '').replace('dB', '').replace('Mbps', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def format_cell(val: Optional[float], is_los_rssi: bool = False) -> str:
    """Formats numeric values with 1 decimal place, or integer for whole LOS RSSI."""
    if val is None:
        return "N/A"
    # Integer formatting for whole-number LOS RSSI (e.g., -39 or -19)
    if is_los_rssi and abs(val - round(val)) < 1e-4:
        return f"{int(round(val))}"
    return f"{val:.1f}"


def generate_table_image(headers: List[str], rows: List[List[Any]], out_path: Path):
    header_map = {
        "Environmental Factor": "Environmental\nFactor",
        "Scenarios Included": "Scenarios\nIncluded",
        "2.4 GHz Mean Deg (%)": "2.4 GHz\nMean\nDeg (%)",
        "5 GHz Mean Deg (%)": "5 GHz\nMean\nDeg (%)",
        "6 GHz Mean Deg (%)": "6 GHz\nMean\nDeg (%)",
        "MLO Mean Deg (%)": "MLO\nMean\nDeg (%)",
        "Most Resilient Band": "Most\nResilient\nBand",
        "Max Signal Attenuation (dB)": "Max Signal\nAttenuation\n(dB)",
        "Observed MLO Fallback Behaviour": "Observed MLO\nFallback\nBehaviour",
    }
    wrapped_headers = [header_map.get(h, textwrap.fill(h, width=10, break_long_words=False)) for h in headers]

    # Rebalance column widths: widen numeric/band/attenuation columns slightly and expand canvas
    col_widths = [0.13, 0.19, 0.075, 0.075, 0.075, 0.075, 0.08, 0.09, 0.21]

    wrap_widths = {
        0: 16,  # Environmental Factor
        1: 24,  # Scenarios Included
        2: 10,  # 2.4 GHz
        3: 10,  # 5 GHz
        4: 10,  # 6 GHz
        5: 10,  # MLO Mean Deg (%)
        6: 12,  # Most Resilient Band
        7: 12,  # Max Signal Attenuation
        8: 24,  # Observed MLO Fallback Behaviour
    }

    wrapped_rows = []
    for row in rows:
        wrapped_row = []
        for i, cell in enumerate(row):
            w = wrap_widths.get(i, 15)
            text = str(cell) if cell is not None else ""
            lines = [
                textwrap.fill(line, width=w, break_long_words=False, break_on_hyphens=False)
                for line in text.split("\n")
            ]
            wrapped_row.append("\n".join(lines))
        wrapped_rows.append(wrapped_row)

    # Size figure specifically to fit the table tightly without large blank margins
    fig, ax = plt.subplots(figsize=(13.5, 7.8))
    ax.axis('tight')
    ax.axis('off')

    table = ax.table(
        cellText=wrapped_rows,
        colLabels=wrapped_headers,
        colWidths=col_widths,
        bbox=[0.0, 0.0, 1.0, 0.92],
        loc='center',
        cellLoc='center',
    )
    table.auto_set_font_size(False)

    for (i, j), cell in table.get_celld().items():
        if i == 0:
            # Slightly smaller header font and narrower wrap prevents adjacent header collision
            cell.set_text_props(weight='bold', fontsize=8.5)
            cell.set_facecolor('#d3d3d3')
        else:
            cell.set_text_props(fontsize=9.5)
        cell.set_edgecolor('black')
        cell.set_linewidth(0.8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ax.set_title("Cross-scenario Degradation by Environmental Factor", fontweight="bold", fontsize=13, pad=12)
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.08)
    plt.close()


def main():
    if load_scenario_data is None or get_freq_stats is None:
        print("Error: Could not import 'wifi7_pipeline' modules from ./src.")
        print("Please ensure this script is placed in the project root directory alongside 'src/'.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Wi-Fi 7 Cross-Scenario Degradation Summary Table Generator")
    parser.add_argument("--dir", "-d", default=str(ROOT_DIR / "compiled_data"), help="Path to compiled_data directory (default: ./compiled_data)")
    parser.add_argument("--tp-source", "-t", choices=['1', '2'], help="1 for iPerf logs, 2 for Wireshark pcap (summed packet sizes)")
    parser.add_argument("--csv", "-o", help="Optional path to export table as a CSV file")
    args = parser.parse_args()

    base_dir = Path(args.dir).resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Error: Base directory '{base_dir}' does not exist.")
        sys.exit(1)

    scenarios = [d for d in base_dir.iterdir() if d.is_dir()]
    if not scenarios:
        print(f"Error: No scenario directories found in '{base_dir}'.")
        sys.exit(1)

    scenarios = sorted(scenarios, key=natural_sort_key)

    summary_dir = (ROOT_DIR / "summary_tables").resolve()
    state_file = summary_dir / "summary_state.json"
    img_file = summary_dir / "summary_table.png"

    if state_file.exists():
        if sys.stdin.isatty():
            print("\nA previous summary table was found:")
            print("  1. Update 'Observed MLO Fallback Behaviour' and regenerate image")
            print("  2. Regenerate image directly from existing JSON")
            print("  3. Recalculate data from scratch")
            ans = input("Select an option [1/2/3] (default 2): ").strip().lower()

            if ans in ['1', 'u', 'y']:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                headers = state.get('headers', [])
                table_rows = state.get('rows', [])
                
                print("\nEnter the MLO Fallback Behaviour for each group (press Enter to keep existing):")
                for row in table_rows:
                    env_factor = row[0]
                    current_val = row[-1]
                    new_val = input(f"  {env_factor} [{current_val}]: ").strip()
                    if new_val:
                        row[-1] = new_val
                        
                with open(state_file, 'w') as f:
                    json.dump({'headers': headers, 'rows': table_rows}, f, indent=4)
                    
                generate_table_image(headers, table_rows, img_file)
                print(f"\n[+] Updated table image saved to {img_file}")

                if args.csv:
                    import csv
                    csv_path = Path(args.csv).resolve()
                    with csv_path.open('w', newline='', encoding='utf-8') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow(headers)
                        writer.writerows(table_rows)
                    print(f"[+] Saved summary CSV to: {csv_path}")
                sys.exit(0)
            elif ans in ['2', 'r', '']:
                with open(state_file, 'r') as f:
                    state = json.load(f)

                headers = state.get('headers', [])
                table_rows = state.get('rows', [])

                generate_table_image(headers, table_rows, img_file)
                print(f"\n[+] Regenerated table image from JSON saved to {img_file}")

                if args.csv:
                    import csv
                    csv_path = Path(args.csv).resolve()
                    with csv_path.open('w', newline='', encoding='utf-8') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow(headers)
                        writer.writerows(table_rows)
                    print(f"[+] Saved summary CSV to: {csv_path}")
                sys.exit(0)
            else:
                print("Proceeding to recalculate data from scratch...\n")

    if args.tp_source:
        tp_source = args.tp_source
    elif sys.stdin.isatty():
        choice = input("\nCalculate throughput from:\n  1. iPerf logs\n  2. Wireshark pcap (summed packet sizes)\nSelection [1/2] (default 1): ").strip()
        tp_source = choice if choice in ['1', '2'] else '1'
    else:
        tp_source = '1'

    source_label = "iPerf logs" if tp_source == '1' else "Wireshark pcap"
    print(f"\nAggregating across {len(scenarios)} scenarios using throughput from {source_label}...\n")

    GROUPS = [
        ("High User Density / Contention", ["mojo", "librarby"], "NONE"),
        ("Structural / Material Blockage", ["artsblock_concrete", "backrooms", "wg403_vroom", "ws200_switched_off"], "NONE"),
        ("Specular Reflection (Glass)", ["wh_elevator_glassish", "we_lvl3_hallway"], "NONE"),
        ("Electromagnetic Interference", ["microwave_on", "ws200_switched_on", "studio"], "NONE"),
        ("Extreme Multipath (Faraday)", ["ws_5_to_4_elevator"], "NONE"),
        ("Dynamic Mobility / Roaming", ["wz300_escalator", "wzlvl3_esc_onlvl3"], "NONE"),
        ("Long Distance / Path Loss (FSPL)", ["busstop"], "NONE"),
        ("Acoustic / Localized Obstruction", ["wz400_quiet_room", "wz_lvl9_meetingroom"], "NONE")
    ]

    PRETTY_NAMES = {
        "mojo": "Mojo Cafe",
        "librarby": "AUT Library",
        "artsblock_concrete": "Between Concrete Floors",
        "backrooms": "Underground Concrete Corner",
        "wg403_vroom": "Lecture Hall",
        "ws200_switched_off": "Server Rack (Off)",
        "wh_elevator_glassish": "Glass Elevator",
        "we_lvl3_hallway": "Hallway with Glass",
        "microwave_on": "Microwave",
        "ws200_switched_on": "Server Rack (On)",
        "studio": "Recording Studio",
        "ws_5_to_4_elevator": "Metal Elevator",
        "wz300_escalator": "Below Escalator",
        "wzlvl3_esc_onlvl3": "Next to Escalator",
        "busstop": "Bus Station",
        "wz400_quiet_room": "Quiet Room",
        "wz_lvl9_meetingroom": "Meeting Room"
    }

    group_scenarios = {g[0]: [] for g in GROUPS}
    scenarios_used = 0

    for scenario_dir in scenarios:
        name_lower = scenario_dir.name.lower()
        for g_name, keywords, _ in GROUPS:
            if any(kw in name_lower for kw in keywords):
                group_scenarios[g_name].append(scenario_dir)
                scenarios_used += 1
                break

    headers = [
        "Environmental Factor",
        "Scenarios Included",
        "2.4 GHz Mean Deg (%)",
        "5 GHz Mean Deg (%)",
        "6 GHz Mean Deg (%)",
        "MLO Mean Deg (%)",
        "Most Resilient Band",
        "Max Signal Attenuation (dB)",
        "Observed MLO Fallback Behaviour"
    ]

    table_rows = []

    for g_name, keywords, mlo_behav in GROUPS:
        scens = group_scenarios[g_name]
        if not scens:
            continue

        band_degs = {'24': [], '5': [], '6': [], 'mlo': []}
        all_rssi_drops = []
        scen_names = []

        for scenario_dir in scens:
            scen_names.append(PRETTY_NAMES.get(scenario_dir.name.lower(), scenario_dir.name))
            raw_data = load_scenario_data(scenario_dir)
            if not raw_data:
                continue

            if tp_source == '2':
                for d in raw_data:
                    d['throughput'] = d.get('wireshark_throughput', [])

            for f in ['24', '5', '6', 'mlo']:
                try:
                    stats = get_freq_stats(f, raw_data)
                except Exception:
                    continue

                if not stats:
                    continue

                # TP Degradation
                deg_tp = to_float(stats.get('deg_tp'))
                if deg_tp is None:
                    los_tp = to_float(stats.get('tp_los', [0]*6)[2]) if 'tp_los' in stats and len(stats['tp_los'])>=3 else None
                    prop_tp = to_float(stats.get('tp_prop', [0]*6)[2]) if 'tp_prop' in stats and len(stats['tp_prop'])>=3 else None
                    if los_tp and prop_tp is not None and los_tp > 0:
                        deg_tp = ((los_tp - prop_tp) / los_tp) * 100.0
                
                if deg_tp is not None and not np.isnan(deg_tp):
                    band_degs[f].append(deg_tp)

                # RSSI Degradation
                deg_rssi = None
                for k in ['deg_rssi_pct', 'deg_rssi', 'deg_dbm', 'rssi_deg']:
                    if k in stats and stats[k] is not None:
                        val = to_float(stats[k])
                        if val is not None:
                            deg_rssi = val
                            break

                if deg_rssi is None and calc_rssi_degradation is not None:
                    los_rssi = to_float(stats.get('dbm_los', [0]*6)[3]) if 'dbm_los' in stats and len(stats['dbm_los'])>=4 else None
                    prop_rssi = to_float(stats.get('dbm_prop', [0]*6)[3]) if 'dbm_prop' in stats and len(stats['dbm_prop'])>=4 else None
                    if los_rssi is not None and prop_rssi is not None:
                        try:
                            deg_rssi = to_float(calc_rssi_degradation(los_rssi, prop_rssi))
                        except Exception:
                            pass

                if deg_rssi is not None and not np.isnan(deg_rssi):
                    all_rssi_drops.append(deg_rssi)

        # Calculate group aggregates
        mean_band_degs = {}
        for f in ['24', '5', '6', 'mlo']:
            if band_degs[f]:
                mean_band_degs[f] = float(np.mean(band_degs[f]))
            else:
                mean_band_degs[f] = None

        most_resilient = "None"
        valid_resilience_bands = {k: v for k, v in mean_band_degs.items() if v is not None and k != 'mlo'}
        if valid_resilience_bands:
            best_band = min(valid_resilience_bands, key=valid_resilience_bands.get)
            most_resilient = "2.4 GHz" if best_band == '24' else f"{best_band} GHz"

        max_rssi_drop = float(np.max(all_rssi_drops)) if all_rssi_drops else None

        def fmt_deg(val):
            return f"{val:.1f}%" if val is not None else "N/A"

        row = [
            g_name,
            ", ".join(scen_names),
            fmt_deg(mean_band_degs['24']),
            fmt_deg(mean_band_degs['5']),
            fmt_deg(mean_band_degs['6']),
            fmt_deg(mean_band_degs['mlo']),
            most_resilient,
            f"{max_rssi_drop:.1f} dB" if max_rssi_drop is not None else "N/A",
            mlo_behav
        ]
        table_rows.append(row)

    summary_dir.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump({'headers': headers, 'rows': table_rows}, f, indent=4)
        
    generate_table_image(headers, table_rows, img_file)
    print(f"\n[+] Processing complete! (Grouped {scenarios_used} matching scenarios)")
    print(f"[+] Saved table JSON state to: {state_file}")
    print(f"[+] Saved table image to: {img_file}")

    # Optional CSV export
    if args.csv:
        import csv
        csv_path = Path(args.csv).resolve()
        with csv_path.open('w', newline='', encoding='utf-8') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(headers)
            writer.writerows(table_rows)
        print(f"[+] Saved summary CSV to: {csv_path}")


if __name__ == "__main__":
    main()
