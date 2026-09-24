"""Replay the at-most-two-maxima / two-state-obstruction corollary.

The supplied support tables are first rechecked against their actual circuits.
Usage: python -m compatibility.structure_check --directory results/succinct
"""

if not __debug__:
    raise RuntimeError("Run finite evidence checks without Python -O/-OO.")

import argparse
import json
from pathlib import Path
from .succinct_check import check


def run(directory):
    directory=Path(directory);result=[]
    with (directory/'circuits.jsonl').open() as cf,(directory/'certificates.jsonl').open() as pf:
        for cline,pline in zip(cf,pf,strict=True):
            circuit=json.loads(cline);proof=json.loads(pline);check(circuit,proof)
            unique={tuple(s) for s in proof['policy_supports']}
            maxima=sorted(s for s in unique if not any(set(s)<set(t) for t in unique))
            assert len(maxima)==(1 if proof['greatest_exists'] else 2)
            core=None;witnesses=[]
            if not proof['greatest_exists']:
                core=[1,max(proof['support'])]
                assert all(not set(core)<=set(s) for s in unique)
                witnesses=[next(a for a,s in enumerate(proof['policy_supports']) if v in s) for v in core]
                assert maxima==sorted([tuple(v for v in proof['support'] if v!=core[0]),
                                       tuple(v for v in proof['support'] if v!=core[1])])
            result.append({'id':proof['id'],'maximal_regions':maxima,'two_state_core':core,'singleton_witnesses':witnesses})
    assert len(result)==6280
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    rows=run(p.parse_args().directory)
    print(json.dumps({'checked':len(rows),'unique_maximum':sum(r['two_state_core'] is None for r in rows),
                      'two_maxima_with_two_state_core':sum(r['two_state_core'] is not None for r in rows)},sort_keys=True))

if __name__=='__main__':main()
