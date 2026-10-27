"""
MODULE 1: PIPELINE THỊ GIÁC, STATE MACHINE & ĐẾM NGƯỜI (HUMAN DETECTION MODULE)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import Dict, Tuple, Optional, Any, List
import time
import cv2
import numpy as np

from core.module1_tracking.segmentor import HumanSegmentor
from core.module1_tracking.tracker import CentroidTracker
from core.module1_tracking.tripwire import TripwireCounter
from core.module1_tracking.visualizer import SurveillanceVisualizer


class HumanDetectionModule:
    """
    Module 1: Pipeline xử lý thị giác toàn diện phát hiện, theo dõi và đếm người qua lại.
    Có thể chạy độc lập hoặc tích hợp với Module 2 (Vạch ảo) và Module 3 (Thích ứng môi trường).
    """

    def __init__(
        self,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]] = ((100, 240), (550, 240)),
        d_threshold: float = 35.0,
        min_area: float = 400.0,
        min_aspect_ratio: float = 0.85,
        max_aspect_ratio: float = 4.5,
        override_large_area: float = 1200.0,
        max_disappeared: int = 15,
        max_distance: float = 60.0,
        use_internal_subtractor: bool = True
    ):
        self.segmentor = HumanSegmentor(
            min_area=min_area,
            min_aspect_ratio=min_aspect_ratio,
            max_aspect_ratio=max_aspect_ratio,
            override_large_area=override_large_area,
            use_moments=True
        )
        self.tracker = CentroidTracker(
            max_disappeared=max_disappeared,
            max_distance=max_distance
        )
        self.tripwire = TripwireCounter(
            line_coords=line_coords,
            d_threshold=d_threshold
        )
        self.visualizer = SurveillanceVisualizer()

        self.internal_subtractor = None
        self.morph_kernel = None
        if use_internal_subtractor:
            self.internal_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=25, detectShadows=True
            )
            self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        self.last_frame_time = time.time()
        self.current_fps = 0.0

    def set_line(
        self,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]],
        d_threshold: Optional[float] = None
    ) -> None:
        """Cập nhật tọa độ vạch phân cách và khoảng cách vùng đệm an toàn."""
        self.tripwire.set_line(line_coords, d_threshold)

    def extract_internal_clean_mask(self, frame: np.ndarray) -> np.ndarray:
        """Trích xuất mặt nạ tiền cảnh sạch độc lập bằng MOG2 và hình thái học."""
        if self.internal_subtractor is None:
            self.internal_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=25, detectShadows=True
            )
            self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        fg_mask = self.internal_subtractor.apply(blurred)

        # Lọc bỏ bóng đổ xám (127)
        _, fg_thresh = cv2.threshold(fg_mask, 250, 255, cv2.THRESH_BINARY)

        clean_mask = cv2.morphologyEx(fg_thresh, cv2.MORPH_OPEN, self.morph_kernel, iterations=1)
        clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, self.morph_kernel, iterations=2)
        return clean_mask

    def process_frame(
        self,
        frame: np.ndarray,
        clean_mask: Optional[np.ndarray] = None,
        annotate: bool = True,
        extra_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Xử lý toàn diện một khung hình qua chu trình Module 1."""
        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.current_fps = 0.9 * self.current_fps + 0.1 * (1.0 / dt) if self.current_fps > 0 else (1.0 / dt)
        self.last_frame_time = now

        if clean_mask is None:
            clean_mask = self.extract_internal_clean_mask(frame)

        valid_boxes, centroids, areas = self.segmentor.filter_and_detect(clean_mask)
        objects = self.tracker.update(valid_boxes, centroids)
        counter_res = self.tripwire.update(objects)

        annotated_frame = None
        if annotate:
            annotated_frame = self.visualizer.draw_all(
                frame=frame,
                tracker=self.tracker,
                tripwire_counter=self.tripwire,
                fps=self.current_fps,
                extra_status=extra_status
            )

        return {
            "count_in": counter_res["count_in"],
            "count_out": counter_res["count_out"],
            "inside": counter_res["inside"],
            "events": counter_res["events"],
            "tracked_objects": dict(self.tracker.objects),
            "boxes": dict(self.tracker.boxes),
            "history": dict(self.tracker.history),
            "states": dict(self.tripwire.states),
            "valid_boxes": valid_boxes,
            "centroids": centroids,
            "areas": areas,
            "clean_mask": clean_mask,
            "annotated_frame": annotated_frame,
            "fps": self.current_fps
        }

    def reset(self) -> None:
        """Khôi phục lại toàn bộ trạng thái của module."""
        self.tracker.reset()
        self.tripwire.reset()
        if self.internal_subtractor is not None:
            self.internal_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=25, detectShadows=True
            )
