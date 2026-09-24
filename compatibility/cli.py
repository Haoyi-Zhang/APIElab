"""Infer or independently check one finite semantic certificate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .model import load_json, InvalidCase, BoundExceeded
from .infer import infer
from .replay import read_json, check, Rejected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    make=sub.add_parser('infer',help='produce an exhaustive finite certificate')
    make.add_argument('case',type=Path); make.add_argument('certificate',type=Path)
    verify=sub.add_parser('check',help='replay against trusted input semantics')
    verify.add_argument('case',type=Path); verify.add_argument('certificate',type=Path)
    args=parser.parse_args()
    try:
        if args.action=='infer':
            cert,counts=infer(load_json(args.case))
            # Never silently overwrite an existing scientific result.
            with args.certificate.open('x',encoding='utf-8') as f:
                json.dump(cert,f,sort_keys=True,indent=2,allow_nan=False); f.write('\n')
            print(json.dumps({'accepted_input':True,'counts':counts},sort_keys=True))
        else:
            counts=check(read_json(args.case),read_json(args.certificate))
            print(json.dumps({'certificate_accepted':True,'counts':counts},sort_keys=True))
    except (OSError, InvalidCase, BoundExceeded, Rejected) as exc:
        parser.exit(2, f'No compatibility conclusion: {exc}\n')

if __name__=='__main__': main()
