"""Reproduce retained deterministic results and verify byte-for-byte input identity.

No hashes or toolchain manifests are created. Machine-dependent timings are not
expected to match. Comparison is exact JSON/text comparison, not a correctness
proof. The pilot's independent oracles provide the separate finite checks.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .pilot import run, write_json
from .model import load_json
from .infer import infer
from .replay import read_json, check


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    target=args.output.resolve()
    # Avoid destroying retained evidence; users must choose a fresh directory.
    if target == root or target in (root/'inputs',root/'results') or target.exists():
        parser.exit(2,'Choose a fresh output directory outside retained inputs/results.\n')
    run(target)
    checked=[]
    for folder in ('inputs','results'):
        for saved in sorted((root/folder).iterdir()):
            if saved.name=='measurement.json' or not saved.is_file():
                continue
            fresh=target/folder/saved.name
            # Only files emitted by the finite pilot are compared here.
            if not fresh.exists():
                continue
            if saved.read_bytes()!=fresh.read_bytes():
                parser.exit(2,f'Reproduction mismatch: {folder}/{saved.name}\n')
            checked.append(f'{folder}/{saved.name}')
    required={'inputs/semantic_cases.jsonl','inputs/control_expectations.json',
              'inputs/scholarly_expectations.json','inputs/scholarly_case_sources.json',
              'inputs/uniform_problems.jsonl',
              'results/semantic_certificates.jsonl','results/semantic_results.csv','results/summary.json',
              'results/uniform_certificates.jsonl','results/uniform_results.jsonl','results/composition.jsonl',
              'results/guard_queries.jsonl','results/observation_sensitivity.json',
              'results/partition_refinement.jsonl'}
    if set(checked)!=required:
        parser.exit(2,'Incomplete deterministic comparison.\n')
    # Authored example and boundary fixtures are retained inputs, not drawn
    # from the 1,230-case campaign and 16-control family. Replay with both independently parsed inputs.
    fixtures=[]
    for name in ('example','boundary'):
        case_path=root/'inputs'/(name+'.json' if name=='example' else 'boundary_case.json')
        cert_path=root/'results'/(name+'_certificate.json')
        fresh_cert,producer_counts=infer(load_json(case_path))
        checker_counts=check(read_json(case_path),read_json(cert_path))
        canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
        if canonical(fresh_cert)!=canonical(read_json(cert_path)):
            parser.exit(2,f'Fixture certificate mismatch: {name}\n')
        if name=='boundary':
            counts={'producer':producer_counts,'checker':checker_counts}
            if canonical(counts)!=canonical(read_json(root/'results'/'boundary_counts.json')):
                parser.exit(2,'Boundary count mismatch.\n')
        write_json(target/'fixtures'/(name+'_certificate.json'),fresh_cert)
        fixtures.append(name)
    report={'deterministic_files_compared':checked,'exact_matches':len(checked),
            'fixtures_reexecuted':fixtures,'boundary_counts_exact':True,
            'measurement_values_compared':False,'general_proof_claim':False}
    write_json(target/'reproduction_check.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
