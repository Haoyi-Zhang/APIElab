"""Retain owned test fixtures when requested by the finite campaign driver."""
from contextlib import contextmanager
import os
import tempfile


@contextmanager
def temporary_directory():
    if os.environ.get('APIELAB_RETAIN_TEST_OUTPUTS') == '1':
        yield tempfile.mkdtemp(prefix='apielab-', dir=os.environ['APIELAB_TEST_TMP'])
    else:
        with tempfile.TemporaryDirectory() as directory:
            yield directory
