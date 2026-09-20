from pathlib import Path

from .errors import AutoCamError
from .model import Frame


class OpenCVFrameProvider:
    """Read requested SOURCE samples only; decoded frames are never persisted."""

    def frames(self, source: Path, intervals, source_origin_us, rotation_degrees, sample_interval_us):
        try:
            import cv2
        except ImportError as exc:
            raise AutoCamError('Install M4 runtime: pip install -e ".[autocam]"') from exc
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise AutoCamError(f"Cannot open source video: {source}")
        if hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
            capture.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
        try:
            for start_us, end_us in intervals:
                timestamp = start_us
                while timestamp < end_us:
                    capture.set(cv2.CAP_PROP_POS_MSEC, max(0, timestamp - source_origin_us) / 1000)
                    ok, image = capture.read()
                    if not ok:
                        raise AutoCamError(f"Frame decode failed near SOURCE {timestamp} us")
                    if rotation_degrees == 90:
                        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                    elif rotation_degrees == 180:
                        image = cv2.rotate(image, cv2.ROTATE_180)
                    elif rotation_degrees == 270:
                        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    height, width = image.shape[:2]
                    yield Frame(timestamp, image, width, height)
                    timestamp += sample_interval_us
        finally:
            capture.release()
