import logging
import threading
from queue import Queue, Full
from urllib.request import Request, urlopen, HTTPError

from time import sleep
from typing import Dict


logger = logging.getLogger("pysample.transport")


class Transport(object):
    def send(self, url: str, headers: Dict[str, str], data: bytes):
        raise NotImplementedError


class ThreadTransport(Transport):
    def __init__(self, max_queue_size: int = -1, send_timeout: int = 5):
        self._thread = None
        self._active = False
        self._lock = threading.Lock()
        self._send_timeout = send_timeout
        self._queue = Queue(max_queue_size)

    def send(self, url: str, headers: Dict[str, str], data: bytes):
        try:
            self._queue.put((url, headers, data), block=False)
        except Full:
            logger.warning("Thread transport queue is full")

    def is_alive(self):
        return self._thread and self._thread.is_alive()

    def start(self):
        self._lock.acquire()
        try:
            if not self.is_alive():
                name = "PySample.ThreadTransport"
                self._thread = threading.Thread(target=self._run, name=name)
                self._thread.setDaemon(True)
                self._thread.start()
                self._active = True
        finally:
            self._lock.release()

    def stop(self, timeout: int = None):
        with self._lock:
            if self._thread:
                self._thread.join(timeout=timeout)
                self._thread = None

    def _send_request(self, url: str, headers: Dict[str, str], data: bytes):
        try:
            response = urlopen(
                url=Request(url, headers=headers), data=data, timeout=self._send_timeout
            )
        except HTTPError:
            raise
        return response

    def _run(self):
        while self._active:
            url, headers, data = self._queue.get()
            try:
                self._send_request(url, headers, data)
            except Exception:
                logger.error("Failed to send request", stack_info=True)
            finally:
                self._queue.task_done()

            sleep(0)
