"""Independent bounded circuit checker using full truth vectors.

Imports neither the generator nor its scalar evaluator. This checks finite
circuits/certificates, not the general polynomial-hierarchy theorem.
"""
from __future__ import annotations
from functools import lru_cache
import json

class Rejected(ValueError):
    pass


def read_json_line(line, byte_limit=2_000_000):
    """Strict JSONL decoding at the structure-replay boundary."""
    if len(line.encode('utf-8')) > byte_limit:
        raise Rejected('JSON line byte bound')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise Rejected('duplicate JSON key')
            value[key] = item
        return value
    def nonfinite(_):
        raise Rejected('non-finite JSON number')
    try:
        return json.loads(line, object_pairs_hook=unique, parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Rejected('invalid JSON line') from exc


def integer(value, lo, hi):
    return type(value) is int and lo <= value <= hi


def admit(c):
    if not isinstance(c,dict) or set(c) != {'id','a_bits','x_bits','nodes','outputs'}:
        raise Rejected('invalid circuit fields')
    if not isinstance(c['id'],str) or not c['id'].isalnum():
        raise Rejected('invalid identifier')
    if not integer(c['a_bits'],1,8) or not integer(c['x_bits'],0,4):
        raise Rejected('circuit input bound exceeded')
    if not isinstance(c['nodes'],list) or not 1 <= len(c['nodes']) <= 6000:
        raise Rejected('circuit size bound exceeded')
    for i,node in enumerate(c['nodes']):
        if not isinstance(node,list) or not node:
            raise Rejected('invalid gate')
        op,*args = node
        if not isinstance(op,str): raise Rejected('invalid operator')
        arity = {'const':1,'a':1,'x':1,'not':1,'and':2,'or':2}.get(op)
        if arity is None or len(args) != arity:
            raise Rejected('invalid gate arity')
        if op == 'const': hi = 1
        elif op == 'a': hi = c['a_bits']-1
        elif op == 'x': hi = c['x_bits']-1
        else: hi = i-1
        if any(not integer(a,0,hi) for a in args):
            raise Rejected('invalid input or backward reference')
    if not isinstance(c['outputs'],list) or not 1 <= len(c['outputs']) <= 32:
        raise Rejected('output bound exceeded')
    if any(not integer(a,0,len(c['nodes'])-1) for a in c['outputs']):
        raise Rejected('invalid output')


@lru_cache(maxsize=100)
def variable(bits, position):
    width = 1 << position
    block = (1 << width)-1
    return sum(block << start for start in range(width,1 << bits,2*width))


def certificate(c,accounting=None):
    admit(c)
    bits = c['a_bits']+c['x_bits']; all_rows = (1 << (1 << bits))-1
    rows = []
    for op,*args in c['nodes']:
        if op == 'a': out = variable(bits,args[0])
        elif op == 'x': out = variable(bits,c['a_bits']+args[0])
        elif op == 'const': out = all_rows if args[0] else 0
        elif op == 'not': out = all_rows ^ rows[args[0]]
        elif op == 'and': out = rows[args[0]] & rows[args[1]]
        else: out = rows[args[0]] | rows[args[1]]
        rows.append(out)
    a_count = 1 << c['a_bits']; a_mask = (1 << a_count)-1
    robust = []
    for idx in c['outputs']:
        good = a_mask
        for x in range(1 << c['x_bits']):
            good &= (rows[idx] >> (a_count*x)) & a_mask
        robust.append(good)
    supports = [[v for v,mask in enumerate(robust) if mask & (1 << a)] for a in range(a_count)]
    union = [v for v,mask in enumerate(robust) if mask]
    witness = next((a for a,s in enumerate(supports) if s == union),None)
    if accounting is not None:
        accounting['bitvector_gate_steps'] = accounting.get('bitvector_gate_steps',0)+len(c['nodes'])
        accounting['local_truth_assignments'] = accounting.get('local_truth_assignments',0)+(1 << bits)
        accounting['output_truth_assignments'] = accounting.get('output_truth_assignments',0)+(1 << bits)*len(c['outputs'])
    return {'id':c['id'],'support':union,'policy_supports':supports,'greatest_exists':witness is not None,'least_policy':witness}


def check(c, proof,accounting=None):
    expected = certificate(c,accounting)
    try:
        actual = json.dumps(proof,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError) as exc:
        raise Rejected('invalid proof encoding') from exc
    if actual != json.dumps(expected,sort_keys=True,separators=(',',':')):
        raise Rejected('not the complete exact certificate')
    return True
