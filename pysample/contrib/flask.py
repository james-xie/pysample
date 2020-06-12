import logging
from typing import Optional

from pysample.client import Client
from pysample.context import SampleContext
from pysample.repository import OutputRepository
from pysample.sampler import sample, Sampler
from pysample.transport import ThreadTransport
from flask import Flask, g, request, Response

CONTEXT_FIELD_NAME = "__pysample_context"
logger = logging.getLogger("pysample.flask")


class RemoteRepository(OutputRepository):
    def __init__(self, client: Client):
        self._client = client

    def store(self, sample_context: SampleContext):
        data = self._client.build_data(
            name=sample_context.name,
            sample_id=sample_context.ident,
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
        transport = self._default_transport()
        transport.start()
        return Client(url, transport)

    def init_app(self, app: Flask):
        repo = RemoteRepository(self._client)
        self._sampler = sample(self._interval, self._output_threshold, output_repo=repo)

        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_request(self.teardown_request)

    def before_request(self):
        name = request.path
        ctx = self._sampler.begin(name)
        setattr(g, CONTEXT_FIELD_NAME, ctx)

    def after_request(self, response: Response) -> Response:
        ctx = getattr(g, CONTEXT_FIELD_NAME, None)
        if ctx:
            self._sampler.end(ctx)
            delattr(g, CONTEXT_FIELD_NAME)

            response.headers["X-PySample-ID"] = f"{self._client.project}/{ctx.ident}"
        else:
            logger.error("Cannot get sample context from flask.g in teardown request")
        return response

    def teardown_request(self, err):
        del err
        ctx = getattr(g, CONTEXT_FIELD_NAME, None)
        if ctx:
            self._sampler.end(ctx)
            delattr(g, CONTEXT_FIELD_NAME)
