from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

import numpy as np


def get_time_range_from_logs(log_path: Path) -> tuple[float | None, float, list[tuple[float, float]]]:
    import collections
    start_epoch: float | None = None
    throughput_data: list[tuple[float, float]] = []
    max_end_time: float = 0.0

    date_regex = re.compile(r'^[a-zA-Z]{3} [a-zA-Z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2} \d{4}')
    raw_tp: list[tuple[float, float, float, bool]] = []

    try:
        with log_path.open('r', encoding='utf-8') as f:
            for line in f:
                if start_epoch is None:
                    match = date_regex.search(line)
                    if match:
                        date_str = re.sub(r'\s+', ' ', match.group())
                        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
                        start_epoch = dt.timestamp()

                if (
                    'sec' in line
                    and 'bits/sec' in line
                    and 'sender' not in line
                    and 'receiver' not in line
                ):
                    is_sum = '[SUM]' in line
                    parts = line.split()
                    try:
                        sec_idx = parts.index('sec')
                        interval_str = parts[sec_idx - 1]
                        start_sec, end_sec = map(float, interval_str.split('-'))
                        max_end_time = max(max_end_time, end_sec)

                        unit_idx = -1
                        for i, part in enumerate(parts):
                            if 'bits/sec' in part:
                                unit_idx = i
                                break

                        if unit_idx != -1:
                            bitrate = float(parts[unit_idx - 1])
                            unit = parts[unit_idx]
                            if 'Gbits' in unit:
                                bitrate *= 1000
                            elif 'Kbits' in unit:
                                bitrate /= 1000
                            raw_tp.append(((start_sec + end_sec) / 2.0, bitrate, end_sec - start_sec, is_sum))
                    except ValueError:
                        pass
    except Exception:
        pass

    if raw_tp:
        has_sum = any(is_sum for _, _, _, is_sum in raw_tp)
        filtered_by_stream = [item for item in raw_tp if item[3]] if has_sum else raw_tp
        
        durations = [round(dur, 2) for _, _, dur, _ in filtered_by_stream]
        if durations:
            mode_dur = collections.Counter(durations).most_common(1)[0][0]
            for midpoint, bitrate, dur, _ in filtered_by_stream:
                if 0.8 * mode_dur <= dur <= 1.2 * mode_dur:
                    throughput_data.append((midpoint, bitrate))

    return start_epoch, max_end_time, throughput_data


def get_csv_lines_from_time_range(
    csv_path: Path,
    start_epoch: float,
    duration: float,
) -> list[tuple[float, int, int]]:
    data: list[tuple[float, int, int]] = []
    if not csv_path.exists():
        return data

    try:
        with csv_path.open('r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)

            for parts in reader:
                if len(parts) >= 3:
                    try:
                        ts: float = float(parts[1])
                        dbm: int = int(parts[2])
                        packet_size = int(parts[3]) if len(parts) >= 4 and parts[3] else 0

                        if dbm < -100:
                            continue

                        rel_time: float = ts - start_epoch
                        if 0 <= rel_time <= duration:
                            data.append((rel_time, dbm, packet_size))
                    except ValueError:
                        continue
    except Exception:
        pass

    return data


def load_diagnostics(diagnostics_path: Path) -> list[dict[str, str | float]]:
    diag: list[dict[str, str | float]] = []
    if not diagnostics_path.exists():
        return diag

    try:
        with diagnostics_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('time') and row.get('time') != 'NAN':
                    diag.append({
                        'time': float(row['time']),
                        'channel': row.get('channel', ''),
                        'frequency': row.get('frequency', ''),
                        'width': row.get('width', ''),
                    })
    except Exception:
        pass

    return sorted(diag, key=lambda x: x['time'])


def get_diagnostic_info(
    diag_data: list[dict[str, str | float]],
    start_epoch: float,
) -> str:
    best_diag: dict[str, str | float] | None = None
    for d in diag_data:
        if not isinstance(d['time'], float):
            continue
        if d['time'] <= start_epoch:
            best_diag = d
        else:
            break
    if best_diag and best_diag['channel'] and best_diag['channel'] != 'NAN':
        freq_info = f" {best_diag['frequency']}MHz" if best_diag.get('frequency') and best_diag['frequency'] != 'NAN' else ""
        return f"Ch {best_diag['channel']} ({best_diag['width']}MHz){freq_info}"
    return ""


def load_scenario_data(
    selected_scenario: Path,
) -> list[dict[str, str | float | list[tuple[float, float | int]]]]:
    raw_data: list[dict[str, str | float | list[tuple[float, float | int]]]] = []
    diag_data = load_diagnostics(selected_scenario / 'diagnostics.csv')

    for log_file in selected_scenario.glob('*.log'):
        match = re.match(r'^([a-zA-Z]+)_([a-zA-Z0-9]+)_[a-zA-Z]_(\d+)', log_file.stem)
        if not match:
            continue

        scenario_type = match.group(1)
        freq = match.group(2)
        run = match.group(3)

        start_epoch, duration, tp_data = get_time_range_from_logs(log_file)
        if start_epoch is None:
            continue

        diag_str = get_diagnostic_info(diag_data, start_epoch)

        csv_filename = f'wireshark_{freq}_R{run}.csv'
        csv_path = selected_scenario / csv_filename
        csv_data = get_csv_lines_from_time_range(csv_path, start_epoch, duration)

        dbm_data_raw = [(t, dbm) for t, dbm, _ in csv_data]
        ws_pkt_data = [(t, size) for t, _, size in csv_data]

        dbm_data: list[tuple[float, float]] = []
        if dbm_data_raw or duration > 0:
            from .transforms import bin_and_aggregate_data
            x_dbm, y_dbm = bin_and_aggregate_data(dbm_data_raw, bin_size=0.5, method='mean', missing_value=-100.0, duration=duration)
            for t_val, v_val in zip(x_dbm, y_dbm):
                dbm_data.append((float(t_val), float(v_val)))

        ws_tp_data: list[tuple[float, float]] = []
        if ws_pkt_data or duration > 0:
            from .transforms import bin_and_aggregate_data

            x_ws, y_ws = bin_and_aggregate_data(ws_pkt_data, bin_size=0.5, method='sum_to_mbps', missing_value=0.0, duration=duration)
            for t_ws, v_ws in zip(x_ws, y_ws):
                ws_tp_data.append((float(t_ws), float(v_ws)))

        non_csv_filename = f'non_wireshark_{freq}_R{run}.csv'
        non_csv_path = selected_scenario / non_csv_filename
        non_csv_data = get_csv_lines_from_time_range(non_csv_path, start_epoch, duration)
        noise_pkt_rate = len(non_csv_data) / duration if duration > 0 else 0

        raw_data.append({
            'test_name': log_file.stem,
            'scenario_type': scenario_type,
            'freq': freq,
            'run': run,
            'group_name': f'{scenario_type}_{freq}',
            'throughput': tp_data,
            'wireshark_throughput': ws_tp_data,
            'dbm': dbm_data,
            'diag_str': diag_str,
            'noise_rate': noise_pkt_rate,
        })

    return raw_data
