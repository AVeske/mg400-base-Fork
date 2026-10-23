"""Letter job lifecycle tests without robot motion or public-server access."""

import io
import json
import unittest
from unittest.mock import Mock, patch

from flask import Flask

from mg400.letter_api import register_letter_routes
from mg400.letter_queue import LETTER_GAP, LetterQueue
from mg400.letters import get_letter_width
from mg400.result_client import AtomResultReporter


class LetterApiTest(unittest.TestCase):
    def setUp(self):
        self.jobs = Mock()
        self.jobs.pending_count.return_value = 1
        app = Flask(__name__)
        register_letter_routes(app, self.jobs)
        self.api = app.test_client()

    def test_id_and_lowercase_letter_are_preserved(self):
        response = self.api.post("/api/letter", json={"letter": "a", "id": 17})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json["id"], 17)
        self.jobs.add.assert_called_once_with("A", job_id=17)

    def test_legacy_letter_without_id(self):
        self.assertEqual(self.api.post("/api/letter", json={"letter": "A"}).status_code, 202)
        self.jobs.add.assert_called_once_with("A", job_id=None)

    def test_invalid_input_does_not_enter_queue(self):
        for body in ([], None, {"letter": 1}, {"letter": "AA"}, {"letter": "?"},
                     {"letter": "A", "id": True}, {"letter": "A", "id": -1},
                     {"letter": "A", "id": "17"}, {"letter": "A", "id": None},
                     {"letter": "A", "id": 2147483648}):
            with self.subTest(body=body):
                response = self.api.post("/api/letter", data=json.dumps(body),
                                         content_type="application/json")
                self.assertEqual(response.status_code, 400)
        self.jobs.add.assert_not_called()


class LetterWorkerTest(unittest.TestCase):
    def setUp(self):
        self.reporter = Mock()
        self.move = Mock()
        with patch("mg400.letter_queue.threading.Thread.start"):
            self.jobs = LetterQueue(self.move, self.reporter)

    def test_done_is_reported_only_after_drawing_returns(self):
        def drawing(*args, **kwargs):
            self.reporter.submit.assert_not_called()
        with patch("mg400.letter_queue.write_plan", side_effect=drawing) as write:
            self.jobs._process_job("A", 17)
        write.assert_called_once()
        self.reporter.submit.assert_called_once_with(17, "done")
        self.assertEqual(self.jobs.cursor_x, get_letter_width("A") + LETTER_GAP)

    def test_failed_movement_reports_error_without_advancing_cursor(self):
        with patch("mg400.letter_queue.write_plan", side_effect=RuntimeError("move timed out")):
            self.jobs._process_job("A", 18)
        self.reporter.submit.assert_called_once_with(18, "error")
        self.assertEqual(self.jobs.cursor_x, 0)

    def test_legacy_letter_has_no_public_result(self):
        with patch("mg400.letter_queue.write_plan"):
            self.jobs._process_job("A", None)
        self.reporter.submit.assert_not_called()

    def test_reporting_error_does_not_redraw_or_mark_drawing_failed(self):
        self.reporter.submit.side_effect = RuntimeError("report unavailable")
        with patch("mg400.letter_queue.write_plan") as write:
            self.jobs._process_job("A", 19)
        write.assert_called_once()
        self.reporter.submit.assert_called_once_with(19, "done")
        self.assertEqual(self.jobs.cursor_x, get_letter_width("A") + LETTER_GAP)

    def test_queue_keeps_id_with_letter(self):
        self.jobs.add("B", job_id=23)
        self.assertEqual(self.jobs.queue.get_nowait(), ("B", 23))


class ResultReporterTest(unittest.TestCase):
    def setUp(self):
        with patch("mg400.result_client.threading.Thread.start"):
            self.reporter = AtomResultReporter(retry_interval=0)

    def response(self, body=b'{"ok":true}', status=200, url=None):
        response = io.BytesIO(body)
        response.status = status
        response.geturl = lambda: url or self.reporter.url
        return response

    def test_posts_exact_result_to_atom(self):
        self.reporter._opener = Mock()
        self.reporter._opener.open.return_value = self.response()
        self.assertTrue(self.reporter._send_once({"id": 17, "result": "done"}))
        request = self.reporter._opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://192.168.4.1/api/result")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"id": 17, "result": "done"})
        self.assertEqual(request.get_header("Content-type"), "application/json")

    def test_invalid_acknowledgements_and_http_errors_are_not_success(self):
        self.reporter._opener = Mock()
        for body, status, url in ((b'{"ok":false}', 200, None), (b'{}', 200, None),
                                  (b'<html>portal</html>', 200, None),
                                  (b'{"ok":true}', 500, None),
                                  (b'{"ok":true}', 200, "http://192.168.4.1/")):
            self.reporter._opener.open.return_value = self.response(body, status, url)
            self.assertFalse(self.reporter._send_once({"id": 17, "result": "done"}))
        self.reporter._opener.open.side_effect = TimeoutError("offline")
        self.assertFalse(self.reporter._send_once({"id": 17, "result": "error"}))

    def test_retry_keeps_same_id_and_result(self):
        payload = {"id": 17, "result": "done"}
        self.reporter._send_once = Mock(side_effect=[False, False, True])
        self.reporter._deliver(payload)
        self.assertEqual(self.reporter._send_once.call_count, 3)
        for call in self.reporter._send_once.call_args_list:
            self.assertEqual(call.args, (payload,))

    def test_rejects_non_final_status(self):
        with self.assertRaises(ValueError):
            self.reporter.submit(17, "Atom Accepted")
        self.assertTrue(self.reporter.pending.empty())


if __name__ == "__main__":
    unittest.main()
