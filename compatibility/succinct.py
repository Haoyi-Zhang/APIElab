"""Bounded Boolean-circuit instances of the parallel-oracle reduction.

All gate inputs precede their users. Each history uses one common immutable
choice (t,z,y) and one universally quantified input x. The generator does not
ask whether the input oracle queries are true. It constructs their circuits.
"""
from __future__ import annotations
from itertools import product


def bit(number: int, position: int) -> int:
    return (number >> position) & 1


class Circuit:
    def __init__(self, a_bits: int, x_bits: int):
        self.a_bits, self.x_bits = a_bits, x_bits
        self.nodes: list[list] = []

    def gate(self, op: str, *args: int) -> int:
        self.nodes.append([op, *args])
        return len(self.nodes)-1

    def conjunction(self, nodes: list[int]) -> int:
        out = self.gate('const', 1)
        for node in nodes:
            out = self.gate('and', out, node)
        return out

    def disjunction(self, nodes: list[int]) -> int:
        out = self.gate('const', 0)
        for node in nodes:
            out = self.gate('or', out, node)
        return out

    def table(self, nodes: list[int], table: int) -> int:
        # Truth tables are explicit inputs in this bounded test family.
        clauses = []
        for mask in range(1 << len(nodes)):
            if bit(table, mask):
                clauses.append(self.conjunction([
                    node if bit(mask,i) else self.gate('not',node)
                    for i,node in enumerate(nodes)]))
        return self.disjunction(clauses)

    def at_least(self, nodes: list[int], k: int) -> int:
        # Dynamic-programming cardinality circuit; polynomial even when the
        # postprocessing function is supplied as a circuit rather than a table.
        if k <= 0:
            return self.gate('const', 1)
        if k > len(nodes):
            return self.gate('const', 0)
        previous = [self.gate('const',1)] + [self.gate('const',0) for _ in range(k)]
        for node in nodes:
            current = [previous[0]]
            for j in range(1,k+1):
                current.append(self.gate('or',previous[j],self.gate('and',node,previous[j-1])))
            previous = current
        return previous[k]


def validate(case: dict) -> None:
    if not isinstance(case,dict) or set(case) != {'id','quantified','queries','post_table'}:
        raise ValueError('invalid succinct input fields')
    if not isinstance(case['id'],str) or not case['id'].isalnum():
        raise ValueError('invalid case identifier')
    if type(case['quantified']) is not bool or not isinstance(case['queries'],list):
        raise ValueError('invalid quantified flag or queries')
    q = len(case['queries'])
    if q not in (1,2,3) or (case['quantified'] and q > 2):
        raise ValueError('outside the bounded reduction-test domain')
    high = 16 if case['quantified'] else 2
    if any(type(t) is not int or not 0 <= t < high for t in case['queries']):
        raise ValueError('invalid query truth table')
    if type(case['post_table']) is not int or not 0 <= case['post_table'] < (1 << (1 << q)):
        raise ValueError('invalid postprocessing table')


def construct(case: dict, *, with_layout: bool = False):
    validate(case)
    q = len(case['queries']); quant = case['quantified']
    c = Circuit(1+q+(q if quant else 0),q if quant else 0)
    t = c.gate('a',0)
    z = [c.gate('a',1+i) for i in range(q)]
    y = [c.gate('a',1+q+i) for i in range(q)] if quant else []
    x = [c.gate('x',i) for i in range(q)] if quant else []
    clauses = []
    for i,table in enumerate(case['queries']):
        query = c.table([y[i],x[i]],table) if quant else c.gate('const',table)
        clauses.append(c.gate('or',c.gate('not',z[i]),query))
    valid = c.conjunction(clauses)
    not_g = c.gate('not',c.table(z,case['post_table']))
    thresholds = []
    for j in range(1,2*q+3):
        if j % 2 == 0:
            score = c.at_least(z,j//2)
        else:
            h = j//2
            score = c.gate('or',c.at_least(z,h+1),c.gate('and',c.at_least(z,h),not_g))
        thresholds.append(c.gate('and',valid,score))
    # Version zero is an always-compatible reference. Version one is the tag
    # anchor; the remaining versions are D_1 through D_(2q+1).
    outputs = [c.gate('const',1),c.gate('not',t)]
    for j in range(1,2*q+2):
        tag = t if j % 2 else c.gate('not',t)
        outputs.append(c.gate('and',thresholds[j-1],c.gate('or',thresholds[j],tag)))
    circuit={'id':case['id'],'a_bits':c.a_bits,'x_bits':c.x_bits,'nodes':c.nodes,'outputs':outputs}
    if with_layout:
        return circuit, {'thresholds':thresholds, 'sentinel':thresholds[-1]}
    return circuit


def evaluate_nodes(circuit: dict, a: int, x: int) -> list[int]:
    """Evaluate every node in topological order (test/audit helper)."""
    values = []
    for node in circuit['nodes']:
        op,*args = node
        if op == 'a': v = bit(a,args[0])
        elif op == 'x': v = bit(x,args[0])
        elif op == 'const': v = args[0]
        elif op == 'not': v = 1-values[args[0]]
        elif op == 'and': v = values[args[0]] & values[args[1]]
        elif op == 'or': v = values[args[0]] | values[args[1]]
        else: raise ValueError('unknown circuit gate')
        values.append(v)
    return values


def evaluate(circuit: dict, a: int, x: int) -> list[int]:
    values=evaluate_nodes(circuit,a,x)
    return [values[i] for i in circuit['outputs']]


def scalar_certificate(circuit: dict) -> dict:
    supports = []
    for a in range(1 << circuit['a_bits']):
        good = [True]*len(circuit['outputs'])
        for x in range(1 << circuit['x_bits']):
            good = [old and bool(new) for old,new in zip(good,evaluate(circuit,a,x))]
        supports.append([i for i,yes in enumerate(good) if yes])
    union = sorted(set().union(*(set(s) for s in supports)))
    witness = next((a for a,s in enumerate(supports) if s == union),None)
    return {'id':circuit['id'],'support':union,'policy_supports':supports,'greatest_exists':witness is not None,'least_policy':witness}


def instances():
    index = 0
    for quant,top in ((False,3),(True,2)):
        for q in range(1,top+1):
            for queries in product(range(16 if quant else 2),repeat=q):
                for g in range(1 << (1 << q)):
                    index += 1
                    yield {'id':f'R{index:05d}','quantified':quant,'queries':list(queries),'post_table':g}
