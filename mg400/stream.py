"""Local USB table-camera MJPEG stream. No camera opens at import time."""

import logging
import os
import threading
import time

import cv2

log = logging.getLogger(__name__)
_camera = None
_viewers = 0
_lock = threading.Lock()
_selected_index = None
_generation = 0


def _configured_index():
    value = _selected_index
    if value is None:
        value = int(os.environ.get("MG400_TABLE_CAMERA_INDEX", "0"))
    if value < 0:
        raise ValueError("Camera index must be a non-negative integer")
    return value


def table_camera_status():
    with _lock:
        return {"index": _configured_index(), "open": _camera is not None}


def select_table_camera(index):
    """Change the process-wide table camera; old streams end safely."""
    global _selected_index, _camera, _viewers, _generation
    if type(index) is not int or index < 0:
        raise ValueError("Camera index must be a non-negative integer")
    with _lock:
        if _selected_index == index:
            return
        _selected_index = index
        _generation += 1
        if _camera is not None:
            _camera.release()
            _camera = None
        _viewers = 0
        log.info("Selected table camera index %s", index)


def _acquire_camera():
    global _camera, _viewers
    with _lock:
        if _camera is None:
            try:
                index = _configured_index()
            except ValueError:
                log.error("MG400_TABLE_CAMERA_INDEX must be a non-negative integer")
                return None
            camera = cv2.VideoCapture(index)
            if not camera.isOpened():
                camera.release()
                log.error("Cannot open table camera %s. Check USB connection, camera permissions and other camera apps.", index)
                return None
            _camera = camera
            log.info("Table camera opened: index=%s", index)
        _viewers += 1
        return _generation


def _release_camera(generation):
    global _camera, _viewers
    with _lock:
        # A disconnected old viewer must not release the newly selected camera.
        if generation != _generation:
            return
        _viewers -= 1
        if _viewers == 0 and _camera is not None:
            _camera.release()
            _camera = None
            log.info("Table camera released")


def generate_table_stream():
    """Yield JPEG multipart frames; share the selected camera across viewers in this process."""
    generation = None
    try:
        generation = _acquire_camera()
        if generation is None:
            return
        while True:
            with _lock:
                if generation != _generation:
                    return
                ok, frame = _camera.read()
                if not ok:
                    log.error("Could not read table camera frame; reload the stream after checking the camera.")
                    return
                encoded, jpeg = cv2.imencode(".jpg", frame)
            if not encoded:
                log.warning("Could not encode table camera frame as JPEG")
                time.sleep(0.1)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + jpeg.tobytes() + b"\r\n")
            time.sleep(1 / 15)
    except cv2.error:
        log.exception("Table camera stream failed")
    finally:
        if generation is not None:
            _release_camera(generation)
