"""
MODULE 2: HÌNH HỌC VÀ GIẢI TÍCH VẠCH ẢO (TRIPWIRE GEOMETRY)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import Tuple
import numpy as np


class TripwireGeometry:
    """
    Các phép toán hình học giải tích liên quan đến vạch ảo và vùng đệm an toàn.
    """

    @staticmethod
    def compute_normal_vector(
        pt1: Tuple[int, int],
        pt2: Tuple[int, int]
    ) -> Tuple[float, float, float]:
        """
        Tính độ dài đoạn thẳng và vector pháp tuyến đơn vị (nx, ny).

        Args:
            pt1: Điểm đầu ((x1, y1))
            pt2: Điểm cuối ((x2, y2))

        Returns:
            Tuple[float, float, float]: (line_length, nx, ny)
        """
        dx = float(pt2[0] - pt1[0])
        dy = float(pt2[1] - pt1[1])
        line_len = max(1e-5, np.hypot(dx, dy))
        nx = -dy / line_len
        ny = dx / line_len
        return line_len, nx, ny

    @staticmethod
    def compute_buffer_lines(
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        d_threshold: float
    ) -> Tuple[Tuple[Tuple[int, int], Tuple[int, int]], Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Tính 2 đường biên vùng đệm an toàn dựa trên khoảng cách ngưỡng d_threshold.

        Returns:
            ((out_p1, out_p2), (in_p1, in_p2))
        """
        _, nx, ny = TripwireGeometry.compute_normal_vector(pt1, pt2)
        b_out_p1 = (int(pt1[0] + nx * d_threshold), int(pt1[1] + ny * d_threshold))
        b_out_p2 = (int(pt2[0] + nx * d_threshold), int(pt2[1] + ny * d_threshold))
        b_in_p1 = (int(pt1[0] - nx * d_threshold), int(pt1[1] - ny * d_threshold))
        b_in_p2 = (int(pt2[0] - nx * d_threshold), int(pt2[1] - ny * d_threshold))
        return (b_out_p1, b_out_p2), (b_in_p1, b_in_p2)

    @staticmethod
    def signed_distance(
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        point: Tuple[int, int]
    ) -> float:
        """
        Tính khoảng cách trực giao có dấu từ point đến đường thẳng pt1-pt2.
        d > 0: OUT_SIDE
        d <= 0: IN_SIDE
        """
        line_len, _, _ = TripwireGeometry.compute_normal_vector(pt1, pt2)
        px, py = point
        cross = (pt2[0] - pt1[0]) * (py - pt1[1]) - (pt2[1] - pt1[1]) * (px - pt1[0])
        return float(cross / line_len)
