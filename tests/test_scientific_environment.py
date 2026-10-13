from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from compatibility.scientific_checks import commands, hardware_metadata


class ScientificEnvironmentTests(unittest.TestCase):
    def test_linux_metadata_comes_from_current_source(self):
        with patch('compatibility.scientific_checks.sys.platform', 'linux'), \
             patch('compatibility.scientific_checks.os.cpu_count', return_value=4), \
             patch('compatibility.scientific_checks.Path.read_text', return_value=
                   'model name: Test CPU\nmodel name: Test CPU\n'):
            value = hardware_metadata()
            self.assertEqual(value['models'], ['Test CPU'])
            self.assertEqual(value['logical_processors'], 4)
            self.assertIsNone(value['physical_cores'])

    def test_unavailable_metadata_stays_unknown(self):
        with patch('compatibility.scientific_checks.sys.platform', 'linux'), \
             patch('compatibility.scientific_checks.Path.read_text', side_effect=OSError), \
             patch('compatibility.scientific_checks.os.sched_getaffinity', create=True,
                   side_effect=OSError):
            value = hardware_metadata()
            self.assertEqual(value['models'], [])
            self.assertIsNone(value['source'])
            self.assertIsNone(value['available_affinity_processors'])

    def test_windows_registry_value_is_not_guessed(self):
        for name, expected in [(' Test CPU ', ['Test CPU']), (True, [])]:
            registry = SimpleNamespace(HKEY_LOCAL_MACHINE=object(),
                                       OpenKey=lambda *_: nullcontext(object()),
                                       QueryValueEx=lambda *_: (name, 1))
            with self.subTest(name=name), \
                 patch('compatibility.scientific_checks.sys.platform', 'win32'), \
                 patch.dict('sys.modules', {'winreg': registry}):
                self.assertEqual(hardware_metadata()['models'], expected)

    def test_group_controls_are_a_separate_owned_command(self):
        entries = commands(Path('output'))
        self.assertEqual(len(entries), 8)
        self.assertEqual(len({name for name, _ in entries}), 8)
        self.assertEqual(entries[-1], ('group-quantifiers',
                         ['-m', 'compatibility.group_controls', '--output',
                          str(Path('output/group-encoding'))]))


if __name__ == '__main__':
    unittest.main()
