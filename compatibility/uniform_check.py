"""Independent policy enumeration oracle and obstruction checker (tiny inputs)."""
from itertools import product


def enumerate_supports(problem):
    """Enumerate supports of every block-respecting policy."""
    m = problem['choices']; blocks = problem['blocks']; rows = problem['safe_choices']
    supports = set()
    for assignment in product(range(m), repeat=max(blocks) + 1):
        supports.add(tuple(v for v in range(len(rows)) if assignment[blocks[v]] in rows[v]))
    return supports


def is_refinement(fine_blocks, coarse_blocks):
    """Return whether every fine block is contained in one coarse block."""
    if type(fine_blocks) is not list or type(coarse_blocks) is not list or len(fine_blocks) != len(coarse_blocks):
        raise ValueError('partition sizes')
    return all(fine_blocks[i] != fine_blocks[j] or coarse_blocks[i] == coarse_blocks[j]
               for i in range(len(fine_blocks)) for j in range(len(fine_blocks)))


def oracle(problem):
    # This oracle deliberately enumerates policies, not per-block intersections.
    m = problem['choices']; blocks = problem['blocks']; rows = problem['safe_choices']
    supports = enumerate_supports(problem)
    union = tuple(v for v in range(len(rows)) if any(v in r for r in supports))
    return {'greatest_region': list(union) if union in supports else None,
            'policy_count': m ** (max(blocks) + 1), 'distinct_supports': len(supports)}


def check(problem, certificate):
    """Check admitted tiny matrix inputs; input schema checked by the campaign.

    No calls to the solver. This validates the conflict, inclusion minimality,
    and the greatest-region claim against exhaustive policy enumeration.
    """
    if type(certificate) is not dict or set(certificate) != {'greatest_region', 'policy', 'obstruction'}:
        raise ValueError('uniform certificate schema')
    expected = oracle(problem)
    if certificate['greatest_region'] != expected['greatest_region']:
        raise ValueError('greatest-region mismatch')
    m = problem['choices']; rows = problem['safe_choices']; labels = problem['blocks']
    def isint(x, stop): return type(x) is int and 0 <= x < stop
    if expected['greatest_region'] is not None:
        p = certificate['policy']
        if certificate['obstruction'] is not None or type(p) is not list or len(p) != max(labels) + 1 or any(not isint(a, m) for a in p):
            raise ValueError('policy schema')
        if type(certificate['greatest_region']) is not list or any(not isint(v, len(rows)) for v in certificate['greatest_region']):
            raise ValueError('region schema')
        if any(p[labels[v]] not in rows[v] for v in expected['greatest_region']):
            raise ValueError('policy failure')
        return expected
    if certificate['policy'] is not None:
        raise ValueError('conflict cannot carry a successful policy')
    c = certificate['obstruction']
    if type(c) is not dict or set(c) != {'block', 'states', 'choice_rejections', 'deletion_witnesses'}:
        raise ValueError('obstruction schema')
    states = c['states']
    if type(states) is not list or not states or any(not isint(v, len(rows)) for v in states) or states != sorted(set(states)):
        raise ValueError('obstruction states')
    if not isint(c['block'], max(labels) + 1) or any(labels[v] != c['block'] or not rows[v] for v in states):
        raise ValueError('not a supported single-block conflict')
    cover = c['choice_rejections']; deletions = c['deletion_witnesses']
    if type(cover) is not list or len(cover) != m or type(deletions) is not list or len(deletions) != len(states):
        raise ValueError('obstruction coverage')
    for a, witness in enumerate(cover):
        if type(witness) is not dict or set(witness) != {'choice', 'state'} or type(witness['choice']) is not int or witness['choice'] != a:
            raise ValueError('choice coverage')
        v = witness['state']
        if not isint(v, len(rows)) or v not in states or a in rows[v]:
            raise ValueError('false rejected choice')
    for v, witness in zip(states, deletions):
        if type(witness) is not dict or set(witness) != {'removed_state', 'choice'} or type(witness['removed_state']) is not int or witness['removed_state'] != v:
            raise ValueError('deletion coverage')
        a = witness['choice']
        if not isint(a, m) or any(a not in rows[u] for u in states if u != v):
            raise ValueError('false deletion witness')
    return expected
