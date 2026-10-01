"""Lightweight CLI-entrypoint checks, separate from in-process runner tests."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class CliEntrypointTests(unittest.TestCase):
    def test_public_module_entrypoints_expose_help(self):
        root=Path(__file__).resolve().parent.parent
        env=dict(os.environ)
        env['PYTHONPATH']=str(root)
        for module in ('compatibility.reproduce','compatibility.reproduce_succinct'):
            completed=subprocess.run(
                [sys.executable,'-m',module,'--help'],
                cwd=root,env=env,text=True,capture_output=True,timeout=15,check=False)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertIn('--output',completed.stdout)


if __name__=='__main__':
    unittest.main()
