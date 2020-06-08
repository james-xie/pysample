import gc
import sys
import inspect
import unittest

from pysample.context import SampleContext


class TestMemoryLeak(unittest.TestCase):

    def _sample(self):
        ctx = SampleContext("test", 10)
        frame = inspect.currentframe()
        ctx.collect(frame)
        ctx.collect(frame)
        ctx.collect(frame)
        return ctx.flame_output()

    def test_with_valgrind(self):
        """
        Run this method using valgrind and a python interpreter build with --with-pydebug.

        The command is as follows:
            valgrind --tool=memcheck --dsymutil=yes --track-origins=yes --show-leak-kinds=definite
            --trace-children=yes --leak-check=full {python interpreter path} -X showrefcount test_for_valgrind.py

        :return:
        """
        self._sample()

    def test_python_refcount_leak(self):
        """
        Run this method using a python interpreter build with --with-pydebug.

        :return:
        """

        def run_test() -> int:
            gc.collect()
            refcount1 = sys.gettotalrefcount()

            self._sample()

            gc.collect()
            refcount2 = sys.gettotalrefcount()
            return refcount2 - refcount1

        # Run the same program four times, the reference count should only be
        # changed for the first time.
        refcount_diff = run_test()

        for _ in range(0, 3):
            self.assertTrue(refcount_diff, 0)


if __name__ == "__main__":
    unittest.main(defaultTest="TestMemoryLeak.test_python_refcount_leak")
