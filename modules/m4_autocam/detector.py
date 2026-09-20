from importlib.metadata import PackageNotFoundError, version

from .errors import AutoCamError
from .model import Detection


class OpenCVSubjectDetector:
    """Replaceable CPU face + person detector using bundled OpenCV models."""
    name = "opencv-haar-hog"

    def __init__(self, requested_device="auto", cpu_fallback=True):
        try:
            import cv2
        except ImportError as exc:
            raise AutoCamError('Install M4 runtime: pip install -e ".[autocam]"') from exc
        self.cv2 = cv2
        try:
            self.version = version("opencv-python-headless")
        except PackageNotFoundError:
            try:
                self.version = version("opencv-python")
            except PackageNotFoundError:
                self.version = getattr(cv2, "__version__", "unknown")
        self.warnings = []
        # Haar cascades and the default HOG backend used here are CPU-only.
        if requested_device == "cuda":
            if not cpu_fallback:
                raise AutoCamError("CUDA is not supported by the M4 v1 OpenCV backend")
            self.warnings.append("CPU_FALLBACK")
        self.device = "cpu"  # This v1 backend is CPU; interface permits replacement.
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face = cv2.CascadeClassifier(cascade_path)
        if self.face.empty():
            raise AutoCamError("OpenCV face cascade unavailable")
        self.hog = cv2.HOGDescriptor(); self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        cv2 = self.cv2
        gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
        faces = self.face.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
        detections = [Detection("face", x/frame.width, y/frame.height, w/frame.width, h/frame.height, 0.9)
                      for x, y, w, h in faces]
        if detections:
            return detections
        people, weights = self.hog.detectMultiScale(frame.image, winStride=(8, 8), padding=(8, 8), scale=1.05)
        return [Detection("person", x/frame.width, y/frame.height, w/frame.width, h/frame.height,
                          max(0.0, min(1.0, float(weight))))
                for (x, y, w, h), weight in zip(people, weights)]
