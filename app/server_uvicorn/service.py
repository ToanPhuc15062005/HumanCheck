"""
Core Background Surveillance Service for FastAPI / Uvicorn Server
Runs video capture loop in a separate thread and provides thread-safe access to frames and stats.
Supports thread-safe camera switching, resolution normalization, and heartbeat telemetry.
"""

import os
import sys
import threading
import time
from typing import Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module1_tracking.pipeline import HumanDetectionModule
from core.module3_adaptive_env.engine import AdaptiveEnvironmentEngine
from core.module2_tripwire_gui.calibrator import TripwireCalibrator, normalize_video_source
from core.device_scanner import get_profile_for_source, save_camera_profile


class VideoSurveillanceService:
    _instance: Optional["VideoSurveillanceService"] = None

    @classmethod
    def get_instance(cls) -> "VideoSurveillanceService":
        if cls._instance is None:
            cls._instance = VideoSurveillanceService()
        return cls._instance

    def __init__(self):
        self.calibrator = TripwireCalibrator(
            config_path=os.path.join(WORKSPACE_ROOT, "data", "configs", "tripwire_config.json"),
            profile_path=os.path.join(WORKSPACE_ROOT, "data", "configs", "cameras_profile.json")
        )

        env_source = os.environ.get("SURVEILLANCE_SOURCE")
        if env_source:
            self.video_source = normalize_video_source(env_source)
        else:
            sample_1 = os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi")
            sample_2 = os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")
            self.video_source = sample_1 if os.path.exists(sample_1) else sample_2

        initial_profile = get_profile_for_source(self.video_source)
        line = (initial_profile["pt1"], initial_profile["pt2"])
        d_thresh = initial_profile.get("d_threshold", 35.0)

        self.detector = HumanDetectionModule(
            line_coords=line,
            d_threshold=d_thresh,
            use_internal_subtractor=False
        )
        self.env_engine = AdaptiveEnvironmentEngine()

        self.running: bool = False
        self.is_paused: bool = False
        self.pause_event: threading.Event = threading.Event()
        self.pause_event.set()
        self.thread: Optional[threading.Thread] = None
        self.lock: threading.Lock = threading.Lock()

        # Command Request Queue for Thread-Safe Video Source Switching
        self._switch_lock: threading.Lock = threading.Lock()
        self._switch_request: Optional[Tuple[Any, threading.Event, Dict[str, Any]]] = None

        self.camera_status: str = "connecting"
        self.consecutive_dropped_frames: int = 0
        self.resolution: Tuple[int, int] = (320, 240)

        # Cached outputs for streaming
        self.current_annotated_frame: Optional[np.ndarray] = None
        self.current_mask_frame: Optional[np.ndarray] = None
        self.current_annotated_jpeg: Optional[bytes] = None
        self.current_mask_jpeg: Optional[bytes] = None
        self.last_stream_request_time: float = 0.0
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
            "camera_status": self.camera_status,
            "active_source": str(self.video_source),
            "resolution": list(self.resolution),
            "dropped_frames": 0,
            "tripwire": {"pt1": list(line[0]), "pt2": list(line[1]), "d_threshold": d_thresh},
            "events": []
        }

    def pause(self):
        with self.lock:
            self.is_paused = True
            self.pause_event.clear()
            self.current_stats["is_paused"] = True

    def resume(self):
        with self.lock:
            self.is_paused = False
            self.pause_event.set()
            self.current_stats["is_paused"] = False

    def toggle_playback(self) -> bool:
        with self.lock:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_event.clear()
            else:
                self.pause_event.set()
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
                "video_source": str(self.video_source),
                "camera_status": self.camera_status,
                "resolution": list(self.resolution)
            }

    def get_events(self):
        with self.lock:
            return list(self.events_history)

    def switch_source(self, new_source: Union[int, str], timeout: float = 4.0) -> bool:
        """
        Chuyển đổi nguồn camera an toàn đa luồng bằng Command Request Pattern.
        Worker thread sẽ thực thi việc đóng capture cũ và mở capture mới.
        """
        norm_source = normalize_video_source(new_source)

        if not self.running or not self.thread or not self.thread.is_alive():
            with self.lock:
                self.video_source = norm_source
                prof = get_profile_for_source(norm_source)
                self.detector.set_line((prof["pt1"], prof["pt2"]), prof["d_threshold"])
                self.current_stats["active_source"] = str(norm_source)
                self.current_stats["tripwire"] = {
                    "pt1": list(prof["pt1"]),
                    "pt2": list(prof["pt2"]),
                    "d_threshold": prof["d_threshold"]
                }
            return True

        done_event = threading.Event()
        result_holder: Dict[str, Any] = {"success": False, "error": None}

        with self._switch_lock:
            self._switch_request = (norm_source, done_event, result_holder)
            # Nếu đang pause thì đánh thức tạm để xử lý switch
            if self.is_paused:
                self.pause_event.set()

            finished = done_event.wait(timeout=timeout)
            if not finished:
                print(f"[SurveillanceService] switch_source timeout sau {timeout}s cho nguồn {norm_source}")
                return False

            return bool(result_holder.get("success", False))

    def start(self, video_source: Optional[Union[int, str]] = None):
        if self.running:
            return
        if video_source is not None:
            self.video_source = normalize_video_source(video_source)

        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print(f"[SurveillanceService] Started background worker on source: {self.video_source}")

    def stop(self):
        self.running = False
        self.pause_event.set()
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
            save_camera_profile(
                source=self.video_source,
                pt1=pt1,
                pt2=pt2,
                d_threshold=d_threshold
            )
            self.current_stats["tripwire"] = {
                "pt1": [int(pt1[0]), int(pt1[1])],
                "pt2": [int(pt2[0]), int(pt2[1])],
                "d_threshold": float(d_threshold)
            }

    def _worker_loop(self):
        source = normalize_video_source(self.video_source)

        def _open_capture(src):
            if isinstance(src, int) and sys.platform.startswith("win"):
                c = cv2.VideoCapture(src, cv2.CAP_DSHOW)
                if c.isOpened():
                    return c
            return cv2.VideoCapture(src)

        cap = _open_capture(source)

        # Warm-up nếu là webcam
        if isinstance(source, int) and cap.isOpened():
            for _ in range(5):
                cap.read()

        is_live_stream = isinstance(source, int) or (
            isinstance(source, str) and (source.startswith("rtsp://") or source.startswith("http://"))
        )

        fps_meta = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 30.0
        target_fps = fps_meta if (10.0 <= fps_meta <= 120.0) else 30.0
        target_dt = 1.0 / target_fps

        with self.lock:
            self.camera_status = "online" if cap.isOpened() else "offline"
            self.current_stats["camera_status"] = self.camera_status

        while self.running:
            # 0. Kiểm tra yêu cầu chuyển đổi nguồn (Command Queue)
            if self._switch_request is not None:
                new_src, done_ev, res_hold = self._switch_request
                self._switch_request = None
                norm_new_src = normalize_video_source(new_src)

                try:
                    new_cap = _open_capture(norm_new_src)
                    if new_cap.isOpened():
                        if isinstance(norm_new_src, int):
                            for _ in range(5):
                                new_cap.read()
                        ret_test, frame_test = new_cap.read()
                        if ret_test and frame_test is not None:
                            cap.release()
                            cap = new_cap
                            source = norm_new_src
                            self.video_source = norm_new_src
                            is_live_stream = isinstance(source, int) or (
                                isinstance(source, str) and (source.startswith("rtsp://") or source.startswith("http://"))
                            )
                            fps_meta = cap.get(cv2.CAP_PROP_FPS)
                            target_fps = fps_meta if (10.0 <= fps_meta <= 120.0) else 30.0
                            target_dt = 1.0 / target_fps

                            raw_h, raw_w = frame_test.shape[:2]
                            proc_w, proc_h = (640, int(raw_h * 640 / raw_w)) if raw_w > 640 else (raw_w, raw_h)

                            prof = get_profile_for_source(source, frame_resolution=(proc_w, proc_h))
                            with self.lock:
                                self.detector.set_line((prof["pt1"], prof["pt2"]), prof["d_threshold"])
                                self.detector.reset()
                                self.env_engine.reset()
                                self.current_annotated_jpeg = None
                                self.current_mask_jpeg = None
                                self.consecutive_dropped_frames = 0
                                self.camera_status = "online"
                                self.resolution = (proc_w, proc_h)
                                self.current_stats["active_source"] = str(source)
                                self.current_stats["camera_status"] = "online"
                                self.current_stats["resolution"] = [proc_w, proc_h]
                                self.current_stats["tripwire"] = {
                                    "pt1": list(prof["pt1"]),
                                    "pt2": list(prof["pt2"]),
                                    "d_threshold": prof["d_threshold"]
                                }

                            res_hold["success"] = True
                            done_ev.set()
                        else:
                            new_cap.release()
                            res_hold["success"] = False
                            res_hold["error"] = "Cannot read initial frame from camera"
                            done_ev.set()
                    else:
                        new_cap.release()
                        res_hold["success"] = False
                        res_hold["error"] = "Cannot open video capture"
                        done_ev.set()
                except Exception as ex:
                    res_hold["success"] = False
                    res_hold["error"] = str(ex)
                    done_ev.set()

            if self.is_paused:
                self.pause_event.wait(timeout=0.2)
                continue

            t_start = time.perf_counter()

            if not cap.isOpened():
                self.consecutive_dropped_frames += 1
                if self.consecutive_dropped_frames >= 20:
                    with self.lock:
                        self.camera_status = "offline"
                        self.current_stats["camera_status"] = "offline"
                time.sleep(0.5)
                cap = _open_capture(source)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                self.consecutive_dropped_frames += 1
                if self.consecutive_dropped_frames >= 20:
                    with self.lock:
                        self.camera_status = "offline"
                        self.current_stats["camera_status"] = "offline"

                if is_live_stream:
                    time.sleep(0.05)
                    if self.consecutive_dropped_frames >= 60:
                        # Thử khởi tạo lại capture sau gián đoạn kéo dài
                        cap.release()
                        time.sleep(0.5)
                        cap = _open_capture(source)
                    continue
                else:
                    # File video kết thúc -> Tua lại frame 0 và dọn tracker tránh đếm ảo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    with self.lock:
                        self.detector.reset()
                    self.consecutive_dropped_frames = 0
                    continue

            # Frame hợp lệ
            if self.consecutive_dropped_frames > 0:
                self.consecutive_dropped_frames = 0
                with self.lock:
                    self.camera_status = "online"
                    self.current_stats["camera_status"] = "online"

            # Chuẩn hóa độ phân giải xử lý (Processing Normalization)
            raw_h, raw_w = frame.shape[:2]
            if raw_w > 640:
                target_h = int(raw_h * 640 / raw_w)
                proc_frame = cv2.resize(frame, (640, target_h), interpolation=cv2.INTER_AREA)
            else:
                proc_frame = frame

            proc_h, proc_w = proc_frame.shape[:2]

            # 1. Module 3: Thích ứng môi trường
            clean_mask, enhanced_frame, telemetry = self.env_engine.process(proc_frame)

            # 2. Module 1: Phân đoạn, theo dõi và đếm qua vạch
            res = self.detector.process_frame(
                frame=enhanced_frame,
                clean_mask=clean_mask,
                annotate=True,
                extra_status="FASTAPI SURVEILLANCE ENGINE"
            )

            # 3. Tối ưu On-Demand Lazy Encoding: Chỉ nén JPEG nếu có ít nhất 1 client đang xem stream
            is_streaming_active = (time.time() - self.last_stream_request_time < 2.5)
            if is_streaming_active:
                ret_ann, buf_ann = cv2.imencode(".jpg", res["annotated_frame"], [cv2.IMWRITE_JPEG_QUALITY, 85])
                ret_msk, buf_msk = cv2.imencode(".jpg", res["clean_mask"], [cv2.IMWRITE_JPEG_QUALITY, 80])
                jpeg_ann = buf_ann.tobytes() if ret_ann else None
                jpeg_msk = buf_msk.tobytes() if ret_msk else None
            else:
                jpeg_ann = None
                jpeg_msk = None

            # Cập nhật state an toàn luồng
            with self.lock:
                self.resolution = (proc_w, proc_h)
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
                self.current_annotated_jpeg = jpeg_ann
                self.current_mask_jpeg = jpeg_msk
                self.current_stats = {
                    "count_in": res["count_in"],
                    "count_out": res["count_out"],
                    "inside": res["inside"],
                    "active_objects_count": len(res["tracked_objects"]),
                    "fps": round(res["fps"], 1),
                    "is_night_mode": telemetry["is_night_mode"],
                    "is_paused": self.is_paused,
                    "mean_luminance": round(telemetry["mean_luminance"], 1),
                    "camera_status": self.camera_status,
                    "active_source": str(self.video_source),
                    "resolution": [proc_w, proc_h],
                    "dropped_frames": self.consecutive_dropped_frames,
                    "tripwire": {
                        "pt1": [int(self.detector.tripwire.pt1[0]), int(self.detector.tripwire.pt1[1])],
                        "pt2": [int(self.detector.tripwire.pt2[0]), int(self.detector.tripwire.pt2[1])],
                        "d_threshold": float(self.detector.tripwire.d_threshold)
                    },
                    "events": list(self.events_history[:25])
                }

            # Giữ nhịp khung hình: Webcam tự do theo phần cứng; File video giữ đúng target_dt
            if is_live_stream:
                time.sleep(0.001)
            else:
                t_elapsed = time.perf_counter() - t_start
                t_sleep = max(0.001, target_dt - t_elapsed)
                time.sleep(t_sleep)

        cap.release()

    def get_latest_frame_jpeg(self, use_mask: bool = False) -> Optional[bytes]:
        with self.lock:
            self.last_stream_request_time = time.time()
            cached = self.current_mask_jpeg if use_mask else self.current_annotated_jpeg
            if cached is not None:
                return cached

            # Nén tức thời nếu là frame đầu hoặc stream vừa kết nối lại sau khi ngủ
            target = self.current_mask_frame if use_mask else self.current_annotated_frame
            if target is None:
                return None
            quality = 80 if use_mask else 85
            ret, buf = cv2.imencode(".jpg", target, [cv2.IMWRITE_JPEG_QUALITY, quality])
            encoded = buf.tobytes() if ret else None
            if use_mask:
                self.current_mask_jpeg = encoded
            else:
                self.current_annotated_jpeg = encoded
            return encoded

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.current_stats)
