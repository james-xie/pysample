import sys
import time
import threading

from pysample.context import SampleContext, SampleContextFactory, SampleContextManager


class SampleTimer:
    """
    Sample event triggered by "SampleTimer".

    Only one SampleTimer is running at the same time. Usually use the "start_timer"
    function to start a "SampleTimer" instead of calling "SamplerTimer().start()" directly.
    """

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class ThreadSampleContext(SampleContext):
    def __init__(self, name: str, delta: int, thread_id: int):
        super().__init__(name, delta)

        self._thread_id = thread_id

    @property
    def thread_id(self):
        return self._thread_id


class ThreadContextFactory(SampleContextFactory):
    def create(self, name: str, delta: int) -> SampleContext:
        t_ident = threading.current_thread().ident
        return ThreadSampleContext(name, delta, t_ident)


class ThreadSampleTimer(SampleTimer):
    """
    Start a new thread, which is used to periodically trigger sampling event.
    """
    def __init__(self, interval: int, context_manager: SampleContextManager[ThreadSampleContext]):
        """
        :param interval:
            Sampling interval (in milliseconds)
        :param context_manager:
        """
        if interval < 5:
            raise ValueError("Interval must be greater than 5")

        self._thread = None
        self._active = False
        self._interval = interval
        self._interval_ms = interval / 1000
        self._context_manager = context_manager
        self._current_thread = threading.current_thread()

    def start(self):
        assert not self._active
        self._active = True
        self._thread = threading.Thread(target=self._do_sample, name="PySample.ThreadSampleTimer")
        self._thread.setDaemon(True)
        self._thread.start()

    def stop(self, timeout=3):
        assert self._active
        self._active = False
        self._thread.join(timeout)
        self._thread = None

    def _do_sample(self):
        while self._active:
            start = time.time()

            for context in self._context_manager.iterator():
                ident = context.thread_id
                frame = sys._current_frames().get(ident)
                context.collect(frame)

            end = time.time()
            elapsed_time = end - start
            time.sleep(self._interval_ms - elapsed_time)


_timer = None
_lock = threading.Lock()


def start_timer(timer: SampleTimer):
    """
    Start the given timer and save the "timer" reference to the global variable "_timer".
    If the timer has started, it will be return immediately

    :param timer:
    :return:
    """
    global _timer

    if _timer:
        return

    with _lock:
        if _timer is None:
            _timer = timer
            timer.start()


def timer_started():
    return bool(_timer)


def stop_timer():
    global _timer

    assert _timer is not None
    _timer.stop()
    _timer = None

