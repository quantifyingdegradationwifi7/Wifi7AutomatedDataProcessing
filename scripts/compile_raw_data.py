import csv
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Tuple
import logging
import time
import subprocess
import re
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent

def get_log_time_range(log_path: Path) -> Tuple[Optional[float], float]:
    start_epoch: Optional[float] = None
    max_end_time: float = 0.0
    date_regex = re.compile(r'^[a-zA-Z]{3} [a-zA-Z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2} \d{4}')
    try:
        with log_path.open('r', encoding='utf-8') as f:
            for line in f:
                if start_epoch is None:
                    match = date_regex.search(line)
                    if match:
                        date_str = match.group()
                        date_str = re.sub(r'\s+', ' ', date_str)
                        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
                        start_epoch = dt.timestamp()
                if "sec" in line and "bits/sec" in line and "sender" not in line and "receiver" not in line:
                    parts = line.split()
                    try:
                        sec_idx = parts.index('sec')
                        interval_str = parts[sec_idx - 1]
                        _, end_sec = map(float, interval_str.split('-'))
                        max_end_time = max(max_end_time, end_sec)
                    except ValueError:
                        pass
    except Exception:
        pass
    return start_epoch, max_end_time

try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        raise RuntimeError
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Compatibility shims for Python 3.14+ where asyncio child watchers were removed
class _DummyChildWatcher:
    """A dummy child watcher for Python 3.14+ compatibility."""
    def __init__(self, *args, **kwargs):
        pass

    def attach_loop(self, *args, **kwargs):
        pass

if not hasattr(asyncio, "set_child_watcher"):
    asyncio.set_child_watcher = lambda *args, **kwargs: None
if not hasattr(asyncio, "get_child_watcher"):
    asyncio.get_child_watcher = lambda *args, **kwargs: _DummyChildWatcher()
if not hasattr(asyncio, "SafeChildWatcher"):
    asyncio.SafeChildWatcher = _DummyChildWatcher

try:
    import pyshark
except ImportError:
    print("Error: 'pyshark' is not installed. Please install it using 'pip install pyshark'.")
    print("You also need Wireshark/tshark installed on your system.")
    exit(1)


def compile_diagnostics(input_path: Path, output_path: Path) -> Tuple[bool, str]:
    """
    Copies diagnostics.csv while removing redundant rows where the connection 
    state (channel, frequency, width, center_channel) hasn't changed.
    """
    print(f"  -> Processing {input_path.name}...")
    
    try:
        with input_path.open('r', encoding='utf-8') as fin, \
             output_path.open('w', newline='', encoding='utf-8') as fout:
            
            reader = csv.reader(fin)
            writer = csv.writer(fout)
            
            header = next(reader, None)
            if not header:
                return False, "File is empty or missing header"
                
            writer.writerow(header)
            
            prev_state: Optional[Tuple[str, ...]] = None
            row_count: int = 0
            kept_count: int = 0
            
            for row in reader:
                row_count += 1
                if len(row) >= 5:
                    # The state is defined by: channel, frequency, width, center_channel
                    current_state: Tuple[str, ...] = tuple(row[1:5])
                    
                    if current_state != prev_state:
                        writer.writerow(row)
                        prev_state = current_state
                        kept_count += 1
                else:
                    # If there's a malformed row, just write it to be safe
                    writer.writerow(row)
                    kept_count += 1
            print(f"     [Diagnostics] Compressed {input_path.name}: retained {kept_count:,} of {row_count:,} rows")
        return True, ""
    except Exception as e:
        return False, str(e)

def stream_pcap_fields(pcap_path: Path, fields: list[str], display_filter: Optional[str] = None):
    """
    Streams extracted packet fields directly from tshark via subprocess.
    Bypasses PyShark's heavy DOM parsing, increasing throughput from ~350 pkts/s to 30,000+ pkts/s.
    """
    try:
        tshark_bin = pyshark.tshark.tshark.get_process_path()
    except Exception:
        tshark_bin = shutil.which("tshark") or "tshark"

    cmd = [tshark_bin, "-r", str(pcap_path)]
    if display_filter:
        cmd.extend(["-Y", display_filter])
    cmd.extend(["-T", "fields"])
    for f in fields:
        cmd.extend(["-e", f])
    cmd.extend(["-E", "separator=\t", "-E", "occurrence=f"])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1024 * 1024,
    )
    try:
        if proc.stdout:
            for line in proc.stdout:
                row_fields = line.rstrip("\r\n").split("\t")
                if len(row_fields) < len(fields):
                    row_fields.extend([""] * (len(fields) - len(row_fields)))
                yield row_fields
    finally:
        if proc.stdout:
            proc.stdout.close()
        proc.kill()
        proc.wait()


def compile_pcapng(pcap_path: Path, output_dir: Path, min_share: float = 0.10, interactive: bool = False) -> Tuple[bool, str, list[Tuple[str, float]]]:
    """
    Single-pass processor for pcapng files (Approach A: In-Memory Buffering).
    Streams all packets once from tshark, accumulates 802.11 Data frame volume
    to identify the iPerf source MAC(s) (>10% share), and writes partitioned
    iperf and non-iperf CSV files from the in-memory buffer without re-scanning.
    """
    print(f"  -> Processing {pcap_path.name} in a single pass...")
    start_time = time.time()
    last_log_time = start_time

    fields = [
        'frame.number',
        'frame.time_epoch',
        'wlan_radio.signal_dbm',
        'wlan.fc.type',
        'frame.len',
        'wlan.sa',
        'wlan.da',
        'wlan.ta',
        'wlan.ra'
    ]

    bytes_by_mac: dict[str, int] = {}
    pkts_by_mac: dict[str, int] = {}
    total_data_bytes: int = 0
    data_packet_count: int = 0
    packet_count: int = 0

    # Buffer packets in memory: (pkt_num, timestamp, signal_dbm, packet_size, (sa, da, ta, ra))
    packet_buffer: list[tuple[str, str, str, str, tuple[str, ...]]] = []

    for fields_data in stream_pcap_fields(pcap_path, fields):
        packet_count += 1
        now = time.time()

        if packet_count % 25000 == 0 or (now - last_log_time) >= 3.0:
            elapsed = now - start_time
            rate = packet_count / elapsed if elapsed > 0 else 0.0
            mb_data = total_data_bytes / (1024 * 1024)
            print(f"     [Processing Progress] {packet_count:,} packets scanned ({mb_data:.1f} MB data frames, {rate:.1f} pkts/s)")
            last_log_time = now

        try:
            pkt_num = fields_data[0]
            timestamp = fields_data[1]
            dbm = fields_data[2]
            fc_type = fields_data[3]
            frame_len_str = fields_data[4]
            sa = fields_data[5].strip().lower()
            da = fields_data[6].strip().lower()
            ta = fields_data[7].strip().lower()
            ra = fields_data[8].strip().lower()

            mac_tuple = (sa, da, ta, ra)
            packet_buffer.append((pkt_num, timestamp, dbm, frame_len_str, mac_tuple))

            # Accumulate statistics for 802.11 Data frames (wlan.fc.type == 2)
            if fc_type == '2':
                src_mac = sa if sa else ta
                if frame_len_str and src_mac:
                    pkt_len = int(frame_len_str)
                    bytes_by_mac[src_mac] = bytes_by_mac.get(src_mac, 0) + pkt_len
                    pkts_by_mac[src_mac] = pkts_by_mac.get(src_mac, 0) + 1
                    total_data_bytes += pkt_len
                    data_packet_count += 1

        except Exception as e:
            logging.warning(f"     [!] Error processing packet #{fields_data[0] if fields_data else 'unknown'}: {e}. Skipping...")
            continue

    scan_elapsed = time.time() - start_time

    if not bytes_by_mac or total_data_bytes == 0:
        reason = "Found no valid 802.11 Data frames"
        print(f"     [!] Warning: Scanned {packet_count:,} packets in {scan_elapsed:.1f}s but {reason} in {pcap_path.name}. Skipping...")
        return False, reason, []

    # Determine dominant MACs
    sorted_macs = sorted(bytes_by_mac.items(), key=lambda x: x[1], reverse=True)

    print(f"     [+] Data frame volume breakdown ({total_data_bytes / (1024 * 1024):.2f} MB total across {data_packet_count:,} data frames in {scan_elapsed:.1f}s):")
    for mac, byte_count in sorted_macs[:5]:
        share = (byte_count / total_data_bytes) * 100
        mb = byte_count / (1024 * 1024)
        print(f"         {mac}: {mb:.2f} MB ({share:.1f}%, {pkts_by_mac[mac]:,} frames)")

    valid_macs: list[Tuple[str, float]] = []
    for mac, byte_count in sorted_macs:
        share = (byte_count / total_data_bytes) * 100
        if (byte_count / total_data_bytes) >= min_share:
            valid_macs.append((mac, share))

    if not valid_macs:
        reason = f"No MAC address met the {min_share * 100:.0f}% threshold"
        print(
            f"     [!] Warning: {reason} in {pcap_path.name}. Skipping..."
        )
        return False, reason, []

    if len(valid_macs) > 1 and interactive:
        print(f"     [?] Multiple mac addresses detected for {pcap_path.name}.")
        for i, (mac, share) in enumerate(valid_macs):
            print(f"         {i+1}: {mac} ({share:.1f}%)")
        ans = input("         Would you like to specify one or more? (comma-separated indices, or enter to use all): ").strip()
        if ans:
            try:
                indices = []
                for x in ans.split(","):
                    x = x.strip()
                    if x.isdigit():
                        indices.append(int(x) - 1)
                selected = [valid_macs[i] for i in indices if 0 <= i < len(valid_macs)]
                if selected:
                    valid_macs = selected
            except Exception:
                print("         Invalid input, using all valid MACs.")

    iperf_macs = set(mac for mac, _ in valid_macs)
    mac_strs = [f"{mac} ({share:.1f}%)" for mac, share in valid_macs]
    macs_str = ", ".join(mac_strs)
    print(
        f"     [+] Detected/Selected iPerf source MAC(s): {macs_str} "
        f"(met {min_share * 100:.0f}% share threshold)"
    )

    # Write partitioned packets to disk from buffer
    iperf_file: Path = output_dir / f"wireshark_{pcap_path.stem}.csv"
    non_iperf_file: Path = output_dir / f"non_wireshark_{pcap_path.stem}.csv"
    print(f"     Writing partitioned packets from memory buffer to CSV files...")

    with iperf_file.open('w', newline='', encoding='utf-8') as f_iperf, \
         non_iperf_file.open('w', newline='', encoding='utf-8') as f_non:

        writer_iperf = csv.writer(f_iperf)
        writer_non = csv.writer(f_non)

        header: list[str] = ['packet_number', 'timestamp', 'signal_dbm', 'packet_size']
        writer_iperf.writerow(header)
        writer_non.writerow(header)

        iperf_count: int = 0
        non_iperf_count: int = 0

        for pkt_num, timestamp, dbm, packet_size, mac_tuple in packet_buffer:
            row: list[str] = [pkt_num, timestamp, dbm, packet_size]
            if any(mac in iperf_macs for mac in mac_tuple):
                writer_iperf.writerow(row)
                iperf_count += 1
            else:
                writer_non.writerow(row)
                non_iperf_count += 1

    total_elapsed = time.time() - start_time
    print(f"     [+] Finished {pcap_path.name}: {packet_count:,} packets processed in {total_elapsed:.1f}s ({iperf_count:,} iPerf, {non_iperf_count:,} Non-iPerf)")
    return True, "", valid_macs


def process_directory(input_path: Path, output_base: Path, missed_global: list, is_single_scenario: bool):
    folder_name: str = input_path.name
    output_path: Path = output_base / folder_name
    
    # Create the output directory
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"\nCreated/Using output directory: {output_path}\n")

    scenario_notes = []

    runs = set()
    logs = {}
    pcaps = {}
    has_diag = False
    
    for file_path in input_path.iterdir():
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if file_path.name == 'diagnostics.csv':
            has_diag = True
        elif ext == '.log':
            m = re.match(r'^([a-zA-Z]+)_([a-zA-Z0-9]+)_[a-zA-Z]_(\d+)', file_path.stem)
            if m:
                run_key = f"{m.group(2)}_R{m.group(3)}"
                runs.add(run_key)
                logs[run_key] = file_path
        elif ext == '.pcapng':
            run_key = file_path.stem
            runs.add(run_key)
            pcaps[run_key] = file_path

    if not has_diag:
        scenario_notes.append("Error: Missing diagnostics.csv")
        missed_global.append((folder_name, "diagnostics.csv", "File not found in raw data"))

    for run_key in sorted(runs):
        if run_key not in logs:
            scenario_notes.append(f"Error: Missing iperf log for run {run_key}")
            missed_global.append((folder_name, f"*.log for {run_key}", "Missing iperf log file in raw data"))
        if run_key not in pcaps:
            scenario_notes.append(f"Error: Missing wireshark pcapng for run {run_key}")
            missed_global.append((folder_name, f"{run_key}.pcapng", "Missing wireshark pcapng file in raw data"))

    # Iterate through the files and dispatch to appropriate processors
    for file_path in input_path.iterdir():
        if not file_path.is_file():
            continue
            
        ext: str = file_path.suffix.lower()
        
        success = True
        reason = ""

        if file_path.name == 'diagnostics.csv':
            out_file = output_path / file_path.name
            if out_file.exists():
                print(f"  -> Skipping {file_path.name} (already compiled)")
            else:
                success, reason = compile_diagnostics(file_path, out_file)
            
        elif ext == '.log':
            out_file = output_path / file_path.name
            if out_file.exists():
                print(f"  -> Skipping {file_path.name} (already copied)")
            else:
                print(f"  -> Copying log file: {file_path.name}...")
                try:
                    shutil.copy2(file_path, out_file)
                except Exception as e:
                    success, reason = False, str(e)
            
        elif ext == '.pcapng':
            out_iperf = output_path / f"wireshark_{file_path.stem}.csv"
            out_non = output_path / f"non_wireshark_{file_path.stem}.csv"
            
            should_recompile = False
            if out_iperf.exists() and out_non.exists():
                existing_note = None
                notes_file = output_path / "notes.txt"
                if notes_file.exists():
                    with notes_file.open('r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith("- Note: Multiple MAC addresses used in") and file_path.name in line:
                                existing_note = line.strip()
                                if existing_note.startswith("- "):
                                    existing_note = existing_note[2:]
                                break
                
                if existing_note:
                    print(f"  -> Found notes indicating multiple MAC addresses for {file_path.name}.")
                    print(f"     {existing_note}")
                    ans = input(f"  -> Would you like to specify one? (y/N): ").strip().lower()
                    if ans == 'y':
                        should_recompile = True
                    else:
                        print(f"  -> Skipping {file_path.name} (already compiled)")
                        scenario_notes.append(existing_note)
                else:
                    print(f"  -> Skipping {file_path.name} (already compiled)")
            
            if not (out_iperf.exists() and out_non.exists()) or should_recompile:
                interactive = is_single_scenario or should_recompile
                success, reason, used_macs = compile_pcapng(file_path, output_path, interactive=interactive)
                if success and len(used_macs) > 1:
                    mac_strs = [f"{mac} ({share:.1f}%)" for mac, share in used_macs]
                    scenario_notes.append(f"Note: Multiple MAC addresses used in {file_path.name}: {', '.join(mac_strs)}")

        if not success:
            scenario_notes.append(f"Error compiling {file_path.name}: {reason}")
            missed_global.append((folder_name, file_path.name, reason))

    # Time period checks
    for run_key in sorted(runs):
        if run_key in logs and run_key in pcaps:
            log_out = output_path / logs[run_key].name
            csv_out = output_path / f"wireshark_{run_key}.csv"
            if log_out.exists() and csv_out.exists():
                start_epoch, duration = get_log_time_range(log_out)
                if start_epoch is not None and duration > 0:
                    try:
                        first_ts = None
                        last_ts = None
                        with csv_out.open('r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            next(reader, None)
                            for row in reader:
                                if len(row) >= 2:
                                    ts = float(row[1])
                                    if first_ts is None:
                                        first_ts = ts
                                    last_ts = ts
                        if first_ts is not None and last_ts is not None:
                            log_end = start_epoch + duration
                            unaccounted = []
                            # Allow up to 2 seconds of slack on both ends
                            if first_ts > start_epoch + 2:
                                unaccounted.append(f"missing first {first_ts - start_epoch:.1f}s")
                            if last_ts < log_end - 2:
                                unaccounted.append(f"missing last {log_end - last_ts:.1f}s")
                            if unaccounted:
                                msg = f"Run {run_key} pcap time period unaccounted for: {', '.join(unaccounted)}"
                                scenario_notes.append(msg)
                    except Exception:
                        pass

    notes_file = output_path / "notes.txt"
    missing_file = output_path / "missing.txt"  # for backwards cleanup
    if missing_file.exists():
        missing_file.unlink()

    if scenario_notes:
        with notes_file.open('w', encoding='utf-8') as f:
            f.write("Notes and errors for this scenario:\n")
            for msg in scenario_notes:
                f.write(f"- {msg}\n")
        print(f"  -> Note: Created notes.txt with {len(scenario_notes)} notes/errors.")
    else:
        if notes_file.exists():
            notes_file.unlink()

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("=== Wi-Fi 7 Data Compiler ===")
    raw_dir_input: str = input("Enter the path to the raw data folder: ").strip()
    
    input_path: Path = Path(raw_dir_input).resolve()
    
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: The directory '{input_path}' does not exist.")
        return

    output_base: Path = (ROOT_DIR / "compiled_data").resolve()
    
    # Find all directories that contain at least one .pcapng, .log or diagnostics.csv file
    target_dirs = set()
    for p in input_path.rglob("*"):
        if p.is_file() and (p.suffix.lower() in ['.pcapng', '.log'] or p.name == 'diagnostics.csv'):
            target_dirs.add(p.parent)

    if not target_dirs:
        print(f"No valid raw data folders found in {input_path}")
        return

    missed_global = []
    is_single_scenario = len(target_dirs) == 1

    for d in sorted(target_dirs):
        print(f"\n--- Processing directory: {d.name} ---")
        process_directory(d, output_base, missed_global, is_single_scenario)

    missed_txt = (ROOT_DIR / "missed_compiled.txt").resolve()
    if missed_global:
        with missed_txt.open('w', encoding='utf-8') as f:
            f.write("=== Missed Compiled Files ===\n\n")
            for folder, filename, reason in missed_global:
                f.write(f"Scenario: {folder}\nFile: {filename}\nReason: {reason}\n\n")
        print(f"\n[!] Note: Some files failed to compile. See {missed_txt.name} for details.")
    else:
        if missed_txt.exists():
            missed_txt.unlink()

    print("\n=== Data compilation complete! ===")


if __name__ == "__main__":
    main()
