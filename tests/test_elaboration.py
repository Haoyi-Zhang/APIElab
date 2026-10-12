"""Semantic checks of the authored polarity adapter, outside frozen campaigns."""
from copy import deepcopy
import unittest

from compatibility.cases import declaration
from compatibility.elaboration import elaborate_request
from compatibility.infer import infer
from compatibility.replay import check
from compatibility.uniform import solve
from compatibility.uniform_check import check as check_uniform


def request_case(expression, polarity, inputs):
    # Reference harness executes the source request, independently of polarity.
    # Only states 1 and 2 execute the elaborated term; neither can distinguish
    # its version inside that term. The guard is not synthesized adapter code.
    return {'id': 'PolarityRequest', 'reference': 0, 'inputs': list(inputs),
            'trace_limit': 0,
            'history': [{}, {'decode': declaration(2)},
                        {'decode': declaration(1)}],
            'client': {'op': 'if_version', 'min': 1,
                       'then': elaborate_request(expression, polarity),
                       'else': {'op': 'return', 'value': deepcopy(expression)}}}


class ElaborationTests(unittest.TestCase):
    def test_preservation_for_polarities_expressions_and_input_domains(self):
        expressions = [({'const': 0}, lambda x: 0),
                       ({'const': 1}, lambda x: 1),
                       ({'var': 'x'}, lambda x: x),
                       ({'not': {'var': 'x'}}, lambda x: 1 - x),
                       ({'not': {'not': {'var': 'x'}}}, lambda x: x)]
        for expression, source in expressions:
            for polarity in (0, 1):
                for inputs in ([0], [1], [0, 1]):
                    with self.subTest(expression=expression, a=polarity, X=inputs):
                        case = request_case(expression, polarity, inputs)
                        proof, _ = infer(case)
                        check(deepcopy(case), proof)
                        self.assertEqual(proof['region'], [0, polarity + 1])
                        for row in proof['rows']:
                            state, x = row['state'], row['input']
                            expected = source(x) if state == 0 else source(x) ^ polarity ^ (state - 1)
                            self.assertEqual(row['outcome'],
                                             {'value': expected, 'trace': [], 'error': None})

    def test_semantically_derived_uniform_conflict_and_refinement(self):
        regions = [infer(request_case({'var': 'x'}, a, [0, 1]))[0]['region']
                   for a in (0, 1)]
        matrix = {'choices': 2, 'blocks': [0, 0, 0],
                  'safe_choices': [[a for a, region in enumerate(regions) if v in region]
                                   for v in range(3)]}
        self.assertEqual(matrix['safe_choices'], [[0, 1], [0], [1]])
        proof = solve(matrix)
        check_uniform(matrix, proof)
        self.assertIsNone(proof['greatest_region'])
        self.assertEqual(proof['obstruction']['states'], [1, 2])
        refined = dict(matrix, blocks=[0, 0, 1])
        proof = solve(refined)
        check_uniform(refined, proof)
        self.assertEqual(proof['greatest_region'], [0, 1, 2])
        self.assertEqual(proof['policy'], [0, 1])

    def test_adapter_has_no_observation_or_default_and_does_not_alias_source(self):
        source = {'var': 'x'}
        for a in (0, 1):
            target = elaborate_request(source, a)
            self.assertEqual(target['op'], 'let')
            self.assertIsNotNone(target['arg'])
            self.assertEqual(target['body']['op'], 'return')
            source['var'] = 'changed'
            argument = target['arg'] if a == 0 else target['arg']['not']
            self.assertEqual(argument, {'var': 'x'})
            source['var'] = 'x'

    def test_polarity_rejects_non_bits_and_boolean_integer_aliases(self):
        for a in (False, True, -1, 2, '0', None):
            with self.subTest(a=a), self.assertRaises(ValueError):
                elaborate_request({'var': 'x'}, a)
