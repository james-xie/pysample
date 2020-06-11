import time
import logging
import threading

from typing import Iterator, Generic, TypeVar

from types import FrameType
from collections import deque

from pysample._cython.sample import PySampleCounter


logger = logging.getLogger(__name__)


class SampleContext:
    def __init__(self, name: str, delta: int):
        self._name = name
        self._delta = 0
        self._total_count = 0
        self._start_time = time.time()
        self._counter = PySampleCounter(delta)

    def collect(self, frame: FrameType):
        self._counter.add_frame(frame)
        self._total_count += self._delta

    def flame_output(self) -> str:
        return self._counter.flame_output()

    @property
    def name(self) -> str:
        return self._name

    @property
    def lifecycle(self) -> int:
        return int((time.time() - self._start_time) * 1000)

    @property
    def total_count(self) -> int:
        return self._total_count


class SampleContextFactory:
    def create(self, name: str, delta: int) -> SampleContext:
        return SampleContext(name, delta)


CtxType = TypeVar("CtxType", bound=SampleContext)


class SampleContextManager(Generic[CtxType]):

    def __init__(self, capacity: int = 1000):
        self._capacity = capacity
        self._active_context = deque()
        self._lock = threading.Lock()

    def push(self, ctx: CtxType):
        with self._lock:
            if len(self._active_context) >= self._capacity:
                logger.warning(f'"SampleContext" exceeds the maximum capacity ({self._capacity}) limit')
                return

            self._active_context.append(ctx)

    def pop(self, ctx: CtxType):
        try:
            self._active_context.remove(ctx)
        except IndexError:
            pass

    def iterator(self) -> Iterator[CtxType]:
        return iter(self._active_context)

    _instance = None
    _get_instance_lock = threading.Lock()

    @classmethod
    def get_default_instance(cls) -> "SampleContextManager":
        if cls._instance:
            return cls._instance

        with cls._get_instance_lock:
            if cls._instance is None:
                cls._instance = SampleContextManager()
        return cls._instance
