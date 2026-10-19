import unittest
import numpy as np
from wifi7_pipeline.core.transforms import bin_and_aggregate_data, apply_smoothing

class TestTransforms(unittest.TestCase):
    def test_bin_and_aggregate_empty(self):
        """Verify handling of completely empty Wireshark data sets."""
        x, y = bin_and_aggregate_data([])
        self.assertEqual(len(x), 0)
        self.assertEqual(len(y), 0)

        # Test duration creates proper bins padded with missing value
        x_dur, y_dur = bin_and_aggregate_data([], duration=2.0)
        self.assertEqual(len(x_dur), 20)
        self.assertEqual(len(y_dur), 20)
        self.assertEqual(y_dur[0], 0.0)

    def test_bin_and_aggregate_mean(self):
        """Test that data points are mapped smoothly to the correct time buckets."""
        data = [(0.05, 10), (0.06, 20), (0.15, 30)]
        x, y = bin_and_aggregate_data(data, bin_size=0.1, method='mean')
        
        # Bin 0 (0.0 to 0.1) has 10 and 20, mean = 15
        self.assertAlmostEqual(x[0], 0.05)
        self.assertAlmostEqual(y[0], 15.0)
        
        # Bin 1 (0.1 to 0.2) has 30, mean = 30
        self.assertAlmostEqual(x[1], 0.15)
        self.assertAlmostEqual(y[1], 30.0)

    def test_bin_and_aggregate_missing(self):
        """Test that dropout points receive the requested missing value (0.0 or nan)."""
        data = [(0.05, 10), (0.25, 30)]
        # Passing duration=0.4 means bins up to 0.4s
        x, y = bin_and_aggregate_data(data, bin_size=0.1, method='mean', missing_value=0.0, duration=0.4)
        
        self.assertEqual(len(x), 4)
        self.assertAlmostEqual(y[0], 10.0)
        self.assertAlmostEqual(y[1], 0.0) # Network dropout bridging
        self.assertAlmostEqual(y[2], 30.0)
        self.assertAlmostEqual(y[3], 0.0)

        # Test with np.nan for RSSI
        _, y_nan = bin_and_aggregate_data(data, bin_size=0.1, method='mean', missing_value=np.nan)
        self.assertTrue(np.isnan(y_nan[1]))

    def test_bin_and_aggregate_sum_to_mbps(self):
        """Test conversion logic from accumulated packet sizes into standard Mbps."""
        # 125,000 bytes = 1,000,000 bits. Sent across a single 0.1 second bin.
        # This translates to a data rate of 10 Mbps.
        data = [(0.05, 125000)]
        x, y = bin_and_aggregate_data(data, bin_size=0.1, method='sum_to_mbps')
        self.assertAlmostEqual(y[0], 10.0)

    def test_apply_smoothing(self):
        """Test continuous NaN-aware smoothing."""
        y = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        smooth = apply_smoothing(y, window_size=3)
        
        # Window for index 2 is [2.0, nan, 4.0], valid are [2.0, 4.0], mean is 3.0
        self.assertAlmostEqual(smooth[2], 3.0)
        
        # Window for index 0 is [1.0, 2.0], valid are [1.0, 2.0], mean is 1.5
        self.assertAlmostEqual(smooth[0], 1.5)