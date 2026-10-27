"""
MODULE 1: PHÂN ĐOẠN & LỌC HÌNH HỌC DÁNG NGƯỜI (HUMAN SEGMENTOR)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import List, Tuple
import cv2
import numpy as np


class HumanSegmentor:
    """
    Bộ phân đoạn và lọc hình học dáng người từ mặt nạ chuyển động.
    """

    def __init__(
        self,
        min_area: float = 400.0,
        min_aspect_ratio: float = 0.85,
        max_aspect_ratio: float = 4.5,
        override_large_area: float = 1200.0,
        use_moments: bool = True
    ):
        """
        Khởi tạo bộ lọc phân đoạn dáng người.

        Args:
            min_area (float): Diện tích tối thiểu để loại bỏ nhiễu vi chuyển động (mặc định: 400px).
            min_aspect_ratio (float): Tỷ lệ H/W tối thiểu đại diện cho dáng người đứng (mặc định: 0.85).
            max_aspect_ratio (float): Tỷ lệ H/W tối đa để lọc các vệt dị thường (mặc định: 4.5).
            override_large_area (float): Ngưỡng diện tích lớn (>= 1200px) để giữ lại bất kể tỷ lệ.
            use_moments (bool): Dùng Spatial Moments (M10/M00, M01/M00) để tính tâm chính xác.
        """
        self.min_area = min_area
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.override_large_area = override_large_area
        self.use_moments = use_moments

    def extract_contours(self, mask: np.ndarray) -> List[np.ndarray]:
        """
        Trích xuất danh sách đường bao ngoài (external contours) từ mặt nạ nhị phân.
        """
        if mask is None or mask.size == 0:
            return []

        if len(mask.shape) == 3:
            mask_single = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else:
            mask_single = mask

        contours, _ = cv2.findContours(
            mask_single,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        return contours

    def compute_centroid(self, contour: np.ndarray, box: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """
        Tính tâm (Centroid) của đối tượng bằng Spatial Moments hoặc Bounding Box Center.
        """
        x, y, w, h = box
        if self.use_moments:
            moments = cv2.moments(contour)
            if moments["m00"] > 1e-5:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
                return (cx, cy)

        return (int(x + w / 2.0), int(y + h / 2.0))

    def filter_and_detect(
        self,
        mask: np.ndarray
    ) -> Tuple[List[Tuple[int, int, int, int]], List[Tuple[int, int]], List[float]]:
        """
        Tìm contour, áp dụng bộ lọc hình học (Diện tích, Tỷ lệ khung hình) và trích xuất
        danh sách Bounding Box cùng Centroid đạt chuẩn người.
        """
        contours = self.extract_contours(mask)
        valid_boxes: List[Tuple[int, int, int, int]] = []
        centroids: List[Tuple[int, int]] = []
        areas: List[float] = []

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < self.min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(h) / max(1.0, float(w))

            is_standing_person = (self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio)
            is_large_cluster = (area >= self.override_large_area)

            if is_standing_person or is_large_cluster:
                box = (int(x), int(y), int(w), int(h))
                center = self.compute_centroid(cnt, box)

                valid_boxes.append(box)
                centroids.append(center)
                areas.append(area)

        return valid_boxes, centroids, areas
