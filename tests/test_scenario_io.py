import unittest
import tempfile
from pathlib import Path
from wifi7_pipeline.core.scenario_io import (
    get_time_range_from_logs,
    get_csv_lines_from_time_range,
    get_diagnostic_info
)

class TestScenarioIO(unittest.TestCase):
    def test_get_time_range_from_logs(self):
        """Test the extraction of throughput values and epoch dates from raw iPerf logs."""
        log_content = """Thu Aug  6 13:31:11 2026
[  6] local 192.168.1.2 port 5000 connected to 192.168.1.3 port 5001
[  6]   0.00-0.10   sec  12.0 MBytes  1.01 Gbits/sec
[  6]   0.10-0.20   sec  6.00 MBytes  500 Kbits/sec
[  6]   0.20-0.24   sec  3.00 MBytes  7.60 Gbits/sec
[  6]   0.00-0.24   sec  21.0 MBytes  700 Mbits/sec
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(log_content)
            tmp_name = f.name
        
        try:
            start_epoch, duration, tp_data = get_time_range_from_logs(Path(tmp_name))
            self.assertIsNotNone(start_epoch)
            self.assertAlmostEqual(duration, 0.24)
            # The artifact trailing interval (0.04s) and summary interval (0.24s) should be filtered out
            self.assertEqual(len(tp_data), 2)
            
            # Midpoint timing
            self.assertAlmostEqual(tp_data[0][0], 0.05)
            
            # Unit conversion (1.01 Gbits -> 1010 Mbps, 500 Kbits -> 0.5 Mbps)
            self.assertAlmostEqual(tp_data[0][1], 1010.0)
            self.assertAlmostEqual(tp_data[1][1], 0.5) 
        finally:
            Path(tmp_name).unlink()

    def test_get_time_range_from_logs_parallel_streams(self):
        """Test that parallel streams use [SUM] lines to avoid double counting."""
        log_content = """Thu Aug  6 13:31:11 2026
[  4]   0.00-1.00   sec  10.0 MBytes  80.0 Mbits/sec
[  5]   0.00-1.00   sec  10.0 MBytes  80.0 Mbits/sec
[SUM]   0.00-1.00   sec  20.0 MBytes  160 Mbits/sec
[  4]   1.00-2.00   sec  10.0 MBytes  80.0 Mbits/sec
[  5]   1.00-2.00   sec  10.0 MBytes  80.0 Mbits/sec
[SUM]   1.00-2.00   sec  20.0 MBytes  160 Mbits/sec
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write(log_content)
            tmp_name = f.name
        
        try:
            start_epoch, duration, tp_data = get_time_range_from_logs(Path(tmp_name))
            self.assertEqual(len(tp_data), 2)
            self.assertAlmostEqual(tp_data[0][1], 160.0)
            self.assertAlmostEqual(tp_data[1][1], 160.0)
        finally:
            Path(tmp_name).unlink()

    def test_get_csv_lines(self):
        """Test that Wireshark CSVs are properly parsed and boundary-restricted."""
        csv_content = "packet_number,timestamp,signal_dbm,packet_size\n1,1000.5,-50,1500\n2,1001.0,-110,1500\n3,1005.0,-40,1000\n"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(csv_content)
            tmp_name = f.name
        
        try:
            data = get_csv_lines_from_time_range(Path(tmp_name), start_epoch=1000.0, duration=2.0)
            
            # Expectations:
            # - Packet 1: Valid
            # - Packet 2: Out of RSSI threshold range (< -100 dbm is skipped)
            # - Packet 3: Out of time range (1005.0 exceeds 1000.0 + 2.0 duration limit)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0][0], 0.5) # Relative time (1000.5 - 1000.0)
            self.assertEqual(data[0][1], -50)
            self.assertEqual(data[0][2], 1500)
        finally:
            Path(tmp_name).unlink()

    def test_get_diagnostic_info(self):
        """Verify the chronological resolution of network diagnostic states."""
        diag_data = [
            {'time': 1000.0, 'channel': '36', 'width': '80'},
            {'time': 1010.0, 'channel': '40', 'width': '160'}
        ]
        
        # Test pulling state right before the change
        info1 = get_diagnostic_info(diag_data, start_epoch=1005.0)
        self.assertEqual(info1, "Ch 36 (80MHz)")
        
        # Test pulling state after the change
        info2 = get_diagnostic_info(diag_data, start_epoch=1015.0)
        self.assertEqual(info2, "Ch 40 (160MHz)")