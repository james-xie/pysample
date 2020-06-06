import os
import time
import shutil
import unittest
import datetime
from concurrent.futures import ThreadPoolExecutor

from pysample.repository import DirectoryRepository, FileRepository
from pysample.sampler import sample
from pysample.timer import timer_started, stop_timer


class TestSamplerWithFileRepository(unittest.TestCase):

    def tearDown(self) -> None:
        if timer_started():
            stop_timer()

    def _clean_output_path(self, path: str):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def test_sample(self):
        path = "/tmp/pysample_test_output/foo.txt"

        @sample(100, 0, path)
        def foo():
            time.sleep(0.11)
            time.sleep(0.21)
            time.sleep(0.31)

        foo()
        with open(path, 'r') as file:
            content = file.read()
            lines = content.splitlines()
            self.assertEqual(len(lines), 3)

        with self.assertRaises(RuntimeError):
            FileRepository(path, False)

        self._clean_output_path(path)

    def test_for_multi_function(self):
        def foo():
            time.sleep(0.11)

        def foo1():
            time.sleep(0.11)
            time.sleep(0.11)

        test_args = [
            ("/tmp/pysample_test_output/foo.txt", foo, 1),
            ("/tmp/pysample_test_output/foo1.txt", foo1, 2),
        ]
        for arg_tuple in test_args:
            path, func, count = arg_tuple
            func_deco = sample(100, 0, path)(func)
            func_deco()
            with open(path, 'r') as file:
                content = file.read()
                lines = content.splitlines()
                self.assertEqual(len(lines), count)

            self._clean_output_path(path)

    def test_for_nested_function(self):
        path1 = "/tmp/pysample_test_output/foo.txt"
        path2 = "/tmp/pysample_test_output/foo1.txt"

        @sample(100, 0, path1)
        def foo():
            time.sleep(0.11)

            @sample(100, 0, path2)
            def foo1():
                time.sleep(0.11)

            foo1()
            time.sleep(0.11)

        foo()

        with open(path1, 'r') as file:
            content = file.read()
            lines = content.splitlines()
            self.assertEqual(len(lines), 3)

        with open(path2, 'r') as file:
            content = file.read()
            lines = content.splitlines()
            self.assertEqual(len(lines), 1)

        self._clean_output_path(path1)
        self._clean_output_path(path2)

    def test_for_multi_threads(self):
        path_template = "/tmp/pysample_test_output/foo_%s.txt"

        def foo():
            time.sleep(0.11)
            time.sleep(0.31)

        def foo1():
            time.sleep(0.11)

        test_funcs = [
            foo,
            foo1,
            foo1,
            foo1,
            foo,
            foo1,
            foo,
            foo1,
            foo,
            foo,
            foo,
        ]

        with ThreadPoolExecutor(max_workers=5) as executor:
            for index, func in enumerate(test_funcs):
                path = path_template % index
                func_deco = sample(100, 0, path)(func)
                executor.submit(func_deco)

        for index, func in enumerate(test_funcs):
            if func == foo:
                count = 2
            else:
                count = 1
            path = path_template % index
            with open(path, 'r') as file:
                content = file.read()
                lines = content.splitlines()
                self.assertEqual(len(lines), count)

            self._clean_output_path(path)


class TestSamplerWithDirectoryRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._output_dir = "/tmp/pysample_test_output1"
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
        output_repo = DirectoryRepository(self._output_dir)

        @sample(100, 0, output_repo=output_repo)
        def foo():
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

    def test_sample_with_output_threshold(self):
        now = datetime.datetime.now()
        output_repo = DirectoryRepository(self._output_dir)

        @sample(10, 500, output_repo=output_repo)
        def foo():
            time.sleep(0.11)

        foo()
        today = now.strftime("%Y-%m-%d")
        subdir = f"{self._output_dir}/{today}"
        self.assertTrue(os.path.exists(subdir))
        self.assertEqual(len(os.listdir(subdir)), 0)

