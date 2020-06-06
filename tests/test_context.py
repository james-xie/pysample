import inspect
import unittest
from types import FrameType
from typing import List

from pysample.context import SampleContext


class TestContext(unittest.TestCase):
    def _frame1(self, ctx: SampleContext, tb_array: List[str]):
        def _inner():
            frame = inspect.currentframe().f_back
            ctx.collect(frame)
            ctx.collect(frame)
            ctx.collect(frame)
            tb_array.append(self._serialize_frame(frame))

        _inner()

    def _frame2(self, ctx: SampleContext, tb_array: List[str]):
        def _inner():
            frame = inspect.currentframe().f_back
            ctx.collect(frame)
            ctx.collect(frame)
            tb_array.append(self._serialize_frame(frame))

        _inner()

    def _serialize_frame(self, frame: FrameType) -> str:
        f_items = []
        while frame is not None:
            item = (
                frame.f_code.co_name,
                frame.f_lineno,
                frame.f_globals.get("__name__"),
            )
            f_items.append(item)
            frame = frame.f_back
        return ";".join("%s:%s (%s)" % _ for _ in f_items[::-1])

    def assert_output_equal(self, expect: str, target: str):
        exp_output = set(expect.splitlines())
        tar_output = set(target.splitlines())
        self.assertEqual(exp_output, tar_output)

    def test_collect_and_output(self):
        tb_array = []
        ctx = SampleContext("test", 10)
        self._frame1(ctx, tb_array)
        self._frame2(ctx, tb_array)

        output = ctx.flame_output()
        expect_output = f"{tb_array[0]}; 30\n{tb_array[1]}; 20\n"
        self.assert_output_equal(expect_output, output)

    def test_empty_output(self):
        ctx = SampleContext("test", 10)
        output = ctx.flame_output()
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main(defaultTest="TestContext.test_collect_and_output")