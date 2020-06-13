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
    """
    Store the sampling results to the remote server.
    """

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
    """
    Integrate PySample with Flask.

    The FlaskSample object registers hook functions such as
    before_request/after_request/teardown_request to the Flask application,
    and it starts two thread to handle sampling timer and remote data transmission
    separately. Once the "init_app" function is called, the two threads will start
    automatically.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        client: Optional[Client] = None,
        interval: int = 10,
        output_threshold: int = 100,
    ):
        """
        :param url:
            Remote server url and project name.
            for example:
                 http://127.0.0.1:10002/{project_name}

            The project name is required.
        :param client:
            Commonly the client object is automatically created with the given url.
            If the client object is specified, the "url" argument will be ignored.
        :param interval:
            Sampling interval (in milliseconds)
        :param output_threshold:
            Output threshold (in milliseconds)
            If the response time is less than "output_threshold", the sampling
            result will be discarded.
        """
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
