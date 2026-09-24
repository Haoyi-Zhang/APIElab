"""Finite observation-respecting choice policies and inclusion-minimal conflicts.

The finite set operations below illustrate the proof in proofs/arguments.md.
They do not constitute a general mechanization or a new synthesis algorithm.
"""
from __future__ import annotations


def validate(problem):
    if type(problem) is not dict or set(problem) != {'choices', 'blocks', 'safe_choices'}:
        raise ValueError('uniform problem fields')
    m = problem['choices']; blocks = problem['blocks']; safe = problem['safe_choices']
    if type(m) is not int or not 1 <= m <= 8:
        raise ValueError('choice bound')
    if type(blocks) is not list or type(safe) is not list or not 1 <= len(blocks) <= 8 or len(blocks) != len(safe):
        raise ValueError('version bound')
    if any(type(b) is not int or b < 0 for b in blocks) or blocks[0] != 0:
        raise ValueError('partition labels')
    for i, b in enumerate(blocks):
        if b > 1 + max(blocks[:i], default=-1):
            raise ValueError('partition must use restricted-growth labels')
    for row in safe:
        if type(row) is not list or any(type(a) is not int or not 0 <= a < m for a in row) or row != sorted(set(row)):
            raise ValueError('choice row')


def feasible(problem, region):
    """Precondition: problem is admitted, region is a subset of its state indices."""
    m = problem['choices']
    for b in set(problem['blocks']):
        available = set(range(m))
        for v in region:
            if problem['blocks'][v] == b:
                available &= set(problem['safe_choices'][v])
        if not available:
            return False
    return True


def solve(problem):
    validate(problem)
    support = [v for v, row in enumerate(problem['safe_choices']) if row]
    if feasible(problem, support):
        policy = []
        for b in range(max(problem['blocks']) + 1):
            available = set(range(problem['choices']))
            for v in support:
                if problem['blocks'][v] == b:
                    available &= set(problem['safe_choices'][v])
            policy.append(min(available))
        return {'greatest_region': support, 'policy': policy, 'obstruction': None}
    # The first failing observation block, followed by deterministic deletion.
    for b in range(max(problem['blocks']) + 1):
        subset = [v for v in support if problem['blocks'][v] == b]
        if not feasible(problem, subset):
            break
    for v in list(subset):
        smaller = [u for u in subset if u != v]
        if not feasible(problem, smaller):
            subset = smaller
    cover = []
    for a in range(problem['choices']):
        cover.append({'choice': a, 'state': next(v for v in subset if a not in problem['safe_choices'][v])})
    deletion = []
    for v in subset:
        surviving = [a for a in range(problem['choices'])
                     if all(a in problem['safe_choices'][u] for u in subset if u != v)]
        deletion.append({'removed_state': v, 'choice': min(surviving)})
    return {'greatest_region': None, 'policy': None,
            'obstruction': {'block': b, 'states': subset,
                            'choice_rejections': cover, 'deletion_witnesses': deletion}}
