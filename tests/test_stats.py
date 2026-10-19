import unittest
import numpy as np
import math
from wifi7_pipeline.core.stats import (
    calc_stats, 
    calc_throughput_degradation, 
    calc_rssi_degradation,
    ordered_stats, 
    format_sig_figs
)

class TestStats(unittest.TestCase):
    def test_calc_stats_empty(self):
        """Test calculation of statistics on an empty list."""
        res = calc_stats([])
        self.assertEqual(res['min'], 0.0)
        self.assertEqual(res['max'], 0.0)
        self.assertEqual(res['median'], 0.0)

    def test_calc_stats_normal(self):
        """Test calculation of quartiles and averages."""
        res = calc_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(res['min'], 1.0)
        self.assertEqual(res['q1'], 2.0)
        self.assertEqual(res['median'], 3.0)
        self.assertEqual(res['mean'], 3.0)
        self.assertEqual(res['q3'], 4.0)
        self.assertEqual(res['max'], 5.0)

    def test_calc_throughput_degradation(self):
        """Test linear throughput degradation without zero capping."""
        # Standard degradation
        self.assertEqual(calc_throughput_degradation(100.0, 50.0), 50.0)
        
        # Improvement (negative degradation)
        self.assertEqual(calc_throughput_degradation(100.0, 150.0), -50.0) 
        
        # Edge case: LOS is 0 (mathematically undefined, returns NaN)
        self.assertTrue(math.isnan(calc_throughput_degradation(0.0, 50.0)))

    def test_calc_rssi_degradation(self):
        """Test linear mathematical subtraction for logarithmic RSSI values."""
        # 10 dB loss
        self.assertEqual(calc_rssi_degradation(-20.0, -30.0), 10.0)
        
        # 10 dB improvement (negative degradation)
        self.assertEqual(calc_rssi_degradation(-30.0, -20.0), -10.0)

    def test_calc_stats_dbm(self):
        """Test logarithmic averaging of dBm values."""
        # -30 dBm is 0.001 mW, -40 dBm is 0.0001 mW
        # Average is 0.00055 mW, which is approx -32.596 dBm
        res = calc_stats([-30.0, -40.0], is_dbm=True)
        self.assertAlmostEqual(res['mean'], -32.596, places=3)

    def test_ordered_stats(self):
        """Test that dictionary unspooling maintains correct Word Table order."""
        stats = {'min': 1, 'q1': 2, 'median': 3, 'mean': 4, 'q3': 5, 'max': 6}
        ordered = ordered_stats(stats)
        # Verify order matches 'Min, Q1, Avg (Mean), Med (Median), Q3, Max'
        self.assertEqual(ordered, [1, 2, 4, 3, 5, 6]) 

    def test_format_sig_figs(self):
        """Test sig fig formatting strings for Word Document typing."""
        self.assertEqual(format_sig_figs(0), "0.0")
        self.assertEqual(format_sig_figs(1.2345), "1.234")
        
        # Formatting handles tiny and large numbers predictably
        self.assertEqual(format_sig_figs(100.123, 4), "100.1")
        self.assertEqual(format_sig_figs(12345, 4), "12340")
        self.assertEqual(format_sig_figs(0.0012345, 4), "0.001234")