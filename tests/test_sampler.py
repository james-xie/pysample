import os
import shutil
import unittest
import datetime

from pysample.sampler import sample
from pysample.timer import timer_started, stop_timer


class TestSampler(unittest.TestCase):
    def setUp(self) -> None:
        self._output_dir = "/tmp/pysample_test_output"
        self.assertFalse(
            os.path.exists(self._output_dir),
            f"The directory '{self._output_dir}' already exists, the test case cannot be run",
        )

    def tearDown(self) -> None:
        self._clean_dir(self._output_dir)
        if timer_started():
            stop_timer()

    def _clean_dir(self, path: str):
        shutil.rmtree(path, ignore_errors=False, onerror=None)

    def test_sample(self):
        now = datetime.datetime.now()

        @sample(100, 0, self._output_dir)
        def foo():
            import time

            time.sleep(0.11)
            time.sleep(0.21)
            time.sleep(0.31)

        foo()
        today = now.strftime("%Y-%m-%d")
        subdir = f"{self._output_dir}/{today}"
        self.assertTrue(os.path.exists(subdir))
        self.assertEqual(len(os.listdir(subdir)), 1)

        filename = os.listdir(subdir)[0]
        foo_name = f"{foo.__module__}.{foo.__qualname__}"
        self.assertTrue(filename.startswith(foo_name))

        with open(f"{subdir}/{filename}", 'r') as file:
            content = file.read()
            lines = content.splitlines()
            self.assertEqual(len(lines), 3)