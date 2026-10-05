"""Regressions for the admitted zero-interval guard language."""
import unittest

from compatibility.guards import (
    component_oracle, endpoint_union_masks, greatest_sound_by_endpoints,
)


class ZeroIntervalBoundaryTests(unittest.TestCase):
    def test_empty_language_has_greatest_empty_guard(self):
        for n in range(1, 7):
            self.assertEqual(endpoint_union_masks(n, 0), (0,))
            for safe in range(1 << n):
                self.assertEqual(component_oracle(safe, n, 0), 0)
                self.assertEqual(greatest_sound_by_endpoints(safe, n, 0), 0)

    def test_positive_interval_cases_keep_their_meaning(self):
        self.assertEqual(component_oracle(0b0110, 4, 1), 0b0110)
        self.assertIsNone(component_oracle(0b0101, 4, 1))
        self.assertEqual(component_oracle(0b0101, 4, 2), 0b0101)


if __name__ == '__main__':
    unittest.main()
