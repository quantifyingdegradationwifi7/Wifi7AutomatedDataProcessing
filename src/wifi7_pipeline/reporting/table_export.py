from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from ..core.scenario_io import load_scenario_data
from .csv_export import get_freq_stats

class KeyboardSimulator:
    def __init__(self):
        self.backend = None
        self.errors = {}
        self._init_backend()

    def _init_backend(self):
        backends = []
        if shutil.which("wtype"):
            backends.append("wtype")
        if shutil.which("ydotool"):
            backends.append("ydotool")
        if shutil.which("xdotool"):
            backends.append("xdotool")
        try:
            import pyautogui
            self.pyautogui = pyautogui
            backends.append("pyautogui")
        except ImportError:
            pass
        try:
            from pynput.keyboard import Controller, Key
            self.pynput_ctrl = Controller()
            self.pynput_key = Key
            backends.append("pynput")
        except ImportError:
            pass

        for b in backends:
            if b == "wtype":
                try:
                    res = subprocess.run(["wtype", "-k", "Shift_L"], capture_output=True, text=True)
                    if res.returncode == 0:
                        self.backend = "wtype"
                        break
                    else:
                        err_msg = res.stderr.strip() or res.stdout.strip()
                        self.errors["wtype"] = err_msg.split('\n')[0] if err_msg else "Unknown error"
                except Exception as e:
                    self.errors["wtype"] = str(e)
            elif b == "ydotool":
                try:
                    res = subprocess.run(["ydotool", "key", "42:1", "42:0"], capture_output=True, text=True)
                    if res.returncode == 0:
                        self.backend = "ydotool"
                        break
                    else:
                        err_msg = res.stderr.strip() or res.stdout.strip()
                        self.errors["ydotool"] = err_msg.split('\n')[0] if err_msg else "Unknown error"
                except Exception as e:
                    self.errors["ydotool"] = str(e)
            elif b == "xdotool":
                try:
                    res = subprocess.run(["xdotool", "key", "Shift_L"], capture_output=True, text=True)
                    if res.returncode == 0:
                        self.backend = "xdotool"
                        break
                    else:
                        err_msg = res.stderr.strip() or res.stdout.strip()
                        self.errors["xdotool"] = err_msg.split('\n')[0] if err_msg else "Unknown error"
                except Exception as e:
                    self.errors["xdotool"] = str(e)
            elif b == "pyautogui":
                self.backend = "pyautogui"
                break
            elif b == "pynput":
                self.backend = "pynput"
                break

    def type_text(self, text: str):
        if not text:
            return
        if self.backend == "wtype":
            subprocess.run(["wtype", text], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "ydotool":
            subprocess.run(["ydotool", "type", text], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "xdotool":
            subprocess.run(["xdotool", "type", "--", text], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "pyautogui":
            self.pyautogui.write(text)
        elif self.backend == "pynput":
            self.pynput_ctrl.type(text)
        else:
            raise RuntimeError("No working keyboard automation tool found.")

    def press_tab(self):
        if self.backend == "wtype":
            subprocess.run(["wtype", "-k", "Tab"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "ydotool":
            subprocess.run(["ydotool", "key", "15:1", "15:0"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "xdotool":
            subprocess.run(["xdotool", "key", "Tab"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        elif self.backend == "pyautogui":
            self.pyautogui.press("tab")
        elif self.backend == "pynput":
            self.pynput_ctrl.press(self.pynput_key.tab)
            self.pynput_ctrl.release(self.pynput_key.tab)
        else:
            raise RuntimeError("No working keyboard automation tool found.")


def build_actions_for_freq(stats: dict, columns: list[str]) -> list[tuple[str, str | None]]:
    actions: list[tuple[str, str | None]] = []
    
    for col in columns:
        if col == 'tp_los':
            for val in stats['tp_los']:
                actions.append(('type', val))
                actions.append(('tab', None))
        elif col == 'dbm_los':
            for val in stats['dbm_los']:
                actions.append(('type', val))
                actions.append(('tab', None))
        elif col == 'noise_los':
            actions.append(('type', stats.get('noise_los', '0/s')))
            actions.append(('tab', None))
        elif col == 'tp_prop':
            for val in stats['tp_prop']:
                actions.append(('type', val))
                actions.append(('tab', None))
        elif col == 'dbm_prop':
            for val in stats['dbm_prop']:
                actions.append(('type', val))
                actions.append(('tab', None))
        elif col == 'noise_prop':
            actions.append(('type', stats.get('noise_prop', '0/s')))
            actions.append(('tab', None))
        elif col == 'deg_tp':
            actions.append(('type', stats['deg_tp']))
            actions.append(('tab', None))
        elif col == 'deg_dbm':
            actions.append(('type', stats['deg_dbm']))
            actions.append(('tab', None))
        elif col == 'tab':
            actions.append(('tab', None))
            
    if actions and actions[-1] == ('tab', None):
        actions.pop()
    
    return actions


def run_table_export(selected_scenario: Path, tp_source: str, freq_choice: str, columns: list[str] | None = None) -> None:
    raw_data = load_scenario_data(selected_scenario)
    if not raw_data:
        print(f"No valid data found for {selected_scenario.name}. Exiting.")
        return

    if tp_source == '2':
        for d in raw_data:
            d['throughput'] = d.get('wireshark_throughput', [])

    simulator = KeyboardSimulator()
    if not simulator.backend:
        print("\n[!] Error: No working keyboard simulation tool found.")
        if simulator.errors:
            print("    The following tools were found but failed to initialize:")
            for b, err in simulator.errors.items():
                print(f"      - {b}: {err}")
        print("\n    Please install or configure one of the following tools:")
        print("    1. sudo dnf install ydotool     (Requires running ydotoold daemon, works on KDE Wayland)")
        print("    2. pip install pyautogui        (Cross-platform Python module)")
        print("    3. sudo dnf install xdotool     (Works on X11 / XWayland)")
        print("    4. sudo dnf install wtype       (Works on wlroots Wayland, but NOT supported on KDE)")
        return
    else:
        print(f"\n[+] Using keyboard backend: {simulator.backend}")

    freq_options = {
        '1': [('24', '2.4 GHz')],
        '2': [('5', '5 GHz')],
        '3': [('6', '6 GHz')],
        '4': [('mlo', 'MLO')],
        '5': [('24', '2.4 GHz'), ('5', '5 GHz'), ('6', '6 GHz'), ('mlo', 'MLO')]
    }

    if freq_choice not in freq_options:
        print("Invalid selection.")
        return

    freq_list = freq_options[freq_choice]
    label = "All frequencies" if freq_choice == '5' else freq_list[0][1]
    
    if columns is None:
        columns = [
            'tp_los', 'tab', 'tab', 'tab', 'tab',
            'dbm_los', 'tab', 'tab',
            'tp_prop', 'deg_tp', 'tab', 'tab', 'tab',
            'dbm_prop', 'deg_dbm'
        ]
    
    actions: list[tuple[str, str | None]] = []
    for i, (f, flabel) in enumerate(freq_list):
        stats = get_freq_stats(f, raw_data)
        actions.extend(build_actions_for_freq(stats, columns))
        if i < len(freq_list) - 1:
            next_label = freq_list[i+1][1]
            actions.append(('pause', next_label))

    print(f"\n[!] Preparing to type: {label}")
    print("    CLICK ON THE FIRST TARGET CELL ([min]) IN WORD ONLINE NOW!")
    print("    Typing will begin in 5 seconds (Press Ctrl+C in terminal to cancel)...")
    try:
        for sec in range(5, 0, -1):
            print(f"    Starting in {sec}...", flush=True)
            time.sleep(1)
        print("    >>> TYPING NOW! DO NOT TOUCH KEYBOARD OR MOUSE <<<")
        
        for action_type, val in actions:
            if action_type == 'type':
                if val:
                    simulator.type_text(val)
            elif action_type == 'tab':
                simulator.press_tab()
            elif action_type == 'pause':
                print(f"\n[+] Moving to next frequency: {val}")
                for _ in range(20):
                    simulator.press_tab()
                    time.sleep(0.05)
                    
                continue
            time.sleep(0.05)
            
        print("\n[+] Finished typing!")
    except KeyboardInterrupt:
        print("\n[!] Aborted by user!")
    except Exception as e:
        print(f"\n[!] Error during typing: {e}")