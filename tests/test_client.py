import json
import zlib
import uuid
import unittest
from mock import MagicMock

from pysample.client import Client


class TestClient(unittest.TestCase):
    def _make_test_client(self, transport) -> Client:
        return Client(
            "http://localhost:8000/proj", transport
        )

    def test_parse_url(self):
        url, project = Client.parse_url("http://localhost:8000/sample")
        self.assertEqual(url, 'http://localhost:8000')
        self.assertEqual(project, 'sample')

        with self.assertRaises(ValueError):
            Client.parse_url("http://localhost:8000/sample/")

        with self.assertRaises(ValueError):
            Client.parse_url("http://localhost:8000/sample!")

        with self.assertRaises(ValueError):
            Client.parse_url("localhost:8000/sample")

        with self.assertRaises(ValueError):
            Client.parse_url("sample")

    def test_capture(self):
        mock_transport = MagicMock()
        client = self._make_test_client(mock_transport)
        data = client.build_data(
            "/rest/sample/list",
            uuid.uuid4().hex,
            "mock stack info",
            20,
        )
        client.capture(data)
        url = "http://localhost:8000/proj/sample/add"
        headers = {
            "Content-Encoding": "deflate",
            "Content-Type": "application/octet-stream",
        }
        call_args = mock_transport.send.call_args[0]
        self.assertEqual(url, call_args[0])
        self.assertDictEqual(headers, call_args[1])
        actual_data = json.loads(zlib.decompress(call_args[2]))
        self.assertIn("sample_id", actual_data)
        self.assertIn("process_id", actual_data)
        self.assertIn("thread_id", actual_data)
        self.assertIn("timestamp", actual_data)
