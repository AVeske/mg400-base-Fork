"""Camera streaming and cleanup tests without opening real camera hardware."""

import unittest
import os
from unittest.mock import Mock, patch

from mg400 import server, stream


class TableStreamTest(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"MG400_TABLE_CAMERA_INDEX": "0"})
        environment.start()
        self.addCleanup(environment.stop)
        stream._camera = None
        stream._viewers = 0
        stream._selected_index = None
        stream._generation = 0
        self.camera = Mock()
        self.camera.isOpened.return_value = True
        self.camera.read.return_value = (True, object())
        self.capture = patch.object(stream.cv2, "VideoCapture", return_value=self.camera)
        self.capture.start()
        self.encode = patch.object(stream.cv2, "imencode",
                                   return_value=(True, Mock(tobytes=lambda: b"jpeg-data")))
        self.encode.start()

    def tearDown(self):
        self.encode.stop()
        self.capture.stop()
        stream._camera = None
        stream._viewers = 0
        stream._selected_index = None
        stream._generation = 0

    def test_camera_selection_api_does_not_open_hardware(self):
        client = server.app.test_client()
        self.assertEqual(client.get("/api/camera/table").json["index"], 0)
        response = client.post("/api/camera/table", json={"index": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["index"], 1)
        stream.cv2.VideoCapture.assert_not_called()
        for value in (-1, True, "1", None):
            self.assertEqual(client.post("/api/camera/table", json={"index": value}).status_code, 400)
        self.assertEqual(client.post("/api/camera/table", json=[]).status_code, 400)
        self.assertEqual(client.get("/api/camera/table").json["index"], 1)

    def test_switching_releases_old_camera_and_old_viewer_cannot_close_new_camera(self):
        replacement = Mock()
        replacement.isOpened.return_value = True
        replacement.read.return_value = (True, object())
        stream.cv2.VideoCapture.side_effect = [self.camera, replacement]
        first = stream.generate_table_stream()
        next(first)
        stream.select_table_camera(1)
        self.camera.release.assert_called_once()
        second = stream.generate_table_stream()
        next(second)
        with self.assertRaises(StopIteration):
            next(first)
        replacement.release.assert_not_called()
        self.assertEqual(stream._viewers, 1)
        second.close()
        replacement.release.assert_called_once()
        self.assertEqual([call.args[0] for call in stream.cv2.VideoCapture.call_args_list], [0, 1])

    def test_camera_index_can_be_selected_without_falling_back(self):
        with patch.dict(os.environ, {"MG400_TABLE_CAMERA_INDEX": "1"}):
            frames = stream.generate_table_stream()
            next(frames)
            stream.cv2.VideoCapture.assert_called_once_with(1)
            frames.close()

    def test_invalid_camera_index_does_not_open_any_camera(self):
        with patch.dict(os.environ, {"MG400_TABLE_CAMERA_INDEX": "invalid"}):
            self.assertEqual(list(stream.generate_table_stream()), [])
        stream.cv2.VideoCapture.assert_not_called()

    def test_jpeg_framing_and_disconnect_cleanup(self):
        frames = stream.generate_table_stream()
        self.assertEqual(next(frames), b"--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg-data\r\n")
        frames.close()
        self.camera.release.assert_called_once()
        self.assertEqual(stream._viewers, 0)

    def test_unavailable_camera_ends_cleanly(self):
        self.camera.isOpened.return_value = False
        self.assertEqual(list(stream.generate_table_stream()), [])
        self.camera.release.assert_called_once()
        self.camera.read.assert_not_called()

    def test_frame_failure_releases_camera(self):
        self.camera.read.return_value = (False, None)
        self.assertEqual(list(stream.generate_table_stream()), [])
        self.camera.release.assert_called_once()

    def test_opencv_exception_releases_camera(self):
        self.camera.read.side_effect = stream.cv2.error("camera disconnected")
        self.assertEqual(list(stream.generate_table_stream()), [])
        self.camera.release.assert_called_once()

    def test_multiple_viewers_share_camera_until_last_disconnect(self):
        first, second = stream.generate_table_stream(), stream.generate_table_stream()
        next(first)
        next(second)
        stream.cv2.VideoCapture.assert_called_once_with(0)
        first.close()
        self.camera.release.assert_not_called()
        second.close()
        self.camera.release.assert_called_once()

    def test_page_and_mjpeg_route(self):
        client = server.app.test_client()
        page = client.get("/stream")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'src="/video/table"', page.data)
        self.assertIn(b'Tool camera not connected yet', page.data)
        self.assertNotIn(b'/video/tool', page.data)
        page.close()
        with client.get("/") as station_page:
            self.assertIn(b'href="/stream"', station_page.data)
        response = client.get("/video/table", buffered=False)
        self.assertEqual(response.content_type, "multipart/x-mixed-replace; boundary=frame")
        self.assertIn(b'jpeg-data', next(response.response))
        response.close()
        self.camera.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
