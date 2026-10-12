"""Tiny exact CNF/subset checks; no SAT dependency or new campaign denominator."""
from itertools import combinations
import unittest

from compatibility.group_constraints import no_input_groups
from compatibility.succinct import scalar_certificate


def subsets(size):
    for count in range(size + 1):
        yield from combinations(range(size), count)


def models(encoding, region):
    clauses = [clause for label in region for clause in encoding['groups'][label]]
    return [assignment for assignment in range(1 << encoding['variable_count'])
            if all(any(bool(assignment & (1 << (abs(literal) - 1))) == (literal > 0)
                       for literal in clause) for clause in clauses)]


class GroupConstraintTests(unittest.TestCase):
    def assert_subset_projection(self, circuit):
        encoding = no_input_groups(circuit)
        proof = scalar_certificate(circuit)
        feasible = []
        for region in subsets(len(circuit['outputs'])):
            satisfying = models(encoding, region)
            projected = {assignment & ((1 << circuit['a_bits']) - 1)
                         for assignment in satisfying}
            expected = {a for a, support in enumerate(proof['policy_supports'])
                        if set(region) <= set(support)}
            self.assertEqual(projected, expected, region)
            if satisfying:
                feasible.append(set(region))
        maxima = [region for region in feasible
                  if not any(region < other for other in feasible)]
        self.assertEqual(len(maxima) == 1, proof['greatest_exists'])
        return encoding, maxima

    def test_all_gate_kinds_and_all_label_subsets(self):
        circuit = {'id': 'GateGroups', 'a_bits': 1, 'x_bits': 0,
                   'nodes': [['a', 0], ['const', 1], ['not', 0],
                             ['and', 0, 1], ['or', 2, 3]], 'outputs': [3, 2, 4]}
        encoding, maxima = self.assert_subset_projection(circuit)
        self.assertEqual(encoding['variable_count'], 16)
        self.assertEqual(maxima, [{0, 2}, {1, 2}])

    def test_an_internally_unsatisfiable_group_is_not_a_single_clause(self):
        circuit = {'id': 'FalseGroup', 'a_bits': 1, 'x_bits': 0,
                   'nodes': [['const', 0], ['a', 0]], 'outputs': [0, 1]}
        encoding, maxima = self.assert_subset_projection(circuit)
        self.assertEqual(maxima, [{1}])
        # Every individual clause is nonempty and satisfiable. Flattening them
        # destroys the atomic version label and makes the whole CNF UNSAT.
        flattened = [clause for group in encoding['groups'] for clause in group]
        self.assertTrue(all(clause for clause in flattened))
        self.assertFalse(models(encoding, [0, 1]))

    def test_duplicate_outputs_keep_distinct_version_labels(self):
        circuit = {'id': 'DuplicateGroups', 'a_bits': 1, 'x_bits': 0,
                   'nodes': [['a', 0]], 'outputs': [0, 0]}
        encoding, maxima = self.assert_subset_projection(circuit)
        self.assertEqual(maxima, [{0, 1}])
        self.assertEqual(len(encoding['groups']), 2)
        self.assertNotEqual(encoding['groups'][0], encoding['groups'][1])

    def test_runtime_inputs_cannot_be_moved_into_constant_gate_witnesses(self):
        circuit = {'id': 'QuantifiedGroup', 'a_bits': 1, 'x_bits': 1,
                   'nodes': [['x', 0]], 'outputs': [0]}
        with self.assertRaises(ValueError):
            no_input_groups(circuit)
