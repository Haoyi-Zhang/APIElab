"""Six named tiny controls for choice/input/gate quantifier placement.

Exhaustive CNF assignment checking, not a SAT/QBF solver or a new campaign.
The checker reads clauses and the emitted prefix, never circuit gate operators.
Scalar and packed-vector circuit paths are cross-checked separately.
"""
from __future__ import annotations
import argparse
import hashlib
from itertools import combinations, product
import json
import platform
from pathlib import Path
import sys

from .group_constraints import no_input_groups, quantified_groups
from .succinct import scalar_certificate
from .succinct_check import check


def controls():
    def circuit(identifier, nodes, outputs, x_bits=1):
        return {'id': identifier, 'a_bits': 1, 'x_bits': x_bits,
                'nodes': nodes, 'outputs': outputs}
    return [
        ('input_dependent_gate_witness',
         circuit('Q001', [['x', 0], ['not', 0], ['or', 0, 1]], [2])),
        ('choice_stays_before_input',
         circuit('Q002', [['a', 0], ['x', 0], ['not', 0], ['not', 1],
                          ['and', 0, 1], ['and', 2, 3], ['or', 4, 5]], [6])),
        ('atomic_opposite_choice_groups',
         circuit('Q003', [['a', 0], ['not', 0], ['x', 0]], [0, 1])),
        ('all_gate_operators',
         circuit('Q004', [['a', 0], ['x', 0], ['const', 1], ['not', 1],
                          ['and', 0, 3], ['or', 4, 2]], [5])),
        ('empty_region_with_impossible_group',
         circuit('Q005', [['x', 0], ['const', 0]], [1])),
        ('no_input_duplicate_labels',
         circuit('Q006', [['a', 0]], [0, 0], x_bits=0)),
    ]


def qbf_truth(clauses, prefix, fixed=None):
    """Tiny exhaustive clause/prefix oracle; rejects outside its finite cap.

    Unused variables can be omitted from enumeration but not from the prefix
    coverage check. Existential and universal blocks retain their given order.
    """
    variables = [v for block in prefix for v in block['variables']]
    if (len(variables) > 16 or len(clauses) > 64
            or any(type(v) is not int or v < 1 for v in variables)
            or len(set(variables)) != len(variables)
            or any(block['quantifier'] not in ('exists', 'forall') for block in prefix)):
        raise ValueError('outside tiny prefix-control domain')
    used = {abs(literal) for clause in clauses for literal in clause}
    if any(type(literal) is not int or literal == 0 for clause in clauses for literal in clause) or not used <= set(variables):
        raise ValueError('invalid literal or unbound variable')
    fixed = dict(fixed or {})
    if not set(fixed) <= set(variables) or any(type(bit) is not int or bit not in (0, 1) for bit in fixed.values()):
        raise ValueError('invalid fixed assignment')

    def visit(index, assignment):
        if index == len(prefix):
            return all(any(assignment[abs(literal)] == int(literal > 0)
                           for literal in clause) for clause in clauses)
        block = prefix[index]
        active = [v for v in block['variables'] if v in used and v not in fixed]
        answers = (visit(index + 1, assignment | dict(zip(active, bits)))
                   for bits in product((0, 1), repeat=len(active)))
        return any(answers) if block['quantifier'] == 'exists' else all(answers)
    return visit(0, fixed)


def choice_projection(encoding, region):
    clauses = [clause for label in region for clause in encoding['groups'][label]]
    choices = encoding['prefix'][0]['variables']
    return [a for a in range(1 << len(choices))
            if qbf_truth(clauses, encoding['prefix'],
                         {v: (a >> i) & 1 for i, v in enumerate(choices)})]


def inspect_control(name, circuit):
    encoding = quantified_groups(circuit)
    proof = scalar_certificate(circuit)
    check(circuit, proof)
    subsets = []
    for count in range(len(circuit['outputs']) + 1):
        for region in combinations(range(len(circuit['outputs'])), count):
            actual = choice_projection(encoding, region)
            expected = [a for a, support in enumerate(proof['policy_supports'])
                        if set(region) <= set(support)]
            if actual != expected:
                raise AssertionError((name, region, actual, expected))
            subsets.append({'labels': list(region), 'choices': actual})
    if not circuit['x_bits']:
        old = no_input_groups(circuit)
        if old != {key: encoding[key] for key in ('variable_count', 'groups')}:
            raise AssertionError('no-input layout changed')
    a, x, h = encoding['prefix']
    clauses = [clause for group in encoding['groups'] for clause in group]
    # These two deliberately wrong prefixes are semantic negative controls.
    hoisted = [a, h, x]
    input_choice = [x, a, h]
    return {'name': name, 'circuit': circuit, 'encoding': encoding,
            'circuit_certificate': proof, 'subset_projections': subsets,
            'whole_region_prefix_answers': {
                'exists_a_forall_x_exists_h': qbf_truth(clauses, encoding['prefix']),
                'exists_a_h_forall_x': qbf_truth(clauses, hoisted),
                'forall_x_exists_a_h': qbf_truth(clauses, input_choice)}}


def run(output):
    if not __debug__:
        raise RuntimeError('Run controls without Python -O/-OO.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    records = [inspect_control(name, circuit) for name, circuit in controls()]
    if records[0]['whole_region_prefix_answers'] != {
            'exists_a_forall_x_exists_h': True, 'exists_a_h_forall_x': False,
            'forall_x_exists_a_h': True}:
        raise AssertionError('input-dependent gate control failed')
    if records[1]['whole_region_prefix_answers'] != {
            'exists_a_forall_x_exists_h': False, 'exists_a_h_forall_x': False,
            'forall_x_exists_a_h': True}:
        raise AssertionError('fixed-choice control failed')
    summary = {'named_controls': [r['name'] for r in records],
               'label_subset_projections': sum(len(r['subset_projections']) for r in records),
               'projection_mismatches': 0, 'wrong_prefixes_distinguished': 2,
               'frozen_campaign_denominators': {'semantic': 1230, 'succinct': 6280},
               'scope': 'six authored tiny controls; no solver, novelty, timing or general-proof claim'}
    root = Path(__file__).resolve().parent.parent
    files = ['compatibility/group_constraints.py', 'compatibility/group_controls.py',
             'compatibility/succinct.py', 'compatibility/succinct_check.py',
             'tests/test_group_constraints.py', 'tests/test_group_quantifiers.py']
    bindings = {'python': sys.version, 'platform': platform.platform(),
                'command': [sys.executable, '-B', '-m', 'compatibility.group_controls',
                            '--output', str(output)],
                'sources': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                            for name in files}}
    for name, value in [('controls', records), ('summary', summary), ('bindings', bindings)]:
        (output / (name + '.json')).write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n',
            encoding='utf-8', newline='\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
