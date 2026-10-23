"""Report drawing outcomes to Atom; Atom forwards them to public Flask.

A separate worker retries HTTP delivery without running robot commands again.
Pending reports are in memory and are lost if the station process exits.
"""

import json
import logging
import queue
import threading
from urllib.request import ProxyHandler, Request, build_opener

log = logging.getLogger(__name__)


class AtomResultReporter:
    def __init__(self, atom_url="http://192.168.4.1", timeout=5.0, retry_interval=5.0):
        self.url = atom_url.rstrip("/") + "/api/result"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.pending = queue.Queue()
        self._stopped = threading.Event()
        # Local AP traffic must not go through a system HTTP proxy.
        self._opener = build_opener(ProxyHandler({}))
        self.worker = threading.Thread(target=self._worker_loop,
                                       name="atom-results", daemon=True)
        self.worker.start()

    def submit(self, job_id, result):
        if type(job_id) is not int or not 0 <= job_id <= 2147483647:
            raise ValueError("Invalid job ID")
        if result not in ("done", "error"):
            raise ValueError("Only final drawing outcomes may be reported")
        self.pending.put({"id": job_id, "result": result})

    def _send_once(self, payload):
        request = Request(self.url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                # A captive-portal redirect or HTML page is not acknowledgement.
                if response.geturl() != self.url or not 200 <= response.status < 300:
                    return False
                acknowledgement = json.load(response)
                return isinstance(acknowledgement, dict) and acknowledgement.get("ok") is True
        except Exception as error:
            log.warning("Result delivery failed for job %s: %s", payload["id"], error)
            return False

    def _deliver(self, payload):
        while not self._stopped.is_set():
            if self._send_once(payload):
                log.info("Atom acknowledged job %s: %s", payload["id"], payload["result"])
                return
            log.warning("Retrying job %s result in %.1f seconds", payload["id"], self.retry_interval)
            if self._stopped.wait(self.retry_interval):
                return

    def _worker_loop(self):
        while not self._stopped.is_set():
            try:
                payload = self.pending.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._deliver(payload)
            finally:
                self.pending.task_done()

    def close(self):
        self._stopped.set()
        self.worker.join(timeout=self.timeout + 1)
