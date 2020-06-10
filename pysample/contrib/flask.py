import logging
from typing import Optional

from pysample.client import Client
from pysample.context import SampleContext
from pysample.repository import OutputRepository
from pysample.sampler import sample, Sampler
from pysample.transport import ThreadTransport
from flask import Flask, g, request


CONTEXT_FIELD_NAME = '__pysample_context'
logger = logging.getLogger("pysample.flask")


class RemoteRepository(OutputRepository):
    def __init__(self, client: Client):
        self._client = client

    def store(self, sample_context: SampleContext):
        data = self._client.build_data(
            name=sample_context.name,
            stack_info=sample_context.flame_output(),
            execution_time=sample_context.lifecycle,
        )
        self._client.capture(data)


class FlaskSample(object):
    def __init__(
        self,
        url: Optional[str] = None,
        client: Optional[Client] = None,
        interval: int = 10,
        output_threshold: int = 0,
    ):
        if client is None:
            if url is None:
                raise ValueError("Either url or client is required")
            client = self._make_client(url)
        self._client = client
        self._interval = interval
        self._output_threshold = output_threshold
        self._sampler: Optional[Sampler] = None

    def _default_transport(self):
        return ThreadTransport()

    def _make_client(self, url: str) -> Client:
        return Client(url, self._default_transport())

    def init_app(self, app: Flask):
        self._sampler = sample(self._interval, self._output_threshold)

        app.before_request(self.before_request)
        app.teardown_request(self.teardown_request)

    def before_request(self):
        name = request.path
        ctx = self._sampler.begin(name)
        setattr(g, CONTEXT_FIELD_NAME, ctx)

    def teardown_request(self):
        ctx = getattr(g, CONTEXT_FIELD_NAME, None)
        if ctx:
            self._sampler.end(ctx)
        else:
            logger.error("Cannot get sample context from flask.g in teardown request")
