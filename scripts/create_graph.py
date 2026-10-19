#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in [str(ROOT_DIR), str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from wifi7_pipeline.core.scenario_io import load_scenario_data
from wifi7_pipeline.viz.graphs import generate_and_save_graph


def main():
    print("=== Wi-Fi 7 Test Grapher ===")
    
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
    print("  0. All scenarios (Bulk mode)")
        
    choice = input("\nSelect a scenario by number (or 0 for all): ").strip()
    try:
        scenario_idx = int(choice)
        if scenario_idx == 0:
            selected_scenarios = scenarios
        else:
            selected_scenarios = [scenarios[scenario_idx - 1]]
    except (ValueError, IndexError):
        print("Invalid selection. Quitting.")
        sys.exit(1)
        
    tp_source = input("\nCalculate throughput from:\n  1. iPerf logs\n  2. Wireshark pcap (summed packet sizes)\nSelection [1/2]: ").strip()
    
    mode = input("\nSelect Mode:\n  1. Interactive (choose options)\n  2. Do everything (generate and save all combinations)\nSelection [1/2]: ").strip()
    
    prefix_choice = input("\nPrefix output filenames with the scenario name? (y/n): ").strip().lower()
    use_prefix = (prefix_choice == 'y')

    if mode == '1':
        gtype = input("Graph type? (line/bar/box/overview): ").strip().lower()
        if gtype not in ['line', 'bar', 'box', 'overview']:
            print("Invalid graph type. Defaulting to line.")
            gtype = 'line'
            
        custom_height = None
        split_mlo = False
        skip_unknown = False
        if gtype == 'overview':
            h_input = input("Enter graph height in inches (or press Enter for auto): ").strip()
            if h_input:
                try:
                    custom_height = float(h_input)
                except ValueError:
                    print("Invalid height. Defaulting to auto.")
            split_mlo_input = input("Show when MLO operated on different frequencies? (y/n) [n]: ").strip().lower()
            split_mlo = (split_mlo_input == 'y')
            if split_mlo:
                skip_unknown_input = input("Skip 'Unknown' subcolumns? (y/n) [n]: ").strip().lower()
                skip_unknown = (skip_unknown_input == 'y')
            freq_list = ['24', '5', '6', 'mlo']
        else:
            freqs_input = input("Which frequencies to graph? (comma separated, e.g. 2.4, 5, 6, mlo): ").lower()
            freq_list = []
            for f in freqs_input.split(','):
                f = f.strip()
                if f == '2.4':
                    f = '24'
                freq_list.append(f)
            
        grouping_pref = 'individual'
        agg_method = 'mean'
        smoothing_pref = 'no'
        layout = 'test'
        
        if gtype == 'line':
            grouping_pref = input("Show every individual line or an average per grouping? (individual/average): ").strip().lower()
            if grouping_pref == 'average':
                agg_method = input("Based on mean or median? (mean/median): ").strip().lower()
            smoothing_pref = input("Use sliding window average smoothing? (yes/no): ").strip().lower()
        elif gtype in ['bar', 'box', 'overview']:
            grouping_pref = input("Average across individual tests or across groupings? (individual/groupings): ").strip().lower()
                
            if gtype in ['bar', 'box']:
                layout = input("Group layout by test type or metric? (test/metric): ").strip().lower()
                if layout not in ['test', 'metric']:
                    print("Invalid layout. Defaulting to test.")
                    layout = 'test'
            else:
                layout = 'test'

    for selected_scenario in selected_scenarios:
        print(f"\nLoading data for {selected_scenario.name} (this may take a moment)...")
        raw_data = load_scenario_data(selected_scenario)
        if not raw_data:
            print(f"No valid data found for {selected_scenario.name}. Skipping.")
            continue

        if tp_source == '2':
            for d in raw_data:
                d['throughput'] = d.get('wireshark_throughput', [])

        output_dir = selected_scenario / "graphs"
        output_dir.mkdir(exist_ok=True)
            
        if mode == '2':
            print(f"\nGenerating all possible combinations into {output_dir} ...")
            freq_combos = [['24'], ['5'], ['6'], ['mlo'], ['24', '5', '6', 'mlo']]
            
            for freqs in freq_combos:
                for grouping in ['individual', 'average']:
                    for smooth in ['yes', 'no']:
                        freq_str = "_".join(freqs)
                        filename = f"line_{grouping}_smooth_{smooth}_{freq_str}.png"
                        if use_prefix:
                            filename = f"{selected_scenario.name}_{filename}"
                        out_path = output_dir / filename
                        success = generate_and_save_graph(selected_scenario.name, raw_data, freqs, 'line', grouping, 'mean', smooth, 'test', out_path)
                        if success:
                            print(f"Saved: {filename}")
                            
            for freqs in freq_combos:
                for grouping in ['individual', 'groupings']:
                    layout_val = 'metric' if grouping == 'groupings' else 'test'
                    freq_str = "_".join(freqs)
                    filename = f"bar_{grouping}_{freq_str}.png"
                    if use_prefix:
                        filename = f"{selected_scenario.name}_{filename}"
                    out_path = output_dir / filename
                    success = generate_and_save_graph(selected_scenario.name, raw_data, freqs, 'bar', grouping, 'mean', 'no', layout_val, out_path)
                    if success:
                        print(f"Saved: {filename}")
                        
            for freqs in freq_combos:
                for grouping in ['individual', 'groupings']:
                    layout_val = 'metric' if grouping == 'groupings' else 'test'
                    freq_str = "_".join(freqs)
                    filename = f"box_{grouping}_{freq_str}.png"
                    if use_prefix:
                        filename = f"{selected_scenario.name}_{filename}"
                    out_path = output_dir / filename
                    success = generate_and_save_graph(selected_scenario.name, raw_data, freqs, 'box', grouping, 'mean', 'no', layout_val, out_path)
                    if success:
                        print(f"Saved: {filename}")
                        
            for grouping in ['individual', 'groupings']:
                filename = f"overview_{grouping}_all.png"
                if use_prefix:
                    filename = f"{selected_scenario.name}_{filename}"
                out_path = output_dir / filename
                success = generate_and_save_graph(selected_scenario.name, raw_data, ['24', '5', '6', 'mlo'], 'overview', grouping, 'mean', 'no', 'test', out_path, split_mlo=True)
                if success:
                    print(f"Saved: {filename}")

            print(f"\nAll graphs generated successfully for {selected_scenario.name}!")
            
        else:
            freq_str = "_".join(freq_list)
            if gtype == 'line':
                filename = f"line_{grouping_pref}_smooth_{smoothing_pref}_{freq_str}.png"
            elif gtype == 'bar':
                filename = f"bar_{grouping_pref}_{freq_str}.png"
            elif gtype == 'box':
                filename = f"box_{grouping_pref}_{freq_str}.png"
            elif gtype == 'overview':
                filename = f"overview_{grouping_pref}_{freq_str}.png"
            else:
                filename = f"custom_graph_{freq_str}.png"
                
            if use_prefix:
                filename = f"{selected_scenario.name}_{filename}"
                
            out_path = output_dir / filename
            
            print(f"Plotting and saving graph for {selected_scenario.name}...")
            show_plot = (len(selected_scenarios) == 1)
            ch = locals().get('custom_height', None)
            sm = locals().get('split_mlo', False)
            su = locals().get('skip_unknown', False)
            success = generate_and_save_graph(selected_scenario.name, raw_data, freq_list, gtype, grouping_pref, agg_method, smoothing_pref, layout, out_path, show=show_plot, custom_height=ch, split_mlo=sm, skip_unknown=su)
            
            if success:
                print(f"Saved custom graph to: {out_path}")
            else:
                print(f"No valid data found matching your query criteria for {selected_scenario.name}.")


if __name__ == "__main__":
    main()
