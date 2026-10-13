"""Subset-preserving atomic groups for admitted Boolean circuits.

Every version label selects all gate definitions plus its asserted output.
Gate variables are private to that label; choice variables remain shared.
There are no hard/background clauses. The translation is polynomial-size,
but exhaustive assignment checking is intended only for tiny tests.
The no-input interface rejects runtime inputs. The separate quantified
interface binds choices before inputs, and private gate witnesses after them.
That prefix is not ordinary group-CNF satisfiability.
"""
from .succinct_check import admit


def no_input_groups(circuit):
    admit(circuit)
    if circuit['x_bits']:
        raise ValueError('group-CNF translation requires no runtime inputs')
    return _groups(circuit)


def quantified_groups(circuit):
    """Encode exists a / forall x / exists h, preserving every label subset.

    For fixed a,x the gate equivalences force a unique h in each selected
    group. Only these definitional witnesses may depend on runtime inputs;
    the original elaboration choice a remains outside the universal block.
    Unselected groups impose no clauses. There are no background clauses.
    """
    admit(circuit)
    encoding = _groups(circuit)
    a_end = circuit['a_bits']
    x_end = a_end + circuit['x_bits']
    encoding['prefix'] = [
        {'quantifier': 'exists', 'variables': list(range(1, a_end + 1))},
        {'quantifier': 'forall', 'variables': list(range(a_end + 1, x_end + 1))},
        {'quantifier': 'exists',
         'variables': list(range(x_end + 1, encoding['variable_count'] + 1))},
    ]
    return encoding


def _groups(circuit):
    # Admission is performed by each public entry point. Keeping the exact
    # old layout when x_bits=0 preserves the existing no-input encoding.
    width = circuit['a_bits'] + circuit['x_bits']
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
            elif op in ('a', 'x'):
                variable = args[0] + 1 + (circuit['a_bits'] if op == 'x' else 0)
                clauses.extend([[-result, variable], [result, -variable]])
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
