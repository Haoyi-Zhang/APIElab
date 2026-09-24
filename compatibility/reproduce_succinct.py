"""Regenerate all 6,280 bounded reduction instances and recheck their structure.

Only fresh output directories are accepted. Timings are measured, not compared.
No network, subprocess, proof assistant, or external solver is used.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import resource
import time
from .succinct_campaign import run
from .structure_check import run as structure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); target=args.output.resolve()
    root=Path(__file__).resolve().parent.parent
    if target.exists():
        parser.exit(2,'Choose a fresh output directory.\n')
    start=time.process_time(); wall=time.monotonic()
    run(target)
    rows=structure(target)
    with (target/'structure.jsonl').open('x',encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    names=('cases.jsonl','circuits.jsonl','certificates.jsonl','per_case.csv',
           'summary.json','negative_controls.json','structure.jsonl')
    for name in names:
        if (target/name).read_bytes() != (root/'results'/'succinct'/name).read_bytes():
            parser.exit(2,f'Exact reproduction mismatch: {name}\n')
    report={'deterministic_files_compared':list(names),'exact_matches':len(names),
            'structure_cases':len(rows),'measurement_values_compared':False,
            'general_proof_claim':False}
    (target/'reproduction_check.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    measured={'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,
              'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'workers':1,'child_processes':0,
              'scope':'full regeneration, mutations, structure replay and exact comparison'}
    (target/'reproduction_measurement.json').write_text(json.dumps(measured,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'reproduction':report,'measurement':measured},indent=2,sort_keys=True))

if __name__=='__main__':main()
