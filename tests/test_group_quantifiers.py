"""Six semantic-prefix controls, separate from both frozen campaigns."""
from copy import deepcopy
import unittest

from compatibility.group_constraints import no_input_groups, quantified_groups
from compatibility.group_controls import controls, inspect_control


class GroupQuantifierTests(unittest.TestCase):
    def receipt(self, index):
        name, circuit = controls()[index]
        return inspect_control(name, circuit)

    def test_input_dependent_gate_witness(self):
        record = self.receipt(0)
        self.assertEqual(record['subset_projections'][1]['choices'], [0, 1])
        self.assertEqual(record['whole_region_prefix_answers'], {
            'exists_a_forall_x_exists_h': True, 'exists_a_h_forall_x': False,
            'forall_x_exists_a_h': True})

    def test_choice_stays_before_input(self):
        record = self.receipt(1)
        self.assertEqual(record['subset_projections'][1]['choices'], [])
        self.assertEqual(record['circuit_certificate']['support'], [])
        self.assertTrue(record['circuit_certificate']['greatest_exists'])
        self.assertEqual(record['whole_region_prefix_answers'], {
            'exists_a_forall_x_exists_h': False, 'exists_a_h_forall_x': False,
            'forall_x_exists_a_h': True})

    def test_atomic_opposite_choice_groups(self):
        record = self.receipt(2)
        self.assertEqual(record['subset_projections'], [
            {'labels': [], 'choices': [0, 1]}, {'labels': [0], 'choices': [1]},
            {'labels': [1], 'choices': [0]}, {'labels': [0, 1], 'choices': []}])
        self.assertFalse(record['circuit_certificate']['greatest_exists'])
        self.assertEqual(record['circuit_certificate']['support'], [0, 1])

    def test_all_gate_operators(self):
        record = self.receipt(3)
        self.assertEqual(record['subset_projections'][1]['choices'], [0, 1])
        encoding = record['encoding']
        self.assertEqual([block['quantifier'] for block in encoding['prefix']],
                         ['exists', 'forall', 'exists'])
        self.assertEqual([v for block in encoding['prefix'] for v in block['variables']],
                         list(range(1, encoding['variable_count'] + 1)))

    def test_empty_region_with_impossible_group(self):
        record = self.receipt(4)
        self.assertEqual(record['subset_projections'], [
            {'labels': [], 'choices': [0, 1]}, {'labels': [0], 'choices': []}])
        self.assertTrue(record['circuit_certificate']['greatest_exists'])
        self.assertEqual(record['circuit_certificate']['support'], [])

    def test_no_input_duplicate_labels_and_legacy_guard(self):
        record = self.receipt(5)
        self.assertEqual(record['circuit_certificate']['support'], [0, 1])
        self.assertEqual(record['subset_projections'][-1]['choices'], [1])
        self.assertEqual(record['encoding']['prefix'][1]['variables'], [])
        for _name, circuit in controls()[:5]:
            with self.assertRaises(ValueError):
                no_input_groups(circuit)
        circuit = deepcopy(controls()[0][1])
        circuit['nodes'][0] = ['not', 0]
        with self.assertRaises(ValueError):
            quantified_groups(circuit)
