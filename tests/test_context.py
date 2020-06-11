import os
import sys
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

    def _shorten_filename(self, filename: str) -> str:
        for path in sorted(sys.path, key=len):
            path_len = len(path)
            if filename.startswith(path):
                if len(filename) > path_len and filename[path_len] == os.path.sep:
                    return filename[path_len+1:]
                return filename[path_len:]
        return filename

    def _serialize_frame(self, frame: FrameType) -> str:
        f_items = []

        while frame is not None:
            item = (
                frame.f_code.co_name,
                self._shorten_filename(frame.f_code.co_filename),
                frame.f_lineno,
            )
            f_items.append(item)
            frame = frame.f_back
        return ";".join("%s (%s:%s)" % _ for _ in f_items[::-1])

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

    def test_perf(self):
        ctx = SampleContext("", 1)

        def test0():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test0()


        def test1():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test1()


        def test2():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test2()


        def test3():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test3()


        def test4():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test4()


        def test5():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test5()


        def test6():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test6()


        def test7():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test7()


        def test8():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test8()


        def test9():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test9()


        def test10():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test10()


        def test11():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test11()


        def test12():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test12()


        def test13():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test13()


        def test14():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test14()


        def test15():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test15()


        def test16():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test16()


        def test17():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test17()


        def test18():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test18()


        def test19():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test19()


        def test20():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test20()


        def test21():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test21()


        def test22():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test22()


        def test23():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test23()


        def test24():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test24()


        def test25():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test25()


        def test26():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test26()


        def test27():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test27()


        def test28():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test28()


        def test29():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test29()


        def test30():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test30()


        def test31():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test31()


        def test32():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test32()


        def test33():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test33()


        def test34():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test34()


        def test35():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test35()


        def test36():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test36()


        def test37():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test37()


        def test38():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test38()


        def test39():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test39()


        def test40():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test40()


        def test41():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test41()


        def test42():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test42()


        def test43():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test43()


        def test44():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test44()


        def test45():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test45()


        def test46():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test46()


        def test47():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test47()


        def test48():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test48()


        def test49():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test49()


        def test50():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test50()


        def test51():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test51()


        def test52():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test52()


        def test53():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test53()


        def test54():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test54()


        def test55():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test55()


        def test56():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test56()


        def test57():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test57()


        def test58():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test58()


        def test59():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test59()


        def test60():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test60()


        def test61():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test61()


        def test62():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test62()


        def test63():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test63()


        def test64():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test64()


        def test65():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test65()


        def test66():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test66()


        def test67():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test67()


        def test68():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test68()


        def test69():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test69()


        def test70():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test70()


        def test71():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test71()


        def test72():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test72()


        def test73():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test73()


        def test74():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test74()


        def test75():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test75()


        def test76():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test76()


        def test77():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test77()


        def test78():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test78()


        def test79():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test79()


        def test80():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test80()


        def test81():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test81()


        def test82():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test82()


        def test83():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test83()


        def test84():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test84()


        def test85():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test85()


        def test86():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test86()


        def test87():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test87()


        def test88():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test88()


        def test89():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test89()


        def test90():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test90()


        def test91():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test91()


        def test92():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test92()


        def test93():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test93()


        def test94():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test94()


        def test95():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test95()


        def test96():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test96()


        def test97():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test97()


        def test98():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test98()


        def test99():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test99()

        def test100():
            frame = inspect.currentframe()
            ctx.collect(frame)
        test100()

        import time

        s = time.time()
        for _ in range(0, 1000):
            ctx.flame_output()
        e = time.time()
        print("interval: ", round(e - s, 2))

        with open('/tmp/test.txt', 'w') as file:
            file.write(ctx.flame_output())


if __name__ == "__main__":
    unittest.main(defaultTest="TestContext.test_collect_and_output")