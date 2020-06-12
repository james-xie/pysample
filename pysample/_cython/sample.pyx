import sys
from types import FrameType


cdef class PySampleCounter:
    def __cinit__(self, int delta):

        self._counter = SampleCounter_Create(
            delta, sorted(sys.path, key=len, reverse=True)
        )
        if self._counter == NULL:
            raise RuntimeError

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
        return SampleCounter_FlameOutput(self._counter)