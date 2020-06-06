import logging
import functools
from types import FunctionType

from pysample.repository import OutputRepository, FileRepository, DirectoryRepository
from pysample.context import SampleContext, SampleContextFactory, SampleContextManager
from pysample.timer import (
    ThreadSampleTimer,
    ThreadContextFactory,
    start_timer,
    timer_started,
)


logger = logging.getLogger(__name__)


class Sampler:
    """
    A decorator class for performance analysis.
    It collect the runtime stack frame of python interpreter, and generate some stacks information
    for analysis. The output stack information will be used as the input of the flame graph.

    Commonly used "sample" function instead of using this class directly.
    """

    def __init__(
        self,
        *,
        interval: int,
        output_threshold: int,
        context_manager: SampleContextManager,
        context_factory: SampleContextFactory,
        output_repo: OutputRepository,
    ):
        """
        :param interval:
            Sampling interval (in milliseconds)
        :param output_threshold:
            Output threshold (in milliseconds)
            If the elapsed time of the function execution is greater than output_threshold,
            it stores the stack information to the "output_repo"
        :param context_manager:
            Track all sample contexts in the context manager.
        :param context_factory:
            Create a sample context using the context factory.
        :param output_repo:
            Store the stack information to the output repository.
        """
        self._interval = interval
        self._output_threshold = output_threshold
        self._context_manager = context_manager
        self._context_factory = context_factory
        self._output_repo = output_repo

    def begin(self, name: str) -> SampleContext:
        ctx = self._context_factory.create(name, self._interval)
        self._context_manager.push(ctx)
        return ctx

    def end(self, ctx: SampleContext):
        self._context_manager.pop(ctx)
        if ctx.lifecycle >= self._output_threshold:
            self._output_repo.store(ctx)

    def __call__(self, func: FunctionType):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            fn_name = f"{func.__module__}.{func.__qualname__}"
            ctx = self.begin(fn_name)
            try:
                res = func(*args, **kwargs)
            finally:
                self.end(ctx)
            return res

        return inner


def sample(
    interval: int,
    output_threshold: int,
    output_path: str = None,
    output_repo: OutputRepository = None,
    auto_start_timer: bool = True,
):
    """
    A decorator function which simplify the use of "sampler" class.

    Usage:
        @sample(10, 100, "/tmp/pysample/foo.txt")
        def foo():
            pass

        Sample the "foo" function every 10 milliseconds, if the function execution time
        is greater than 100ms, it will store the stacks information to the given output path.

    :param interval:
        Sampling interval (in milliseconds)
        The minimum interval value is 5. By default, the GIL will be released after
        5 milliseconds, so that other threads can have a chance to acquire the GIL.
    :param output_threshold:
        Output threshold (in milliseconds)
    :param output_path:
        Store the sampling result to the output path
    :param auto_start_timer:
        Start timer before sampling
    :param output_repo:
        If the "output_repo" argument is specified, the "output_path" argument will be discarded.
    :return:
    """
    if interval < 5:
        interval = 5

    context_manager = SampleContextManager.get_default_instance()
    context_factory = ThreadContextFactory()
    if output_repo is None:
        output_repo = FileRepository(output_path)

    if auto_start_timer and not timer_started():
        start_timer(ThreadSampleTimer(interval, context_manager))

    sampler = Sampler(
        interval=interval,
        output_threshold=output_threshold,
        context_manager=context_manager,
        context_factory=context_factory,
        output_repo=output_repo,
    )
    return sampler
