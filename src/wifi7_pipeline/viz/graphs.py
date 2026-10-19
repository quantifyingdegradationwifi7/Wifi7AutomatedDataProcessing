from __future__ import annotations

import collections
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

from ..core.stats import calc_stats, calc_throughput_degradation, calc_rssi_degradation
from ..core.transforms import apply_smoothing, bin_and_aggregate_data


def get_band_from_diag(diag_str: str) -> str:
    import re
    if "MHz" in diag_str:
        m = re.search(r' (\d{4})MHz', diag_str)
        if m:
            freq = int(m.group(1))
            if 2400 <= freq < 2500: return '2.4GHz'
            if 5000 <= freq < 5900: return '5GHz'
            if 5900 <= freq < 7200: return '6GHz'
    m = re.search(r'Ch (\d+)', diag_str)
    if m:
        ch = int(m.group(1))
        if ch <= 14: return '2.4GHz'
        elif 36 <= ch <= 165: return '5GHz'
        else: return '6GHz'
    return 'Unknown'


def sort_key(name: str) -> int:
    score = 0
    name_l = name.lower()
    
    if 'los' in name_l:
        score += 0
    else:
        score += 100000
        
    if 'mlo' in name_l:
        score += 40000
        if '2.4ghz' in name_l:
            score += 1000
        elif '5ghz' in name_l:
            score += 2000
        elif '6ghz' in name_l:
            score += 3000
        elif 'unknown' in name_l:
            score += 4000
    elif '24' in name_l or '2.4' in name_l:
        score += 10000
    elif '5' in name_l:
        score += 20000
    elif '6' in name_l:
        score += 30000
        
    import re
    m = re.search(r'r_?(\d+)', name_l)
    if m:
        score += int(m.group(1))
        
    return score


def format_key_name(key: str) -> str:
    parts = key.lower().split('_')
    scenario = "LOS" if parts[0] == 'los' else "Scenario"
    if len(parts) > 1:
        freq = parts[1]
        if freq == '24': freq = '2.4GHz'
        elif freq == '5': freq = '5GHz'
        elif freq == '6': freq = '6GHz'
        elif freq == 'mlo': freq = 'MLO'
        else: freq = f"{freq}GHz"
    else:
        freq = ""
        
    suffix = ""
    band_suffix = ""
    for p in parts[2:]:
        if 'ghz' in p:
            band_suffix = f" ({p.replace('ghz', ' GHz')})"
        elif p.startswith('r') and p[1:].isdigit():
            suffix = f" (R{p[1:]})"
            
    return f"{scenario} {freq}{band_suffix}{suffix}".strip()


def generate_and_save_graph(
        selected_scenario_name: str,
        raw_data: list[dict[str, str | float | list[tuple[float, float | int]]]],
        freq_list: list[str],
        gtype: str,
        grouping_pref: str,
        agg_method: str,
        smoothing_pref: str,
        layout: str,
        output_path: Path,
        show: bool=False,
        custom_height: float | None = None,
        split_mlo: bool = False,
        skip_unknown: bool = False
    ) -> bool:
    
    los_durs = []
    proper_durs = []
    
    for d in raw_data:
        if d['throughput']:
            m_time = max((t for t, v in d['throughput']), default=0)
            if d['scenario_type'] == 'los':
                los_durs.append(m_time)
            elif d['scenario_type'] == 'proper':
                proper_durs.append(m_time)
                
    los_dur_str = f"{np.mean(los_durs):.1f}s" if los_durs else "N/A"
    proper_dur_str = f"{np.mean(proper_durs):.1f}s" if proper_durs else "N/A"
    dur_info = f"Avg LOS Test Duration: {los_dur_str} | Avg Scenario Test Duration: {proper_dur_str}"

    data_store: dict[str, dict[str, list]] = collections.defaultdict(
        lambda: {'throughput': [], 'dbm': [], 'diag_strs': set(), 'noise_rates': []}
    )
    
    for d in raw_data:
        if d['freq'] not in freq_list:
            continue
        target_key = d['group_name'] if grouping_pref in ['average', 'groupings'] else d['test_name']
        
        if split_mlo and d['freq'] == 'mlo':
            band = get_band_from_diag(d['diag_str'])
            if skip_unknown and band == 'Unknown':
                continue
            target_key = f"{target_key}_{band}"

        data_store[target_key]['throughput'].extend(d['throughput'])
        data_store[target_key]['dbm'].extend(d['dbm'])
        if d['diag_str']:
            data_store[target_key]['diag_strs'].add(d['diag_str'])
        data_store[target_key]['noise_rates'].append(d['noise_rate'])

    if not data_store:
        return False

    global_max_tp = 0
    for key, data in data_store.items():
        if data['throughput']:
            m_tp = max((v for t, v in data['throughput']), default=0)
            if m_tp > global_max_tp:
                global_max_tp = m_tp
                
    global_max_tp = math.ceil(global_max_tp / 100.0) * 100 if global_max_tp > 0 else 100

    keys = sorted(list(data_store.keys()), key=sort_key)
    
    deg_strs = []
    for f in freq_list:
        los_tp_f = []
        prop_tp_f = []
        los_dbm_f = []
        prop_dbm_f = []
        for d in raw_data:
            if d['freq'] == f:
                if d['scenario_type'] == 'los':
                    los_tp_f.extend([v for t, v in d['throughput']])
                    los_dbm_f.extend([v for t, v in d['dbm']])
                elif d['scenario_type'] == 'proper':
                    prop_tp_f.extend([v for t, v in d['throughput']])
                    prop_dbm_f.extend([v for t, v in d['dbm']])
                    
        if los_tp_f or prop_tp_f:
            med_los_tp = calc_stats(los_tp_f)['median'] if los_tp_f else 0.0
            med_prop_tp = calc_stats(prop_tp_f)['median'] if prop_tp_f else 0.0
            deg_tp = calc_throughput_degradation(med_los_tp, med_prop_tp)
            
            med_los_dbm = calc_stats(los_dbm_f, is_dbm=True)['median'] if los_dbm_f else 0.0
            med_prop_dbm = calc_stats(prop_dbm_f, is_dbm=True)['median'] if prop_dbm_f else 0.0
            deg_dbm = calc_rssi_degradation(med_los_dbm, med_prop_dbm)
            
            fname = '2.4GHz' if f == '24' else ('MLO' if f == 'mlo' else f"{f}GHz")
            deg_strs.append(f"{fname} (TP: {deg_tp:.1f}%, RSSI: {deg_dbm:.1f} dB)")
            
    if len(deg_strs) > 2:
        mid = math.ceil(len(deg_strs) / 2)
        deg_info = "Degradations: " + " | ".join(deg_strs[:mid]) + "\n" + " | ".join(deg_strs[mid:])
    else:
        deg_info = "Degradations: " + " | ".join(deg_strs) if deg_strs else "Degradations: N/A"
    
    if gtype == 'line':
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        fig.suptitle(f"Wi-Fi 7 Test Results: {selected_scenario_name} (Line Graph)\n{dur_info}\n{deg_info}")
        
        for key in keys:
            data = data_store[key]
            display_name = format_key_name(key)
            diag_info = (" | " + ", ".join(data['diag_strs'])) if data['diag_strs'] else ""
            noise_info = f" | Noise: {np.mean(data['noise_rates']):.1f} pkt/s" if data['noise_rates'] else ""
            label_text = f"{display_name}{diag_info}{noise_info}"

            if data['throughput']:
                x_tp, y_tp = bin_and_aggregate_data(data['throughput'], bin_size=1.0, method=agg_method, missing_value=0.0)
                if smoothing_pref == 'yes':
                    y_tp = apply_smoothing(y_tp, window_size=3)
                ax1.plot(x_tp, y_tp, label=label_text)
                
            if data['dbm']:
                x_dbm, y_dbm = bin_and_aggregate_data(data['dbm'], bin_size=0.5, method=agg_method, missing_value=np.nan)
                if smoothing_pref == 'yes':
                    y_dbm = apply_smoothing(y_dbm, window_size=6)
                ax2.plot(x_dbm, y_dbm, label=label_text)
                
        ax1.set_ylim(0, global_max_tp)
        ax2.set_ylim(-110, 0)
        ax1.set_xlabel("Test Time (s)")
        ax1.set_ylabel("Throughput (Mbps)")
        ax1.set_title("Throughput Timeline")
        ax1.legend(fontsize='small')
        ax1.grid(True)
        
        ax2.set_xlabel("Test Time (s)")
        ax2.set_ylabel("Signal Strength (dBm)")
        ax2.set_title("RSSI Timeline")
        ax2.legend(fontsize='small')
        ax2.grid(True)

    elif gtype == 'bar':
        fig, ax1 = plt.subplots(figsize=(18, 8))
        ax2 = ax1.twinx()
        fig.suptitle(f"Wi-Fi 7 Test Results: {selected_scenario_name} (Bar Graph)\n{dur_info}\n{deg_info}")
        
        tp_means = []
        dbm_means = []
        labels = []
        tp_colors = []
        dbm_colors = []
        
        for key in keys:
            data = data_store[key]
            display_name = format_key_name(key)
            diag_info = ("\n" + ", ".join(data['diag_strs'])) if data['diag_strs'] else ""
            noise_info = f"\nNoise: {np.mean(data['noise_rates']):.1f} pkt/s" if data['noise_rates'] else ""
            labels.append(f"{display_name}{diag_info}{noise_info}")

            tp_vals = [v for t, v in data['throughput']]
            dbm_vals = [v for t, v in data['dbm']]
            tp_means.append(np.mean(tp_vals) if tp_vals else 0)
            if dbm_vals:
                mw = [10**(v/10.0) for v in dbm_vals]
                dbm_means.append(10.0 * math.log10(np.mean(mw)) if np.mean(mw) > 0 else -100.0)
            else:
                dbm_means.append(0)
            
            is_los = 'los' in key.lower()
            tp_colors.append('cornflowerblue' if is_los else 'darkblue')
            dbm_colors.append('sandybrown' if is_los else 'saddlebrown')
            
        if layout == 'metric':
            width_tp = 0.6
            width_dbm = 0.6
            pos_tp = np.arange(len(keys), dtype=float)
            pos_dbm = np.arange(len(keys), dtype=float) + len(keys) + 1
            all_x = np.concatenate([pos_tp, pos_dbm])
            all_labels = []
            for l in labels:
                parts = l.split('\n', 1)
                all_labels.append(parts[0] + " (TP)" + ("\n" + parts[1] if len(parts) > 1 else ""))
            for l in labels:
                parts = l.split('\n', 1)
                all_labels.append(parts[0] + " (RSSI)" + ("\n" + parts[1] if len(parts) > 1 else ""))
        else:
            width_tp = 0.35
            width_dbm = 0.35
            x_pos = np.arange(len(keys), dtype=float)
            pos_tp = x_pos - width_tp/2
            pos_dbm = x_pos + width_dbm/2
            all_x = x_pos
            all_labels = labels
        
        ax1.bar(pos_tp, tp_means, width_tp, color=tp_colors, alpha=0.9, label='Throughput')
        ax2.bar(pos_dbm, dbm_means, width_dbm, color=dbm_colors, alpha=0.9, label='RSSI')
        
        ax1.set_xlim(min(all_x) - 1, max(all_x) + 1)
        ax1.set_ylim(0, global_max_tp)
        ax2.set_ylim(-110, 0)
        ax1.set_xticks(all_x)
        ax1.set_xticklabels(all_labels, rotation=45, ha='right')
        ax1.set_ylabel("Average Throughput (Mbps)", color='darkblue', fontweight='bold')
        ax2.set_ylabel("Average Signal Strength (dBm)", color='saddlebrown', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='darkblue')
        ax2.tick_params(axis='y', labelcolor='saddlebrown')
        ax1.grid(axis='y', alpha=0.5)
        
        legend_handles = [
            mpatches.Patch(color='cornflowerblue', label='LOS Throughput'),
            mpatches.Patch(color='darkblue', label='Scenario Throughput'),
            mpatches.Patch(color='sandybrown', label='LOS RSSI'),
            mpatches.Patch(color='saddlebrown', label='Scenario RSSI')
        ]
        ax1.legend(handles=legend_handles, loc='upper left', bbox_to_anchor=(1.05, 1))

    elif gtype == 'box':
        fig, ax1 = plt.subplots(figsize=(20, 10))
        ax2 = ax1.twinx()
        fig.suptitle(f"Wi-Fi 7 Test Results: {selected_scenario_name} (Box Plot)\n{dur_info}\n{deg_info}")
        
        tp_data_list = []
        dbm_data_list = []
        labels = []
        tp_legend_text = []
        dbm_legend_text = []
        
        for key in keys:
            data = data_store[key]
            display_name = format_key_name(key)
            diag_info = ("\n" + ", ".join(data['diag_strs'])) if data['diag_strs'] else ""
            noise_info = f"\nNoise: {np.mean(data['noise_rates']):.1f} pkt/s" if data['noise_rates'] else ""
            labels.append(f"{display_name}{diag_info}{noise_info}")
            
            tp_vals = [v for t, v in data['throughput']]
            dbm_vals = [v for t, v in data['dbm']]
            
            tp_data_list.append(tp_vals if tp_vals else [0])
            dbm_data_list.append(dbm_vals if dbm_vals else [0])
            
            def calc_box_stats(vals, is_dbm=False):
                if not vals: return 0,0,0,0,0,0,0,0
                mi = np.min(vals)
                ma = np.max(vals)
                if is_dbm:
                    mw = [10**(v/10.0) for v in vals]
                    me = 10.0 * math.log10(np.mean(mw)) if np.mean(mw) > 0 else -100.0
                else:
                    me = np.mean(vals)
                md = np.median(vals)
                q1 = np.percentile(vals, 25)
                q3 = np.percentile(vals, 75)
                iqr = q3 - q1
                ran = ma - mi
                return mi, q1, md, me, q3, ma, iqr, ran
            
            t_mi, t_q1, t_md, t_me, t_q3, t_ma, t_iqr, t_ran = calc_box_stats(tp_vals, is_dbm=False)
            tp_legend_text.append(f"{display_name} (TP)\n- Min: {t_mi:.1f}\n- Q1: {t_q1:.1f}\n- Med: {t_md:.1f}\n- Mean: {t_me:.1f}\n- Q3: {t_q3:.1f}\n- Max: {t_ma:.1f}\n- IQR: {t_iqr:.1f}\n- Rng: {t_ran:.1f}")

            d_mi, d_q1, d_md, d_me, d_q3, d_ma, d_iqr, d_ran = calc_box_stats(dbm_vals, is_dbm=True)
            dbm_legend_text.append(f"{display_name} (RSSI)\n- Min: {d_mi:.1f}\n- Q1: {d_q1:.1f}\n- Med: {d_md:.1f}\n- Mean: {d_me:.1f}\n- Q3: {d_q3:.1f}\n- Max: {d_ma:.1f}\n- IQR: {d_iqr:.1f}\n- Rng: {d_ran:.1f}")
            
        if layout == 'metric':
            width_tp = 0.6
            width_dbm = 0.6
            pos_tp = np.arange(len(keys), dtype=float)
            pos_dbm = np.arange(len(keys), dtype=float) + len(keys) + 1
            all_x = np.concatenate([pos_tp, pos_dbm])
            all_labels = []
            for l in labels:
                parts = l.split('\n', 1)
                all_labels.append(parts[0] + " (TP)" + ("\n" + parts[1] if len(parts) > 1 else ""))
            for l in labels:
                parts = l.split('\n', 1)
                all_labels.append(parts[0] + " (RSSI)" + ("\n" + parts[1] if len(parts) > 1 else ""))
        else:
            width_tp = 0.35
            width_dbm = 0.35
            x_pos = np.arange(len(keys), dtype=float)
            pos_tp = x_pos - width_tp/2
            pos_dbm = x_pos + width_dbm/2
            all_x = x_pos
            all_labels = labels
        
        meanprops = dict(marker='D', markeredgecolor='black', markerfacecolor='red', markersize=6)
        medianprops = dict(color='magenta', linewidth=2)
        
        bp1 = ax1.boxplot(tp_data_list, positions=pos_tp, widths=width_tp-0.05,
                          patch_artist=True, showmeans=True, showfliers=True,
                          meanprops=meanprops, medianprops=medianprops)
                          
        bp2 = ax2.boxplot(dbm_data_list, positions=pos_dbm, widths=width_dbm-0.05,
                          patch_artist=True, showmeans=True, showfliers=True,
                          meanprops=meanprops, medianprops=medianprops)
                          
        tp_edge_colors = []
        dbm_edge_colors = []
        
        for i, key in enumerate(keys):
            is_los = 'los' in key.lower()
            c_tp = 'cornflowerblue' if is_los else 'darkblue'
            c_dbm = 'sandybrown' if is_los else 'saddlebrown'
            
            tp_edge_colors.append(c_tp)
            dbm_edge_colors.append(c_dbm)
            
            bp1['boxes'][i].set_facecolor('white')
            bp1['boxes'][i].set_edgecolor(c_tp)
            bp1['boxes'][i].set_linewidth(1.5)
            bp1['whiskers'][2*i].set_color(c_tp)
            bp1['whiskers'][2*i+1].set_color(c_tp)
            bp1['caps'][2*i].set_color(c_tp)
            bp1['caps'][2*i+1].set_color(c_tp)
            
            bp2['boxes'][i].set_facecolor('white')
            bp2['boxes'][i].set_edgecolor(c_dbm)
            bp2['boxes'][i].set_linewidth(1.5)
            bp2['whiskers'][2*i].set_color(c_dbm)
            bp2['whiskers'][2*i+1].set_color(c_dbm)
            bp2['caps'][2*i].set_color(c_dbm)
            bp2['caps'][2*i+1].set_color(c_dbm)
            
        ax1.set_xlim(min(all_x) - 1, max(all_x) + 1)
        ax1.set_ylim(0, global_max_tp)
        ax2.set_ylim(-110, 0)
        ax1.set_xticks(all_x)
        ax1.set_xticklabels(all_labels, rotation=45, ha='right')
        ax1.set_ylabel("Throughput (Mbps)", color='darkblue', fontweight='bold')
        ax2.set_ylabel("Signal Strength (dBm)", color='saddlebrown', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='darkblue')
        ax2.tick_params(axis='y', labelcolor='saddlebrown')
        ax1.grid(axis='y', alpha=0.5)
        
        mean_line = mlines.Line2D([], [], color='red', marker='D', linestyle='None', markersize=6, markeredgecolor='black', label='Mean')
        median_line = mlines.Line2D([], [], color='magenta', linewidth=2, label='Median')
        
        handles = [mean_line, median_line]
        for text, c in zip(tp_legend_text, tp_edge_colors):
            handles.append(mpatches.Patch(facecolor='white', edgecolor=c, linewidth=1.5, label=text))
        for text, c in zip(dbm_legend_text, dbm_edge_colors):
            handles.append(mpatches.Patch(facecolor='white', edgecolor=c, linewidth=1.5, label=text))
            
        cols = max(2, min(5, len(keys)))
        ax1.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.05, 1), ncol=cols, fontsize='x-small')

    elif gtype == 'overview':
        h = custom_height if custom_height is not None else 6.0
        fig, axs = plt.subplots(2, 4, figsize=(12, h), sharey='row', gridspec_kw={'wspace': 0.25, 'hspace': 0.45})
        
        freq_cols = ['24', '5', '6', 'mlo']
        col_titles = ["2.4 GHz", "5 GHz", "6 GHz", "MLO (2.4, 5, and 6 GHz)"]
        
        for c, f in enumerate(freq_cols):
            ax_tp = axs[0, c]
            ax_dbm = axs[1, c]
            
            f_keys = [k for k in keys if k.split('_')[1] == f]
            if skip_unknown:
                f_keys = [k for k in f_keys if 'unknown' not in k.lower()]
            
            tp_data_list = []
            dbm_data_list = []
            tp_colors = []
            dbm_colors = []
            
            for k in f_keys:
                data = data_store[k]
                tp_vals = [v for t, v in data['throughput']]
                dbm_vals = [v for t, v in data['dbm']]
                tp_data_list.append(tp_vals if tp_vals else [0])
                dbm_data_list.append(dbm_vals if dbm_vals else [0])
                
                is_los = 'los' in k.lower()
                tp_colors.append('cornflowerblue' if is_los else 'darkblue')
                dbm_colors.append('sandybrown' if is_los else 'saddlebrown')
                
            if f_keys:
                pos = np.arange(len(f_keys), dtype=float)
                bp1 = ax_tp.boxplot(tp_data_list, positions=pos, widths=0.6,
                                  patch_artist=True, showmeans=False, showfliers=True)
                bp2 = ax_dbm.boxplot(dbm_data_list, positions=pos, widths=0.6,
                                   patch_artist=True, showmeans=False, showfliers=True)
                                   
                for i in range(len(f_keys)):
                    c_tp = tp_colors[i]
                    c_dbm = dbm_colors[i]
                    
                    bp1['boxes'][i].set_facecolor('white')
                    bp1['boxes'][i].set_edgecolor(c_tp)
                    bp1['boxes'][i].set_linewidth(1.5)
                    bp1['whiskers'][2*i].set_color(c_tp)
                    bp1['whiskers'][2*i+1].set_color(c_tp)
                    bp1['caps'][2*i].set_color(c_tp)
                    bp1['caps'][2*i+1].set_color(c_tp)
                    bp1['medians'][i].set_color(c_tp)
                    bp1['medians'][i].set_linewidth(1.5)
                    bp1['fliers'][i].set_markeredgecolor(c_tp)
                    
                    bp2['boxes'][i].set_facecolor('white')
                    bp2['boxes'][i].set_edgecolor(c_dbm)
                    bp2['boxes'][i].set_linewidth(1.5)
                    bp2['whiskers'][2*i].set_color(c_dbm)
                    bp2['whiskers'][2*i+1].set_color(c_dbm)
                    bp2['caps'][2*i].set_color(c_dbm)
                    bp2['caps'][2*i+1].set_color(c_dbm)
                    bp2['medians'][i].set_color(c_dbm)
                    bp2['medians'][i].set_linewidth(1.5)
                    bp2['fliers'][i].set_markeredgecolor(c_dbm)
                    
                los_keys = [(i, k) for i, k in enumerate(f_keys) if 'los' in k.lower()]
                exp_keys = [(i, k) for i, k in enumerate(f_keys) if 'los' not in k.lower()]
                
                y_offset_idx = 0
                for group_keys, group_name in [(los_keys, "LOS"), (exp_keys, "Experiment")]:
                    if not group_keys:
                        continue
                        
                    if group_name == "Experiment" and los_keys:
                        y_offset_idx += 1
                        
                    center_pos = sum(i for i, k in group_keys) / len(group_keys)
                    
                    # 1. Place "LOS" / "Experiment" above the top graph
                    ax_tp.text(center_pos, 1.04, group_name, ha='center', va='bottom', 
                               transform=ax_tp.get_xaxis_transform(), fontsize=12, fontweight='bold', clip_on=False)
                    
                    # 2. Place band labels and noise text below the top graph
                    if split_mlo and f == 'mlo':
                        for i, k in group_keys:
                            parts = k.split('_')
                            band_str = ""
                            short_band = ""
                            for p in parts[2:]:
                                if 'GHz' in p or 'ghz' in p.lower():
                                    band_str = p.replace('ghz', ' GHz').replace('GHz', ' GHz')
                                    short_band = p.lower().replace('ghz', '')
                            
                            if not band_str:
                                band_str = "Unknown"
                                short_band = "?"
                                
                            ax_tp.text(pos[i], -0.04, band_str, ha='center', va='top', 
                                       transform=ax_tp.get_xaxis_transform(), fontsize=10, clip_on=False)
                                       
                            noise_val = np.mean(data_store[k]['noise_rates']) if data_store[k]['noise_rates'] else 0.0
                            if len(group_keys) == 1:
                                noise_str = f"{noise_val:.0f} pkts/s noise"
                            else:
                                noise_str = f"{short_band}: {noise_val:.0f} pkts/s noise"
                            
                            y_pos = -0.11 - (y_offset_idx * 0.06)
                            ax_tp.text(center_pos, y_pos, noise_str, ha='center', va='top', 
                                       transform=ax_tp.get_xaxis_transform(), fontsize=10, clip_on=False)
                            y_offset_idx += 1
                    else:
                        noise_val = np.mean(data_store[group_keys[0][1]]['noise_rates']) if data_store[group_keys[0][1]]['noise_rates'] else 0.0
                        noise_str = f"{noise_val:.0f} pkts/s noise"
                        y_pos = -0.11 - (y_offset_idx * 0.06)
                        ax_tp.text(center_pos, y_pos, noise_str, ha='center', va='top', 
                                   transform=ax_tp.get_xaxis_transform(), fontsize=10, clip_on=False)
                        y_offset_idx += 1
                    
                last_los_idx = -1
                first_prop_idx = -1
                for i, k in enumerate(f_keys):
                    if 'los' in k.lower():
                        last_los_idx = max(last_los_idx, i)
                    else:
                        if first_prop_idx == -1:
                            first_prop_idx = i
                            
                if last_los_idx != -1 and first_prop_idx != -1 and last_los_idx < first_prop_idx:
                    sep_pos = (pos[last_los_idx] + pos[first_prop_idx]) / 2.0
                    ax_tp.axvline(x=sep_pos, color='darkgray', linestyle='--', linewidth=2, zorder=0)
                    ax_dbm.axvline(x=sep_pos, color='darkgray', linestyle='--', linewidth=2, zorder=0)
                    
                ax_tp.set_xlim(-0.5, len(f_keys) - 0.5)
                ax_dbm.set_xlim(-0.5, len(f_keys) - 0.5)
                
            # Reduced top padding since the text is no longer up there, makes the box plots taller/clearer
            ax_tp.set_ylim(0, global_max_tp * 1.10)
            ax_dbm.set_ylim(-110, 0)
            
            ax_tp.set_xticks([])
            ax_dbm.set_xticks([])
            
            ax_tp.set_title(col_titles[c], fontsize=14, fontweight='bold', pad=25)
            
            if c == 0:
                ax_tp.set_ylabel("Throughput (Mbps)", fontsize=12, fontweight='bold')
                ax_dbm.set_ylabel("RSSI (dBm)", fontsize=12, fontweight='bold')
                ax_tp.tick_params(axis='y', labelsize=10)
                ax_dbm.tick_params(axis='y', labelsize=10)
            else:
                ax_tp.tick_params(axis='y', which='both', length=0, labelsize=10)
                ax_dbm.tick_params(axis='y', which='both', length=0, labelsize=10)
                
            ax_tp.grid(axis='y', alpha=0.3)
            ax_dbm.grid(axis='y', alpha=0.3)

        los_tp_patch = mpatches.Patch(facecolor='white', edgecolor='cornflowerblue', linewidth=2, label='LOS Throughput')
        exp_tp_patch = mpatches.Patch(facecolor='white', edgecolor='darkblue', linewidth=2, label='Experiment Throughput')
        los_rssi_patch = mpatches.Patch(facecolor='white', edgecolor='sandybrown', linewidth=2, label='LOS RSSI')
        exp_rssi_patch = mpatches.Patch(facecolor='white', edgecolor='saddlebrown', linewidth=2, label='Experiment RSSI')
        fig.legend(handles=[los_tp_patch, exp_tp_patch, los_rssi_patch, exp_rssi_patch], loc='lower center', ncol=4, fontsize=14, bbox_to_anchor=(0.5, -0.05), frameon=False)

    plt.tight_layout()
    fig.savefig(output_path, bbox_inches='tight', dpi=400)
    
    if show:
        plt.show()
        
    plt.close(fig)
    return True