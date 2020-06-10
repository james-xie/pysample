import os
import re
import uuid
import zlib
import json
import time
import threading
from typing import Dict, Any, Tuple
from urllib.parse import urlparse

from pysample.transport import Transport


class Client(object):
    def __init__(self, url: str, transport: Transport):
        self._url, self._project = self.parse_url(url)
        self._transport = transport
        self._add_url = f"{self._url}/{self._project}/sample/add"

    @classmethod
    def parse_url(cls, url: str) -> Tuple[str, str]:
        ret = urlparse(url)
        if ret.scheme not in ["http", "https"]:
            raise ValueError(f"invalid scheme '{ret.scheme}'")
        if not ret.netloc:
            raise ValueError(f"invalid netloc '{ret.netloc}'")

        path = ret.path
        if not path or path == "/":
            raise ValueError(f"can't get project name from path")

        path_prefix, project = path.rsplit("/", 1)
        if not re.match(r"^[\w-]+$", project):
            raise ValueError(
                f"invalid project name, only [a-zA-Z0-9_-] characters are allowed"
            )

        if not path_prefix:
            url = f"{ret.scheme}://{ret.netloc}"
        else:
            url = f"{ret.scheme}://{ret.netloc}/{path_prefix}"
        return url, project

    def _encode(self, data: Dict[str, Any]) -> bytes:
        return zlib.compress(json.dumps(data).encode("utf8"))

    def send(self, data: Dict[str, Any]):
        """

        :param data:
            data format: {
                "sample_id": str,
                "process_id": int,
                "thread_id": int,
                "timestamp": float,
                "name": str,
                "stack_info": str,
                "execution_time": int,  # milliseconds
            }

        :return:
        """
        message = self._encode(data)
        headers = {
            "Content-Encoding": "deflate",
            "Content-Type": "application/octet-stream",
        }
        self._transport.send(self._add_url, headers, message)

    def build_data(
        self, name: str, stack_info: str, execution_time: int, **kwargs
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "stack_info": stack_info,
            "execution_time": execution_time,
            **kwargs,
        }

    def capture(self, data: Dict[str, Any]):
        assert "name" in data, "'name' is required."
        assert "stack_info" in data, "'stack_info' is required."
        assert "execution_time" in data, "'execution_time' is required."

        data = dict(data)
        data.setdefault("sample_id", uuid.uuid4().hex)
        data.setdefault("process_id", os.getpid())
        data.setdefault("thread_id", threading.current_thread().ident)
        data.setdefault("timestamp", time.time())
        self.send(data)
