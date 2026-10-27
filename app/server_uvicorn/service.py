"""
Core Background Surveillance Service for FastAPI / Uvicorn Server
Runs video capture loop in a separate thread and provides thread-safe access to frames and stats.
"""

import os
import sys
import threading
import time
from typing import Dict, Any, Optional
import cv2
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module1_tracking.pipeline import HumanDetectionModule
from core.module3_adaptive_env.engine import AdaptiveEnvironmentEngine
from core.module2_tripwire_gui.calibrator import TripwireCalibrator


class VideoSurveillanceService:
    _instance: Optional["VideoSurveillanceService"] = None

    @classmethod
    def get_instance(cls) -> "VideoSurveillanceService":
        if cls._instance is None:
            cls._instance = VideoSurveillanceService()
        return cls._instance

    def __init__(self):
        self.calibrator = TripwireCalibrator(os.path.join(WORKSPACE_ROOT, "data", "configs", "tripwire_config.json"))
        line = self.calibrator.load_config() or ((135, 38), (135, 213))

        self.detector = HumanDetectionModule(
            line_coords=line,
            d_threshold=35.0,
            use_internal_subtractor=False
        )
        self.env_engine = AdaptiveEnvironmentEngine()

        sample_1 = os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi")
        sample_2 = os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")
        self.video_source: Any = sample_1 if os.path.exists(sample_1) else sample_2
        self.running: bool = False
        self.is_paused: bool = False
        self.thread: Optional[threading.Thread] = None
        self.lock: threading.Lock = threading.Lock()

        # Cached outputs for streaming
        self.current_annotated_frame: Optional[np.ndarray] = None
        self.current_mask_frame: Optional[np.ndarray] = None
        self.events_history = []
        self.current_stats: Dict[str, Any] = {
            "count_in": 0,
            "count_out": 0,
            "inside": 0,
            "active_objects_count": 0,
            "fps": 0.0,
            "is_night_mode": False,
            "is_paused": False,
            "mean_luminance": 100.0,
            "tripwire": {"pt1": list(line[0]), "pt2": list(line[1]), "d_threshold": 35.0},
            "events": []
        }

    def pause(self):
        with self.lock:
            self.is_paused = True
            self.current_stats["is_paused"] = True

    def resume(self):
        with self.lock:
            self.is_paused = False
            self.current_stats["is_paused"] = False

    def toggle_playback(self) -> bool:
        with self.lock:
            self.is_paused = not self.is_paused
            self.current_stats["is_paused"] = self.is_paused
            return self.is_paused

    def get_config(self) -> Dict[str, Any]:
        with self.lock:
            pt1 = self.detector.tripwire.pt1
            pt2 = self.detector.tripwire.pt2
            d = self.detector.tripwire.d_threshold
            return {
                "pt1": [int(pt1[0]), int(pt1[1])],
                "pt2": [int(pt2[0]), int(pt2[1])],
                "d_threshold": float(d),
                "video_source": str(self.video_source)
            }

    def get_events(self):
        with self.lock:
            return list(self.events_history)

    def start(self, video_source: Optional[str] = None):
        if self.running:
            return
        if video_source:
            self.video_source = video_source

        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print(f"[SurveillanceService] Started background worker on source: {self.video_source}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        print("[SurveillanceService] Stopped background worker.")

    def reset_counters(self):
        with self.lock:
            self.detector.reset()
            self.env_engine.reset()
            self.events_history.clear()
            self.current_stats["count_in"] = 0
            self.current_stats["count_out"] = 0
            self.current_stats["inside"] = 0
            self.current_stats["events"] = []

    def update_tripwire(self, pt1, pt2, d_threshold=35.0):
        with self.lock:
            self.detector.set_line((pt1, pt2), d_threshold)
            self.calibrator.save_config((pt1, pt2), d_threshold)

    def _worker_loop(self):
        cap = cv2.VideoCapture(self.video_source)
        while self.running:
            if self.is_paused:
                time.sleep(0.04)
                continue

            if not cap.isOpened():
                time.sleep(0.5)
                cap = cv2.VideoCapture(self.video_source)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                # Video lặp lại vô tận - xóa cache đối tượng tránh đếm ảo do nhảy frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                with self.lock:
                    self.detector.tracker.objects.clear()
                    self.detector.tracker.boxes.clear()
                    self.detector.tracker.disappeared.clear()
                    self.detector.tracker.history.clear()
                    self.detector.tripwire.states.clear()
                continue

            # 1. Module 3
            clean_mask, enhanced_frame, telemetry = self.env_engine.process(frame)

            # 2. Module 1
            res = self.detector.process_frame(
                frame=enhanced_frame,
                clean_mask=clean_mask,
                annotate=True,
                extra_status="FASTAPI SURVEILLANCE ENGINE"
            )

            # Cập nhật state an toàn luồng
            with self.lock:
                if res["events"]:
                    for evt_type, obj_id in res["events"]:
                        self.events_history.insert(0, {
                            "id": f"evt-{int(time.time()*1000)}-{obj_id}",
                            "timestamp": time.strftime("%H:%M:%S"),
                            "object_id": int(obj_id),
                            "type": str(evt_type),
                            "action": "Ingress" if evt_type == "IN" else "Egress",
                            "inside": int(res["inside"])
                        })
                        if len(self.events_history) > 100:
                            self.events_history.pop()

                self.current_annotated_frame = res["annotated_frame"]
                self.current_mask_frame = res["clean_mask"]
                self.current_stats = {
                    "count_in": res["count_in"],
                    "count_out": res["count_out"],
                    "inside": res["inside"],
                    "active_objects_count": len(res["tracked_objects"]),
                    "fps": round(res["fps"], 1),
                    "is_night_mode": telemetry["is_night_mode"],
                    "is_paused": self.is_paused,
                    "mean_luminance": round(telemetry["mean_luminance"], 1),
                    "tripwire": {
                        "pt1": [int(self.detector.tripwire.pt1[0]), int(self.detector.tripwire.pt1[1])],
                        "pt2": [int(self.detector.tripwire.pt2[0]), int(self.detector.tripwire.pt2[1])],
                        "d_threshold": float(self.detector.tripwire.d_threshold)
                    },
                    "events": list(self.events_history[:25])
                }

            # Giữ nhịp ~30-40 FPS
            time.sleep(0.025)

        cap.release()

    def get_latest_frame_jpeg(self, use_mask: bool = False) -> Optional[bytes]:
        with self.lock:
            target = self.current_mask_frame if use_mask else self.current_annotated_frame
            if target is None:
                return None
            ret, jpeg = cv2.imencode(".jpg", target)
            return jpeg.tobytes() if ret else None

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.current_stats)
