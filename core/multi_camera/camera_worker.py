"""
PHASE 2 ARCHITECTURE: MULTI-CAMERA CONCURRENCY SUBSYSTEM
Camera Worker: Quản lý luồng đọc và chạy pipeline xử lý ảnh độc lập cho từng camera.
"""

import threading
import time
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

from core.module1_tracking.pipeline import HumanDetectionModule
from core.module3_adaptive_env.engine import AdaptiveEnvironmentEngine
from core.module2_tripwire_gui.calibrator import normalize_video_source
from core.device_scanner import get_profile_for_source


class CameraWorker:
    """
    Worker xử lý video cho một Camera ID duy nhất.
    Hoạt động hoàn toàn độc lập, lỗi phần cứng ở 1 camera không ảnh hưởng tới camera khác.
    """

    def __init__(self, camera_id: str, video_source: Any):
        self.camera_id = str(camera_id)
        self.video_source = normalize_video_source(video_source)
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.lock: threading.Lock = threading.Lock()

        prof = get_profile_for_source(self.video_source)
        self.detector = HumanDetectionModule(
            line_coords=(prof["pt1"], prof["pt2"]),
            d_threshold=prof["d_threshold"],
            use_internal_subtractor=False
        )
        self.env_engine = AdaptiveEnvironmentEngine()

        self.camera_status: str = "connecting"
        self.current_annotated_jpeg: Optional[bytes] = None
        self.current_mask_jpeg: Optional[bytes] = None
        self.last_access_time: float = 0.0

        self.stats: Dict[str, Any] = {
            "camera_id": self.camera_id,
            "count_in": 0,
            "count_out": 0,
            "inside": 0,
            "fps": 0.0,
            "camera_status": self.camera_status,
            "active_objects": 0
        }

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run(self):
        def _open(src):
            if isinstance(src, int) and sys.platform.startswith("win"):
                c = cv2.VideoCapture(src, cv2.CAP_DSHOW)
                if c.isOpened():
                    return c
            return cv2.VideoCapture(src)

        cap = _open(self.video_source)
        is_live = isinstance(self.video_source, int) or str(self.video_source).startswith(("rtsp://", "http://"))

        with self.lock:
            self.camera_status = "online" if cap.isOpened() else "offline"
            self.stats["camera_status"] = self.camera_status

        while self.running:
            if not cap.isOpened():
                time.sleep(0.5)
                cap = _open(self.video_source)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                if is_live:
                    time.sleep(0.05)
                    continue
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    with self.lock:
                        self.detector.reset()
                    continue

            # Downscale if > 640px
            h, w = frame.shape[:2]
            if w > 640:
                frame = cv2.resize(frame, (640, int(h * 640 / w)), interpolation=cv2.INTER_AREA)

            clean_mask, enhanced_frame, tele = self.env_engine.process(frame)
            res = self.detector.process_frame(
                frame=enhanced_frame,
                clean_mask=clean_mask,
                annotate=True,
                extra_status=f"CAM: {self.camera_id}"
            )

            # Lazy encode on demand
            if time.time() - self.last_access_time < 3.0:
                _, buf_ann = cv2.imencode(".jpg", res["annotated_frame"], [cv2.IMWRITE_JPEG_QUALITY, 80])
                _, buf_msk = cv2.imencode(".jpg", res["clean_mask"], [cv2.IMWRITE_JPEG_QUALITY, 75])
                with self.lock:
                    self.current_annotated_jpeg = buf_ann.tobytes()
                    self.current_mask_jpeg = buf_msk.tobytes()

            with self.lock:
                self.stats.update({
                    "count_in": res["count_in"],
                    "count_out": res["count_out"],
                    "inside": res["inside"],
                    "fps": round(res["fps"], 1),
                    "camera_status": "online",
                    "active_objects": len(res["tracked_objects"])
                })

            time.sleep(0.005 if is_live else 0.02)

        cap.release()

    def get_frame(self, use_mask: bool = False) -> Optional[bytes]:
        with self.lock:
            self.last_access_time = time.time()
            return self.current_mask_jpeg if use_mask else self.current_annotated_jpeg

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.stats)

