from pathlib import Path

import cv2
import numpy as np
import pytest

from modules.m4_autocam.detector import OpenCVSubjectDetector
from modules.m4_autocam.errors import AutoCamError
from modules.m4_autocam.frames import OpenCVFrameProvider
from modules.m4_autocam.model import Frame


def make_video(path: Path):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened()
    for index in range(10):
        writer.write(np.full((48, 64, 3), index * 20, dtype=np.uint8))
    writer.release()


def test_frame_provider_decodes_only_requested_source_samples_and_rotates(tmp_path):
    source = tmp_path / "source.avi"
    make_video(source)
    frames = list(OpenCVFrameProvider().frames(source, [(200_000, 500_000)], 0, 90, 100_000))
    assert [frame.source_us for frame in frames] == [200_000, 300_000, 400_000]
    assert all((frame.width, frame.height) == (48, 64) for frame in frames)


def test_opencv_detector_runs_on_cpu_without_subject():
    detector = OpenCVSubjectDetector("cpu")
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(Frame(0, image, 320, 240)) == []
    assert detector.device == "cpu"


def test_cuda_request_has_explicit_cpu_fallback():
    detector = OpenCVSubjectDetector("cuda", cpu_fallback=True)
    assert detector.device == "cpu"
    assert detector.warnings == ["CPU_FALLBACK"]
    with pytest.raises(AutoCamError, match="not supported"):
        OpenCVSubjectDetector("cuda", cpu_fallback=False)
