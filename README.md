# Wi-Fi 7 Automated Data Processing Pipeline 📊📡

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome to **Stage 2** of the Wi-Fi 7 Degradation Quantification project. 

This repository contains a high-throughput, automated data processing pipeline designed to ingest, process, and visualize massive amounts of network telemetry data collected during Wi-Fi 7 environmental field tests. It parses raw `pcapng` packet captures, `iPerf3` logs, and `iw` diagnostic data to quantify network degradation across different frequencies (2.4 GHz, 5 GHz, 6 GHz, and MLO).

> **Note:** This is Stage 2 of the project (Data Processing). 
> For **Stage 1 (Automated Data Collection)**, please visit the [Wifi7AutomatedDataCollection Repository](https://github.com/quantifyingdegradationwifi7/Wifi7AutomatedDataCollection).

## 📖 Table of Contents
- [System Intent & Background](#system-intent--background)
- [Architecture & Performance](#architecture--performance)
- [Requirements & Setup](#requirements--setup)
- [Pipeline Usage](#pipeline-usage)
  - [1. Data Compilation](#1-data-compilation)
  - [2. Graph Generation](#2-graph-generation)
  - [3. Tabular & CSV Exports](#3-tabular--csv-exports)
  - [4. Summary Aggregation](#4-summary-aggregation)
- [Methodology](#methodology)

## 🎯 System Intent & Background
Evaluating Wi-Fi 7's Multi-Link Operation (MLO) and single-band resilience requires analyzing network behavior under extreme real-world constraints (e.g., Faraday cages, concrete blockers, extreme distance, microwave EM interference). 

Manually parsing Wireshark packet captures and cross-referencing them with throughput logs across hundreds of tests is nearly impossible. This pipeline was built to:
1. **Automate Data Extraction:** Strip out massive `.pcapng` files into manageable CSVs, extracting only relevant 802.11 Data frames, RSSI (dBm), and noise metrics.
2. **Align Timestamps:** Chronologically stitch together throughput tests with physical layer diagnostics.
3. **Calculate True Degradation:** Automatically compare Line-of-Sight (LOS) baselines against experimental environmental runs using statistically sound math (e.g., Logarithmic averaging for dBm).
4. **Generate Reporting Assets:** Programmatically create line graphs, box plots, CSVs, and formatted tables for research papers.

## ⚡ Architecture & Performance
Parsing DOM-based packet captures via Python (e.g., standard `PyShark`) is inherently slow (~350 packets/sec). This pipeline utilizes an in-memory buffered subprocess stream directly to the `tshark` binary, increasing parsing speeds to **over 30,000 packets/sec**. 

The system relies on a modular `wifi7_pipeline` core library (`/src`), ensuring calculations are strictly tested (`/tests`) and statistically robust.

## ⚙️ Requirements & Setup

### Prerequisites
* **Python:** 3.10 or higher.
* **Tshark:** The CLI version of Wireshark must be installed and accessible in your system's PATH.
* **Keyboard Automation (Optional):** For `generate_copy_paste_table.py` to type directly into Word/Excel.
  * *Linux:* `ydotool`, `wtype`, or `xdotool`
  * *Windows/Mac:* `pyautogui` or `pynput`

### Installation
Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/quantifyingdegradationwifi7/Wifi7AutomatedDataProcessing.git
cd Wifi7AutomatedDataProcessing
pip install -r requirements.txt
```

## 🚀 Pipeline Usage

The toolkit is divided into a sequence of scripts that should be run chronologically.

### 1. Data Compilation
Takes raw logs and PCAPs, identifies the primary MAC addresses driving traffic, and partitions them into aligned, time-series CSVs.
```bash
python3 scripts/compile_raw_data.py
```
*Prompts for the raw data folder path and outputs to `./compiled_data/`.*

### 2. Graph Generation
Visualizes the compiled data. Supports Line graphs, Bar graphs, Box plots, and a consolidated Overview grid.
```bash
python3 scripts/create_graph.py
```
*Allows selection of specific scenarios, frequency bands, and smoothing parameters.*

### 3. Tabular & CSV Exports
To extract data for reports, you have three options depending on your workflow:

* **Table Image:** Generates a clean, styled `.png` table of the throughput, RSSI, and degradation stats.
```bash
python3 scripts/generate_table_image.py
```
* **Summary CSV:** Compiles all selected scenarios into a single large CSV for Excel ingestion.
```bash
python3 scripts/generate_csv.py
```
* **Keyboard Macro Injection:** Physically takes control of your keyboard to type the data exactly into a formatted MS Word/Excel table (to preserve highly specific academic formatting).
```bash
python3 scripts/generate_copy_paste_table.py
```

### 4. Summary Aggregation
Aggregates tests into environmental categories (e.g., "Electromagnetic Interference", "Structural Blockage") to find the mean degradation across multiple related scenarios.
```bash
python3 scripts/get_summary.py
```

## 📐 Methodology
For an in-depth breakdown of the statistical techniques used (Logarithmic vs Linear averaging, missing value bridging, smoothing windows), please read our [Data Processing Methodology](docs/METHODOLOGY.md).

---
*This repository is maintained as part of an ongoing network engineering research initiative evaluating IEEE 802.11be (Wi-Fi 7) in real-world environments.*