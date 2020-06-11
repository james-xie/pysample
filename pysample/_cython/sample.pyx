import sys
from types import FrameType


cdef class PySampleCounter:
    def __cinit__(self, int delta):
        self._counter = SampleCounter_Create(delta)
        if self._counter == NULL:
            raise RuntimeError
        self._sys_path = None

    def __dealloc__(self):
        if self._counter:
            SampleCounter_Free(self._counter)
            self._counter = NULL

    def add_frame(self, frame: FrameType):
        cdef int res

        if not isinstance(frame, FrameType):
            raise TypeError

        res = SampleCounter_AddFrame(self._counter, frame)
        if res == -1:
            raise RuntimeError

    def flame_output(self) -> str:
        if self._sys_path is None or len(sys.path) != self._sys_path:
            self._sys_path = sorted(sys.path, key=len)
        return SampleCounter_FlameOutput(self._counter, self._sys_path)