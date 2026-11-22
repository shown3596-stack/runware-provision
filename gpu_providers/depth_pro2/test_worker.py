import unittest
import numpy as np
from worker import relative_inverse_depth

class DepthOutputTest(unittest.TestCase):
    def test_near_is_bright_and_invalid_is_far(self):
        output = relative_inverse_depth(np.array([[0.1, 0.3, 0.7, float('inf'), 0]]))
        self.assertEqual(output.dtype, np.uint8)
        self.assertLess(output[0,0], output[0,2])
        self.assertEqual(output[0,3], 0)
        self.assertEqual(output[0,4], 0)
    def test_empty_invalid_depth_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_inverse_depth(np.array([[0, float('nan')]]))
