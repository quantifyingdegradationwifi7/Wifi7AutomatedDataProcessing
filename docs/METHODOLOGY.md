# Data Processing Methodology

This document outlines the mathematical and engineering principles applied in the Wi-Fi 7 Automated Data Processing Pipeline. Because network telemetry relies on disparate data types (logarithmic power levels, discrete packet counts, and continuous throughput streams), ensuring mathematical accuracy is critical.

## 1. Subprocess Packet Streaming
Standard packet parsing (such as PyShark) loads the entire packet DOM into memory. When analyzing millions of packets across an entire field test, this causes severe memory leaks and bottlenecks (~350 pkts/s). 

This pipeline bypasses DOM loading by opening an asynchronous subprocess directly to the `tshark` binary, extracting only the required hex/fields (`wlan.fc.type`, `wlan_radio.signal_dbm`, `frame.len`, etc.). It buffers this in memory to identify the top MAC address contributors (identifying the active `iPerf` streams vs. background noise) before writing partitioned CSVs. Throughput is effectively increased to 30,000+ pkts/s.

## 2. Statistical Aggregation
When analyzing network stability over time, data is binned into slices (default 0.1s to 1.0s depending on the view) and aggregated.

* **Linear Aggregation (Throughput):** Throughput is measured in linear units (Mbps). When aggregating these bins, the arithmetic mean and standard quartiles are applied natively.
* **Logarithmic Aggregation (RSSI):** Signal strength is measured in Decibel-milliwatts (dBm), which is a logarithmic scale. Averaging `-30 dBm` and `-40 dBm` arithmetically yields `-35 dBm`. This is mathematically incorrect. Our pipeline converts dBm to linear milliwatts ($mW = 10^{(dBm/10)}$), averages the milliwatts, and converts back to dBm, yielding the true physical average of `~ -32.6 dBm`.

## 3. Degradation Calculations
The pipeline calculates the degradation between the Line-of-Sight (LOS) control test and the actual scenario.

* **Throughput Degradation:** Calculated linearly. 
  * Formula: `((LOS - Scenario) / LOS) * 100`
  * Example: LOS = 1000 Mbps, Scenario = 500 Mbps -> `50% Degradation`
* **RSSI Attenuation:** Because dBm is already logarithmic, attenuation is calculated via linear subtraction. 
  * Formula: `LOS - Scenario`
  * Example: LOS = -30 dBm, Scenario = -40 dBm -> `10 dB Attenuation` (A 10x drop in actual physical power).

## 4. Signal Bridging & Smoothing
During severe blockage (e.g., Faraday Cage, heavy concrete), the Wi-Fi 7 radios may drop packets entirely. 
* If a timestamp bin receives 0 packets, the pipeline inserts a `0.0` for Throughput.
* For RSSI, a `NaN` (Not a Number) or `-100 dBm` floor is inserted so the graphs accurately reflect a network drop rather than connecting two points across a gap of dead air.
* To make visuals readable, a sliding window average (continuous `NaN`-aware smoothing) is optionally applied to line graphs.