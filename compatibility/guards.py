"""Independent finite implementations for bounded k-interval guard queries.

The endpoint-union enumerator never calls ``component_count``.  The latter is
kept as a mathematically direct cross-check.  This separation is only an
implementation-independence claim for the retained n<=6, k<=3 family.
"""
from __future__ import annotations
from functools import lru_cache


def _admit(n: int, k: int, mask: int | None = None) -> None:
    if type(n) is not int or not 1 <= n <= 32:
        raise ValueError('state count')
    if type(k) is not int or not 0 <= k <= 32:
        raise ValueError('interval limit')
    if mask is not None and (type(mask) is not int or not 0 <= mask < (1 << n)):
        raise ValueError('mask')


def interval_mask(left: int, right: int) -> int:
    """Return the half-open integer interval [left,right) as a bit mask."""
    if type(left) is not int or type(right) is not int or not 0 <= left < right:
        raise ValueError('interval endpoints')
    return ((1 << (right - left)) - 1) << left


@lru_cache(maxsize=None)
def endpoint_union_masks(n: int, k: int) -> tuple[int, ...]:
    """Enumerate masks expressible as a union of at most k endpoint intervals.

    Intervals may overlap or touch.  Consequently two consecutive points are
    produced by one interval, not counted as two singleton components.
    """
    _admit(n, k)
    intervals = [interval_mask(left, right)
                 for left in range(n) for right in range(left + 1, n + 1)]
    masks = {0}
    frontier = {0}
    for _ in range(k):
        frontier = {base | interval for base in frontier for interval in intervals}
        masks.update(frontier)
    return tuple(sorted(masks))


def greatest_sound_by_endpoints(safe_mask: int, n: int, k: int) -> int | None:
    """Find a greatest sound endpoint-union guard by inclusion, if one exists."""
    _admit(n, k, safe_mask)
    candidates = [mask for mask in endpoint_union_masks(n, k)
                  if mask & ~safe_mask == 0]
    union = 0
    for mask in candidates:
        union |= mask
    # A greatest candidate, if present, equals the union of all candidates.
    return union if union in candidates else None


def component_count(mask: int, n: int) -> int:
    """Count maximal nonempty contiguous components without endpoint enumeration."""
    _admit(n, 0, mask)
    return sum(bool(mask & (1 << state))
               and (state == 0 or not (mask & (1 << (state - 1))))
               for state in range(n))


def component_oracle(safe_mask: int, n: int, k: int) -> int | None:
    """Closed-form oracle for a semantic set under a k-interval language."""
    _admit(n, k, safe_mask)
    if k == 0:
        return 0
    return safe_mask if component_count(safe_mask, n) <= k else None
