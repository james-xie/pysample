import os
import zlib
import json
import uuid
import time
import threading
import unittest


class TestServer(unittest.TestCase):
    def setUp(self) -> None:
        from server.app import app
        self._app = app

    def test_sample_add_and_get(self):
        with self._app.test_client() as c:
            project = "proj"
            sample_id = uuid.uuid4().hex
            data = zlib.compress(json.dumps(
                {
                    "name": "/test/path",
                    "sample_id": sample_id,
                    "process_id": os.getpid(),
                    "thread_id": threading.current_thread().ident,
                    "timestamp": time.time(),
                    "stack_info": "test stack info",
                    "execution_time": 100,
                }
            ).encode("utf8"))
            rv = c.post(f'/sample/add/{project}', data=data)
            data = json.loads(rv.data)
            self.assertEqual(data["success"], True)

            rv = c.get(f'/sample/get/{project}/{sample_id}')
            resp_data = json.loads(rv.data)
            self.assertEqual(resp_data["success"], True)
            self.assertEqual(resp_data["data"]["stack_info"], "test stack info")
            self.assertEqual(resp_data["data"]["execution_time"], 100)

    def test_flame_graph(self):
        with self._app.test_client() as c:
            project = "proj"
            sample_id = uuid.uuid4().hex
            data = zlib.compress(json.dumps(
                {
                    "name": "/test/path",
                    "sample_id": sample_id,
                    "process_id": os.getpid(),
                    "thread_id": threading.current_thread().ident,
                    "timestamp": time.time(),
                    "stack_info": "test_server.py 10",
                    "execution_time": 100,
                }
            ).encode("utf8"))
            rv = c.post(f'/sample/add/{project}', data=data)
            data = json.loads(rv.data)
            self.assertEqual(data["success"], True)

            rv = c.get(f'/sample/flamegraph/{project}/{sample_id}')
            self.assertIn(b"Flame graph stack visualization", rv.data)


