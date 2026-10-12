"""Subset-preserving group-CNF translation of admitted no-input circuits.

Every version label selects all gate definitions plus its asserted output.
Gate variables are private to that label; choice variables remain shared.
There are no hard/background clauses. The translation is polynomial-size,
but exhaustive assignment checking is intended only for tiny tests.
This is not a quantified-CNF translation: runtime-input circuits are rejected.
"""
from .succinct_check import admit


def no_input_groups(circuit):
    admit(circuit)
    if circuit['x_bits']:
        raise ValueError('group-CNF translation requires no runtime inputs')
    width = circuit['a_bits']
    nodes = circuit['nodes']
    groups = []
    for label, output in enumerate(circuit['outputs']):
        offset = width + label * len(nodes)
        clauses = []
        for index, node in enumerate(nodes):
            op, *args = node
            result = offset + index + 1
            if op == 'const':
                clauses.append([result if args[0] else -result])
            elif op == 'a':
                choice = args[0] + 1
                clauses.extend([[-result, choice], [result, -choice]])
            elif op == 'not':
                operand = offset + args[0] + 1
                clauses.extend([[-result, -operand], [result, operand]])
            else:
                left, right = (offset + argument + 1 for argument in args)
                if op == 'and':
                    clauses.extend([[-result, left], [-result, right],
                                    [result, -left, -right]])
                else:  # admission restricted this remaining operator to 'or'
                    clauses.extend([[result, -left], [result, -right],
                                    [-result, left, right]])
        clauses.append([offset + output + 1])
        groups.append(clauses)
    return {'variable_count': width + len(groups) * len(nodes), 'groups': groups}
