"""One-worker exhaustive pilot, independent oracles, and certificate mutations.

Run from the repository root: python -m compatibility.pilot --output PATH
Only stdlib; bounded computation on owned finite data; no networking/subprocesses.
"""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("Run finite evidence checks without Python -O/-OO.")
import argparse
import csv
import json
import os
import resource
import time
from collections import Counter
from copy import deepcopy
from itertools import product
from pathlib import Path
from .cases import (history_cases, effect_history_cases, controls,
                    truth_table_oracle, effect_oracle, uniform_problems)
from .scholarly import scholarly_cases, source_records
from .infer import infer
from .replay import check, Rejected
from .uniform import solve
from .uniform_check import check as uniform_check


def bounds():
    if hasattr(os, 'sched_getaffinity'):
        available = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(available)})
    resource.setrlimit(resource.RLIMIT_AS, (768*1024*1024, 768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    os.environ['OMP_NUM_THREADS'] = '1'


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')
    temp.replace(path)


def write_lines(path, values):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for v in values:
            f.write(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n')


def csv_file(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('empty result table')
    with path.open('w', newline='', encoding='utf-8') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def syntactic_apis(term):
    pending=[term]; names=set()
    while pending:
        t=pending.pop()
        if t['op']=='let': names.add(t['api']); pending.append(t['body'])
        elif t['op'] in ('if','if_present','if_version'): pending.extend([t['then'],t['else']])
    return names


def predictions(case, cert):
    hist=case['history']; n=len(hist); names=syntactic_apis(case['client'])
    intro=max((next((i for i,h in enumerate(hist) if a in h),n) for a in names), default=0)
    safe=set(cert['region'])
    hull=set(range(min(safe),max(safe)+1))
    runs=[]
    for v in sorted(safe):
        if runs and v==runs[-1][-1]+1: runs[-1].append(v)
        else: runs.append([v])
    largest=set(min(runs,key=lambda r:(-len(r),r[0])))
    return {'minimum_introduction':set(range(intro,n)),
            'syntactic_availability':{i for i,h in enumerate(hist) if names <= set(h)},
            'interval_hull':hull, 'largest_sound_interval':largest}


def mutations(cert):
    variants=[]
    def emit(name, change):
        altered=deepcopy(cert); change(altered); variants.append((name,altered))
    emit('omit_row',lambda c:c['rows'].pop())
    emit('reorder_rows',lambda c:c['rows'].reverse())
    emit('duplicate_row',lambda c:c['rows'].append(deepcopy(c['rows'][0])))
    successful=next(i for i,row in enumerate(cert['rows']) if row['outcome']['value'] is not None)
    emit('flip_result',lambda c:c['rows'][successful]['outcome'].__setitem__(
         'value',1-c['rows'][successful]['outcome']['value']))
    emit('boolean_as_integer',lambda c:c['rows'][0].__setitem__('input',False))
    emit('omit_safe_reference',lambda c:c['region'].remove(c['region'][0]))
    emit('false_least_witness',lambda c:c.__setitem__('least_counterexample',{'state':99,'input':0}))
    emit('wrong_identity',lambda c:c.__setitem__('case_id',c['case_id']+'z'))
    emit('unknown_field',lambda c:c.__setitem__('extra',0))
    emit('false_trace',lambda c:c['rows'][0]['outcome']['trace'].append('a'))
    target=next((i for i,row in enumerate(cert['rows']) if row['calls']),None)
    if target is not None:
        emit('false_call_log',lambda c:c['rows'][target]['calls'][0].__setitem__('api','wrong'))
    return variants


def trace_sensitivity(case, cert):
    def region(mode):
        projected={}
        for row in cert['rows']:
            out=row['outcome']
            if mode=='all_events': trace=()
            else: trace=tuple(a for call in row['calls'] for a in call['body_trace'])
            projected[row['state'],row['input']]=(out['value'],trace,out['error'])
        return [v for v in range(len(case['history'])) if all(
            projected[v,x][2] is None and projected[v,x]==projected[case['reference'],x]
            for x in case['inputs'])]
    return {'all_events_erased':region('all_events'), 'default_events_erased':region('defaults')}


def run(output):
    bounds()
    begin_wall=time.monotonic(); begin_cpu=time.process_time()
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    inp=output/'inputs'; res=output/'results'
    inp.mkdir(parents=True,exist_ok=True); res.mkdir(parents=True,exist_ok=True)
    truth_family=list(history_cases())
    effect_family=list(effect_history_cases())
    scholarly=scholarly_cases()
    special=controls()
    generated=truth_family+effect_family
    campaign=generated+[c for c,_,_ in scholarly]
    cases=campaign+[c for c,_ in special]
    assert len(truth_family)==600 and len(effect_family)==600
    assert len(generated)==1200 and len(scholarly)==30 and len(campaign)==1230
    assert len(special)==16 and len(cases)==1246
    write_lines(inp/'semantic_cases.jsonl',cases)
    write_json(inp/'scholarly_case_sources.json',
               {'sources':source_records(),'cases':[m for _,_,m in scholarly]})
    write_json(inp/'scholarly_expectations.json',[e for _,e,_ in scholarly])
    write_json(inp/'control_expectations.json',[e for _,e in special])
    certs=[]; raw=[]; base=Counter(); mutate=Counter(); steps=Counter(); maxima=Counter()
    sensitivity=[]; replay_accounting=Counter()
    for index,case in enumerate(cases):
        cert,metrics=infer(case); checked=check(case,cert,replay_accounting)
        if index < 600:
            oracle=truth_table_oracle(case,index%6)
            assert all(cert[k]==v for k,v in oracle.items()), (case['id'],'truth-table mismatch')
        elif index < 1200:
            oracle=effect_oracle(case,(index-600)%6)
            assert all(cert[k]==v for k,v in oracle.items()), (case['id'],'effect-oracle mismatch')
        elif index < 1230:
            expected=scholarly[index-1200][1]
            assert cert['region']==expected['region'] and cert['least_counterexample']==expected['least_counterexample'], case['id']
            sensitivity.append(dict(id=case['id'], family='scholarly_projection',
                                    exact_region=cert['region'], **trace_sensitivity(case,cert)))
        else:
            expected=special[index-1230][1]
            assert cert['region']==expected['region'] and cert['least_counterexample']==expected['least_counterexample'], case['id']
            sensitivity.append(dict(id=case['id'], family='regression_control',
                                    exact_region=cert['region'], **trace_sensitivity(case,cert)))
        certs.append(cert)
        safe=set(cert['region']); n=len(case['history'])
        for name,pred in predictions(case,cert).items():
            base[name+'_false_accept']+=len(pred-safe)
            base[name+'_false_reject']+=len(safe-pred)
            base[name+'_decisions']+=n
        for key in ('evaluation_steps','certificate_nodes','executions'):
            steps[key]+=metrics[key]
        steps['checker_steps']+=checked['checker_steps']
        for key in ('states','declarations','call_sites','ast_nodes','max_trace','certificate_nodes'):
            maxima[key]=max(maxima[key],metrics[key])
        for name,altered in mutations(cert):
            assert altered != cert or name=='boolean_as_integer'
            try:
                check(case,altered,replay_accounting)
            except Rejected:
                mutate[name]+=1
            else:
                raise AssertionError((case['id'],'accepted faulty certificate',name))
        family=('generated_truth_table' if index<600 else
                'generated_effect_default' if index<1200 else
                'scholarly_projection' if index<1230 else 'regression_control')
        raw.append(dict(id=case['id'],family=family,
                        region=';'.join(map(str,cert['region'])),
                        least_state='' if cert['least_counterexample'] is None else cert['least_counterexample']['state'],
                        least_input='' if cert['least_counterexample'] is None else cert['least_counterexample']['input'],
                        **metrics,checker_steps=checked['checker_steps']))
    write_lines(res/'semantic_certificates.jsonl',certs)
    csv_file(res/'semantic_results.csv',raw)
    write_json(res/'observation_sensitivity.json',sensitivity)
    uniform_inputs=list(uniform_problems()); assert len(uniform_inputs)==3102
    write_lines(inp/'uniform_problems.jsonl',uniform_inputs)
    uniform_raw=[]; uniform_certs=[]; un=Counter(); uniform_mutation=Counter()
    for i,problem in enumerate(uniform_inputs):
        cert=solve(problem); checked=uniform_check(problem,cert)
        un['policy_enumerations']+=checked['policy_count']
        un['greatest_exists' if cert['greatest_region'] is not None else 'no_greatest']+=1
        size=0 if cert['obstruction'] is None else len(cert['obstruction']['states'])
        if size:
            assert size<=problem['choices']
            un['obstruction_size_'+str(size)]+=1
            altered=deepcopy(cert); altered['obstruction']['choice_rejections'].pop()
            try: uniform_check(problem,altered)
            except ValueError: uniform_mutation['omitted_choice_rejection']+=1
            else: raise AssertionError('bad uniform conflict accepted')
            altered=deepcopy(cert); altered['obstruction']['deletion_witnesses'][0]['choice']=problem['choices']
            try: uniform_check(problem,altered)
            except ValueError: uniform_mutation['invalid_deletion_choice']+=1
            else: raise AssertionError('bad deletion witness accepted')
        uniform_certs.append(cert)
        uniform_raw.append({'case':i+1,'states':len(problem['blocks']),'choices':problem['choices'],
                            'blocks':max(problem['blocks'])+1,'greatest_exists':int(cert['greatest_region'] is not None),
                            'obstruction_size':size,**checked})
    write_lines(res/'uniform_certificates.jsonl',uniform_certs)
    write_lines(res/'uniform_results.jsonl',uniform_raw)
    composition=[]; composition_summary=Counter()
    functions=[tuple((code>>x)&1 for x in (0,1)) for code in range(4)]
    for f0,f1,g0,g1 in product(functions,repeat=4):
        local_all=(f0==f1 and g0==g1)
        composed=tuple(g1[f1[x]]==g0[f0[x]] for x in (0,1))
        whole=all(composed)
        local_zero=(f0[0]==f1[0] and g0[0]==g1[0])
        assert not local_all or whole
        composition_summary['whole_compatible']+=int(whole)
        composition_summary['local_universal_accepted']+=int(local_all)
        composition_summary['universal_false_reject']+=int(whole and not local_all)
        composition_summary['initial_zero_false_accept']+=int(local_zero and not composed[0])
        composition.append({'f0':f0,'f1':f1,'g0':g0,'g1':g1,'local_universal':local_all,
                            'whole':whole,'local_input_zero':local_zero,'composed_input_zero':composed[0]})
    assert len(composition)==256
    write_lines(res/'composition.jsonl',composition)
    guard=[]; guard_summary=Counter()
    def components(mask,n):
        return sum(bool(mask&(1<<v)) and (v==0 or not(mask&(1<<(v-1)))) for v in range(n))
    for n in range(1,7):
        for safe in range(1<<n):
            for k in (1,2,3):
                candidates=[m for m in range(1<<n) if m & ~safe==0 and components(m,n)<=k]
                greatest=next((m for m in candidates if all(q & ~m==0 for q in candidates)),None)
                theorem=(safe if components(safe,n)<=k else None)
                assert greatest==theorem
                guard_summary['greatest_exists' if greatest is not None else 'no_greatest']+=1
                guard.append({'states':n,'safe_mask':safe,'interval_limit':k,'components':components(safe,n),
                              'greatest_mask':greatest})
    assert len(guard)==378
    write_lines(res/'guard_queries.jsonl',guard)
    summary={'semantic':{'generated_truth_table_cases':600,
                         'generated_effect_default_cases':600,
                         'generated_cases':1200,'scholarly_illustrations':30,
                         'campaign_cases':1230,'regression_controls':16,'total_executed':1246,
                         'oracle_mismatches':0,'mutation_rejections':sum(mutate.values()),
                         'mutation_categories':dict(mutate),'totals':dict(steps),'including_mutations':dict(replay_accounting),'measured_dimensions':dict(maxima)},
             'baselines':dict(base),
             'uniform':{'problems':3102,'oracle_mismatches':0,**dict(un),
                        'mutation_rejections':sum(uniform_mutation.values()),'mutation_categories':dict(uniform_mutation)},
             'composition':{'quadruples':256,**dict(composition_summary)},
             'guards':{'queries':378,'oracle_mismatches':0,**dict(guard_summary)},
             'scope':{'general_mechanized_proofs':0,'scholarly_cases':30,'device_runs':0,
                      'scholarly_case_kind':'bounded hand-authored projections, not source reproductions',
                      'random_sampling':False,'symbolic_execution':False,
                      'all_tiny_histories_claim':False,'workers':1}}
    write_json(res/'summary.json',summary)
    measurement={'wall_seconds':time.monotonic()-begin_wall,'cpu_seconds':time.process_time()-begin_cpu,
                 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 'measurement_scope':'single pilot process; includes mutations, independent oracles and output writing',
                 'workers':1,'child_processes':0,'cpu_limit_seconds':30,'virtual_memory_limit_bytes':768*1024*1024}
    write_json(res/'measurement.json',measurement)
    print(json.dumps({'summary':summary,'measurement':measurement},indent=2,sort_keys=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Root for generated inputs/ and results/')
    options=parser.parse_args()
    run(options.output)

if __name__=='__main__': main()
