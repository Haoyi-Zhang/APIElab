"""Failure-path tests for exclusive output ownership."""
import tempfile
import unittest
from pathlib import Path
from compatibility.pilot import run as semantic_run
from compatibility.succinct_campaign import run as succinct_run


class ReproductionFailureTests(unittest.TestCase):
    def _exercise(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fresh=root/'fresh'
            with self.assertRaises(RuntimeError):
                runner(fresh,inject_failure_after_create=True)
            self.assertTrue(fresh.is_dir())
            self.assertEqual(list(fresh.iterdir()),[])

            existing=root/'existing'; existing.mkdir()
            sentinel=existing/'keep.txt'; sentinel.write_text('unchanged',encoding='utf-8')
            with self.assertRaises(FileExistsError):
                runner(existing,inject_failure_after_create=True)
            self.assertEqual(sentinel.read_text(encoding='utf-8'),'unchanged')

    def test_semantic_failure_retains_only_fresh_owned_path(self):
        self._exercise(semantic_run)

    def test_succinct_failure_retains_only_fresh_owned_path(self):
        self._exercise(succinct_run)


if __name__=='__main__':
    unittest.main()
