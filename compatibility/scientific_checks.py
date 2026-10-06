"""Bounded complete local campaign, retained fixtures and raw command logs.

No network, downloads, installs, shell, or deletion. Each of seven owned child
commands has a 180-second wall timeout. Individual scientific campaigns keep
their own measured CPU/RSS records; this driver reports command wall time only.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


def commands(output):
    return [
        ('unit-tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-v']),
        ('semantic', ['-m', 'compatibility.reproduce', '--output', str(output/'semantic')]),
        ('succinct', ['-m', 'compatibility.reproduce_succinct', '--output', str(output/'succinct')]),
        ('example-check', ['-m', 'compatibility.cli', 'check',
                           'inputs/example.json', 'results/example_certificate.json']),
        ('boundary-check', ['-m', 'compatibility.cli', 'check',
                            'inputs/boundary_case.json', 'results/boundary_certificate.json']),
        ('example-infer', ['-m', 'compatibility.cli', 'infer',
                           'inputs/example.json', str(output/'example_certificate.json')]),
        ('example-fresh-check', ['-m', 'compatibility.cli', 'check',
                                 'inputs/example.json', str(output/'example_certificate.json')]),
    ]


def run(output):
    if not __debug__:
        raise RuntimeError('Run without Python -O/-OO.')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    logs = output/'logs'; logs.mkdir()
    test_tmp = output/'test-fixtures'; test_tmp.mkdir()
    root = Path(__file__).resolve().parent.parent
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(root), APIELAB_RETAIN_TEST_OUTPUTS='1',
               APIELAB_TEST_TMP=str(test_tmp), TMP=str(test_tmp), TEMP=str(test_tmp))
    report = {'python': sys.version, 'python_executable': sys.executable,
              'platform': platform.platform(), 'machine': platform.machine(),
              'command_timeout_seconds': 180, 'maximum_child_commands': 7,
              'test_fixtures_retained': True, 'commands': [], 'complete': False}
    def save():
        (output/'campaign.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n',
                                           encoding='utf-8', newline='\n')
    save()
    for name, args in commands(output):
        command = [sys.executable, '-B', *args]
        start = time.monotonic()
        try:
            result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                    timeout=180, check=False)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, code = exc.stdout or b'', exc.stderr or b'', None
            timed_out = True
        (logs/(name+'.stdout.txt')).write_bytes(stdout)
        (logs/(name+'.stderr.txt')).write_bytes(stderr)
        record = {'name': name, 'command': command, 'returncode': code,
                  'timed_out': timed_out, 'wall_seconds': time.monotonic()-start}
        if name == 'unit-tests':
            match = re.search(rb'Ran (\d+) tests? in', stderr)
            record['tests_run'] = int(match.group(1)) if match else None
        report['commands'].append(record)
        save()
        print(f'{name}: returncode={code}, wall={record["wall_seconds"]:.3f}s', flush=True)
        if code != 0 or timed_out:
            raise RuntimeError(f'{name} failed; raw logs and owned outputs retained at {output}')
    report['complete'] = True
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
