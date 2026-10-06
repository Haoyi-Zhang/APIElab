"""Exhaustive bounded tests of the succinct-principality reduction.

Usage: python -m compatibility.succinct_campaign --output FRESH_DIRECTORY
The output directory is exclusive-created. No solver, network, or child process.
"""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("Run finite evidence checks without Python -O/-OO.")
import argparse
from collections import Counter
from copy import deepcopy
import csv
import json
from pathlib import Path
import time
from .succinct import instances, construct, scalar_certificate, evaluate_nodes
from .succinct_check import certificate, check, Rejected
from .measurement import configure_limits, snapshot


def oracle(case):
    q = len(case['queries']); quant = case['quantified']
    b = 0
    for i,table in enumerate(case['queries']):
        yes = any(all((table >> (y+2*x)) & 1 for x in (0,1)) for y in (0,1)) if quant else bool(table)
        b |= int(yes) << i
    k = max(2*z.bit_count()+1-((case['post_table']>>z)&1) for z in range(1<<q) if z & ~b == 0)
    supports=[]
    for a in range(1 << (1+q+(q if quant else 0))):
        t=a&1; z=(a>>1)&((1<<q)-1); y=a>>(q+1)
        valid = True
        for i,table in enumerate(case['queries']):
            if z & (1 << i):
                good = all((table >> (((y>>i)&1)+2*x))&1 for x in (0,1)) if quant else bool(table)
                valid &= good
        score=2*z.bit_count()+1-((case['post_table']>>z)&1)
        support=[0]+([1] if t==0 else [])
        for j in range(1,2*q+2):
            if valid and score>=j and (score>=j+1 or t==j%2): support.append(j+1)
        supports.append(support)
    return b,k,bool((case['post_table']>>b)&1),supports


def run(output:Path, *, inject_failure_after_create=False):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    # A failed run retains the fresh path it exclusively created; existing paths
    # are rejected and are never removed or overwritten.
    if inject_failure_after_create:
        raise RuntimeError('injected failure after exclusive output creation')
    limits = configure_limits(40)
    start_cpu=time.process_time();start_wall=time.monotonic()
    accounting={}; counts=Counter(); maxima=Counter()
    streams={n:(output/(n+'.jsonl')).open('w',encoding='utf-8',newline='\n') for n in ('cases','circuits','certificates')}
    def emit(name,data):
        streams[name].write(json.dumps(data,separators=(',',':'),sort_keys=True)+'\n')
    fields=['id','quantified','queries','a_bits','x_bits','history_states','gates','oracle_answers','maximum_score','greatest_exists','least_policy']
    with (output/'per_case.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        try:
            for case in instances():
                circuit=construct(case); proof=scalar_certificate(circuit)
                check(circuit,proof,accounting)
                b,k,expected,supports=oracle(case)
                assert proof['policy_supports']==supports,(case,'whole-policy oracle mismatch')
                assert proof['greatest_exists']==expected,(case,'decision mismatch')
                assert k==2*b.bit_count()+1-int(expected)
                assert proof['support']==list(range(k+2)),(case,'support-prefix mismatch')
                assert proof['greatest_exists']==(k%2==0)
                counts['quantified' if case['quantified'] else 'constant']+=1
                counts['greatest_exists' if expected else 'no_greatest']+=1
                for key,changed in (
                    ('flip_decision',dict(proof,greatest_exists=not proof['greatest_exists'])),
                    ('omit_policy',dict(proof,policy_supports=proof['policy_supports'][:-1])),
                    ('wrong_identifier',dict(proof,id=proof['id']+'X'))):
                    try: check(circuit,changed,accounting)
                    except Rejected: counts['rejected_'+key]+=1
                    else: raise AssertionError(('accepted mutation',case['id'],key))
                maxima['a_bits']=max(maxima['a_bits'],circuit['a_bits'])
                maxima['x_bits']=max(maxima['x_bits'],circuit['x_bits'])
                maxima['history_states']=max(maxima['history_states'],len(circuit['outputs']))
                maxima['gates']=max(maxima['gates'],len(circuit['nodes']))
                counts['scalar_global_assignments']+=(1<<(circuit['a_bits']+circuit['x_bits']))
                counts['scalar_gate_steps']+=len(circuit['nodes'])*(1<<(circuit['a_bits']+circuit['x_bits']))
                counts['scalar_version_evaluations']+=len(circuit['outputs'])*(1<<(circuit['a_bits']+circuit['x_bits']))
                emit('cases',case);emit('circuits',circuit);emit('certificates',proof)
                writer.writerow({'id':case['id'],'quantified':int(case['quantified']),'queries':len(case['queries']),
                    'a_bits':circuit['a_bits'],'x_bits':circuit['x_bits'],'history_states':len(circuit['outputs']),
                    'gates':len(circuit['nodes']),'oracle_answers':b,'maximum_score':k,
                    'greatest_exists':int(expected),'least_policy':'' if proof['least_policy'] is None else proof['least_policy']})
        finally:
            for f in streams.values():f.close()
    assert counts['constant']==2120 and counts['quantified']==4160
    # Actual formula-level negative controls, separate from certificate mutations.
    anchor_case={'id':'N001','quantified':False,'queries':[1],'post_table':0}
    anchored=construct(anchor_case); omitted=deepcopy(anchored);omitted['outputs'].pop(1)
    anchored_answer=certificate(anchored)['greatest_exists'];omitted_answer=certificate(omitted)['greatest_exists']
    assert not anchored_answer and omitted_answer
    # Weight one no longer makes cardinality dominate postprocessing.
    weight_one_case={'truth_vector':1,'post_table':2,'q':1}
    k1=max(z.bit_count()+1-((2>>z)&1) for z in (0,1))
    assert k1==1
    # Equality y=x admits an input-dependent response but no fixed y.
    ea=any(all(y==x for x in (0,1)) for y in (0,1))
    ae=all(any(y==x for y in (0,1)) for x in (0,1))
    assert not ea and ae

    # Fixed selections precede the universal runtime input.  C1=x and
    # C2=not x are each false under exists-witness/forall-input semantics, so
    # both the individually viable count u and shared-choice maximum s are zero.
    c1=lambda x: x
    c2=lambda x: 1-x
    fixed_rows=[{'x':x,'C1':c1(x),'C2':c2(x)} for x in (0,1)]
    u=sum(all(row[name] for row in fixed_rows) for name in ('C1','C2'))
    s=max(sum(all(row[name] for row in fixed_rows) for name in ('C1','C2')) for _a in (0,1))
    assert (u,s)==(0,0)

    boundary=[]
    for q in (1,2):
        for label,case,wanted in (
            ('minimum',{'id':f'B{q}L','quantified':False,'queries':[0]*q,'post_table':1},0),
            ('maximum',{'id':f'B{q}H','quantified':False,'queries':[1]*q,'post_table':0},2*q+1)):
            circuit,layout=construct(case,with_layout=True)
            b,k,expected,_=oracle(case)
            assert k==wanted and len(circuit['outputs'])==2*q+3
            assert all(evaluate_nodes(circuit,a,0)[layout['sentinel']]==0
                       for a in range(1<<circuit['a_bits']))
            proof=scalar_certificate(circuit)
            assert proof['support']==list(range(k+2))
            assert proof['greatest_exists']==expected==(k%2==0)
            boundary.append({'q':q,'endpoint':label,'oracle_answers':b,
                             'K':k,'output_count':len(circuit['outputs']),
                             'sentinel':f'T{2*q+2}','sentinel_always_false':True,
                             'support':proof['support'],'greatest_exists':expected})

    negative={'anchor_omission':{'input':anchor_case,'correct':anchored_answer,'without_anchor':omitted_answer},
              'weight_one':{'input':weight_one_case,'actual_postprocessing':True,'maximum_score':k1,'parity_prediction':False},
              'quantifier_swap':{'query_table':9,'exists_y_forall_x':ea,'forall_x_exists_y':ae},
              'fixed_selection_truth_table':{'formula_order':'exists choice,selection; forall input',
                  'C1':'x','C2':'not x','rows':fixed_rows,'u':u,'s':s},
              'construction_boundaries':boundary}
    summary={'cases':6280,'counts':dict(counts),'checker_including_three_mutations_per_case':accounting,
             'maxima':dict(maxima),'oracle_mismatches':0,'negative_controls':3,
             'construction_boundary_checks':len(boundary),'fixed_selection_truth_table':{'u':u,'s':s},
             'scope':'exhaustive stated truth-table families; scalar whole-policy enumeration and independent truth-vector checks; not a mechanized asymptotic proof'}
    measurement=snapshot(start_cpu,start_wall,limits,
        measurement_scope='scalar campaign including direct oracles, mutations and output writing')
    for name,data in [('summary',summary),('measurement',measurement),('negative_controls',negative)]:
        (output/(name+'.json')).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'summary':summary,'measurement':measurement},indent=2,sort_keys=True))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)

if __name__=='__main__': main()
