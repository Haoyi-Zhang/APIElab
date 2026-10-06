"""Actual measurement, serialization, and certificate-decoding regressions."""
import os
import unittest
from pathlib import Path
from tests.fixtures import temporary_directory
from compatibility.measurement import configure_limits, peak_rss_kib
from compatibility.pilot import write_json, write_lines
from compatibility.succinct_check import read_json_line, Rejected


class PortableEvidenceTests(unittest.TestCase):
    def test_json_and_jsonl_have_platform_independent_lf_bytes(self):
        with temporary_directory() as directory:
            path = Path(directory)
            write_json(path/'one.json', {'event': 'a'})
            write_lines(path/'two.jsonl', [{'event': 'a'}, {'event': 'b'}])
            self.assertEqual((path/'one.json').read_bytes(), b'{\n  "event": "a"\n}\n')
            self.assertEqual((path/'two.jsonl').read_bytes(),
                             b'{"event":"a"}\n{"event":"b"}\n')

    def test_current_process_has_a_real_positive_peak(self):
        self.assertGreater(peak_rss_kib(), 0)

    @unittest.skipUnless(os.name == 'nt', 'Windows limit contract')
    def test_windows_does_not_claim_unenforced_posix_limits(self):
        self.assertEqual(configure_limits(30), {
            'cpu_limit_seconds': None, 'virtual_memory_limit_bytes': None,
            'affinity_cpu_count': None})

    def test_jsonl_rejects_duplicate_keys(self):
        with self.assertRaises(Rejected):
            read_json_line('{"id":"good","id":"bad"}')
        with self.assertRaises(Rejected):
            read_json_line('{"nodes":[{"value":0,"value":1}]}')

    def test_jsonl_rejects_nonfinite_and_oversized_records(self):
        for word in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(word=word), self.assertRaises(Rejected):
                read_json_line('{"value":' + word + '}')
        with self.assertRaises(Rejected):
            read_json_line('{"id":"abc"}', byte_limit=5)
        self.assertEqual(read_json_line('{"id":"abc"}'), {'id': 'abc'})


if __name__ == '__main__':
    unittest.main()
