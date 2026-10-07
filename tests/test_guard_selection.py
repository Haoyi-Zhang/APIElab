"""Finite set-based references for endpoint greatest-guard selection."""
from functools import lru_cache
from itertools import combinations
import unittest
from unittest.mock import patch

from compatibility.guards import (
    component_oracle, endpoint_union_masks, greatest_sound_by_endpoints,
)


def encode(region):
    return sum(2 ** point for point in region)


@lru_cache(maxsize=None)
def reference_families(n, k):
    """Choose interval sets without production's bitwise frontier expansion."""
    intervals = [frozenset(range(left, right))
                 for left in range(n) for right in range(left + 1, n + 1)]
    regions = {frozenset()}
    for size in range(1, k + 1):
        for selected in combinations(intervals, size):
            regions.add(frozenset().union(*selected))
    return tuple(sorted(regions, key=encode))


def pairwise_reference(safe_mask, n, k):
    """Use set containment, not the union-membership production decision."""
    safe = frozenset(point for point in range(n) if safe_mask & (2 ** point))
    sound = [region for region in reference_families(n, k) if region <= safe]
    for region in sound:
        if all(other <= region for other in sound):
            return encode(region)
    return None


class GuardSelectionTests(unittest.TestCase):
    def test_complete_small_family_against_pairwise_and_component_oracles(self):
        queries = exists = absent = 0
        for n in range(1, 7):
            for k in range(4):
                self.assertEqual(endpoint_union_masks(n, k),
                                 tuple(map(encode, reference_families(n, k))))
                for safe in range(1 << n):
                    with self.subTest(n=n, k=k, safe=safe):
                        got = greatest_sound_by_endpoints(safe, n, k)
                        self.assertEqual(got, pairwise_reference(safe, n, k))
                        self.assertEqual(got, component_oracle(safe, n, k))
                        queries += 1
                        if k:
                            exists += got is not None
                            absent += got is None
        self.assertEqual((queries, exists, absent), (504, 306, 72))

    def test_incomparable_maxima_are_not_a_greatest_guard(self):
        self.assertIsNone(greatest_sound_by_endpoints(0b0101, 4, 1))
        self.assertEqual(greatest_sound_by_endpoints(0b0101, 4, 2), 0b0101)
        self.assertEqual(greatest_sound_by_endpoints(0b0110, 4, 1), 0b0110)

    def test_selection_does_not_call_the_component_oracle(self):
        with patch('compatibility.guards.component_count', side_effect=AssertionError), \
             patch('compatibility.guards.component_oracle', side_effect=AssertionError):
            self.assertIsNone(greatest_sound_by_endpoints(0b0101, 4, 1))
            self.assertEqual(greatest_sound_by_endpoints(0b0110, 4, 1), 0b0110)

    def test_admission_and_cheap_upper_boundaries(self):
        for n, k, safe in [(True, 1, 0), (0, 1, 0), (33, 1, 0),
                           (1, True, 0), (1, -1, 0), (1, 33, 0),
                           (1, 0, False), (1, 0, -1), (1, 0, 2)]:
            with self.subTest(n=n, k=k, safe=safe), self.assertRaises(ValueError):
                greatest_sound_by_endpoints(safe, n, k)
        self.assertEqual(greatest_sound_by_endpoints((1 << 32) - 1, 32, 0), 0)
        self.assertEqual(greatest_sound_by_endpoints(1, 1, 32), 1)


if __name__ == '__main__':
    unittest.main()
