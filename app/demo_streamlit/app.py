"""
STREAMLIT DEMO: HỆ THỐNG GIÁM SÁT THÔNG MINH & ĐẾM NGƯỜI QUA LẠI
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
Mô hình Pure DIP: Không dùng AI/Deep Learning, hiệu năng cao, thích ứng môi trường.
Tính năng mới: Interactive Canvas Overlay cho phép kẻ vạch phân cách trực tiếp bằng chuột.
"""

import os
import sys
import time
import tempfile
import io
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

# Thêm thư mục gốc vào PYTHONPATH
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module1_tracking.pipeline import HumanDetectionModule
from core.module1_tracking.tripwire import TripwireCounter
from core.module1_tracking.visualizer import SurveillanceVisualizer
from core.module2_tripwire_gui.calibrator import TripwireCalibrator
from core.module3_adaptive_env.engine import AdaptiveEnvironmentEngine


# ==============================================================================
# CẤU HÌNH GIAO DIỆN STREAMLIT & CSS
# ==============================================================================
st.set_page_config(
    page_title="HumanCheck - PTIT DIP Surveillance",
    page_icon="🚶",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #616161;
        margin-bottom: 16px;
    }
    .overlay-badge {
        background-color: #E3F2FD;
        border-left: 4px solid #1E88E5;
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 12px;
        font-size: 13px;
        color: #0D47A1;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# QUẢN LÝ SESSION STATE
# ==============================================================================
calibrator = TripwireCalibrator(os.path.join(WORKSPACE_ROOT, "data", "configs", "tripwire_config.json"))
saved_line = calibrator.load_config() or ((80, 160), (280, 160))

def init_session_state():
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    if "events_log" not in st.session_state:
        st.session_state.events_log = []
    if "reset_trigger" not in st.session_state:
        st.session_state.reset_trigger = False
    if "tripwire_pt1" not in st.session_state:
        st.session_state.tripwire_pt1 = saved_line[0]
    if "tripwire_pt2" not in st.session_state:
        st.session_state.tripwire_pt2 = saved_line[1]
    if "temp_click_pts" not in st.session_state:
        st.session_state.temp_click_pts = []
    if "last_canvas_time" not in st.session_state:
        st.session_state.last_canvas_time = 0

init_session_state()


# ==============================================================================
# HÀM TRỢ GIÚP: ĐỌC FRAME XEM TRƯỚC & VẼ VẠCH PHÂN CÁCH TRỰC QUAN
# ==============================================================================
def get_preview_frame(source):
    """Trích xuất 1 frame xem trước từ nguồn video/webcam."""
    if source is None:
        return np.zeros((240, 320, 3), dtype=np.uint8)
    try:
        cap = cv2.VideoCapture(source)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            return frame
    except Exception:
        pass
    return np.zeros((240, 320, 3), dtype=np.uint8)


def render_tripwire_preview(base_frame, pt1, pt2, d_thresh, temp_pt=None):
    """Vẽ vạch phân cách, mũi tên chiều vào (IN) và vùng đệm an toàn lên frame xem trước."""
    canvas_img = base_frame.copy()
    
    # Nếu đang chọn điểm thứ nhất ở chế độ Click
    if temp_pt is not None:
        cv2.circle(canvas_img, temp_pt, 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(canvas_img, "Diem A (Chon tiep Diem B)", (temp_pt[0] + 10, temp_pt[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2, cv2.LINE_AA)
        return canvas_img

    if pt1 is not None and pt2 is not None:
        counter = TripwireCounter((pt1, pt2), d_threshold=d_thresh)
        viz = SurveillanceVisualizer()
        canvas_img = viz.draw_tripwire(canvas_img, counter)
        
        # Vẽ Điểm A (Đỏ)
        cv2.circle(canvas_img, pt1, 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(canvas_img, f"A ({pt1[0]}, {pt1[1]})", (pt1[0] + 8, pt1[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Vẽ Điểm B (Xanh biển)
        cv2.circle(canvas_img, pt2, 7, (255, 100, 0), -1, cv2.LINE_AA)
        cv2.putText(canvas_img, f"B ({pt2[0]}, {pt2[1]})", (pt2[0] + 8, pt2[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 100, 0), 2, cv2.LINE_AA)
        
        # Vẽ Mũi tên chỉ hướng VÀO (IN) vuông góc vạch
        cx = int((pt1[0] + pt2[0]) / 2)
        cy = int((pt1[1] + pt2[1]) / 2)
        arrow_len = int(d_thresh * 1.3)
        arrow_end = (int(cx - counter.nx * arrow_len), int(cy - counter.ny * arrow_len))
        cv2.arrowedLine(canvas_img, (cx, cy), arrow_end, (0, 255, 128), 2, tipLength=0.35, line_type=cv2.LINE_AA)
        cv2.putText(canvas_img, "HUONG VAO (IN)", (arrow_end[0] + 4, arrow_end[1] + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 128), 2, cv2.LINE_AA)
        
    return canvas_img


# ==============================================================================
# SIDEBAR: CẤU HÌNH THAM SỐ 3 MODULES
# ==============================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/e/e0/Logo_PTIT.png", width=120)
st.sidebar.markdown("### 🎛️ Bảng Điều Khiển Giám Sát")

# Nguồn Video
video_source_type = st.sidebar.radio(
    "Nguồn Video:",
    ["Video Mẫu (surveillance.avi)", "Tải lên File Video", "Webcam"],
    index=0
)

video_path = None
if video_source_type == "Video Mẫu (surveillance.avi)":
    sample_1 = os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi")
    sample_2 = os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")
    if os.path.exists(sample_1):
        video_path = sample_1
    elif os.path.exists(sample_2):
        video_path = sample_2
    else:
        st.sidebar.error("Không tìm thấy file data/samples/surveillance.avi!")
elif video_source_type == "Tải lên File Video":
    uploaded_file = st.sidebar.file_uploader("Chọn video (mp4, avi):", type=["mp4", "avi"])
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        video_path = tfile.name
else:
    video_path = 0  # Webcam index

# ------------------------------------------------------------------------------
# Cấu hình Module 2: Vạch ảo Tripwire
st.sidebar.markdown("---")
st.sidebar.markdown("#### 📏 Module 2: Tọa Độ Vạch Phân Cách")

col_p1, col_p2 = st.sidebar.columns(2)
with col_p1:
    x1_in = st.number_input("Điểm A (X1)", 0, 1920, int(st.session_state.tripwire_pt1[0]), step=5)
    y1_in = st.number_input("Điểm A (Y1)", 0, 1080, int(st.session_state.tripwire_pt1[1]), step=5)
with col_p2:
    x2_in = st.number_input("Điểm B (X2)", 0, 1920, int(st.session_state.tripwire_pt2[0]), step=5)
    y2_in = st.number_input("Điểm B (Y2)", 0, 1080, int(st.session_state.tripwire_pt2[1]), step=5)

# Cập nhật state nếu người dùng nhập số từ Sidebar
if (x1_in, y1_in) != st.session_state.tripwire_pt1 or (x2_in, y2_in) != st.session_state.tripwire_pt2:
    st.session_state.tripwire_pt1 = (int(x1_in), int(y1_in))
    st.session_state.tripwire_pt2 = (int(x2_in), int(y2_in))

d_threshold = st.sidebar.slider("Vùng đệm an toàn Hysteresis (px):", 10.0, 80.0, 35.0, 5.0)

# ------------------------------------------------------------------------------
# Cấu hình Module 1: Phân đoạn & Lọc dáng người
st.sidebar.markdown("---")
st.sidebar.markdown("#### ⚙️ Module 1: Lọc Dáng Người")
min_area = st.sidebar.slider("Diện tích tối thiểu (Area px):", 100.0, 1500.0, 400.0, 50.0)
min_ar = st.sidebar.slider("Tỷ lệ đứng tối thiểu (H/W):", 0.5, 2.0, 0.85, 0.05)
max_dist = st.sidebar.slider("Khoảng cách ghép cặp Tracker (px):", 20.0, 120.0, 60.0, 5.0)

# ------------------------------------------------------------------------------
# Cấu hình Module 3: Thích ứng môi trường
st.sidebar.markdown("---")
st.sidebar.markdown("#### 🛡️ Module 3: Thích Ứng Môi Trường")
enable_night = st.sidebar.checkbox("Kéo sáng thích ứng (Gamma + CLAHE)", value=True)
enable_shadow = st.sidebar.checkbox("Khử bóng đổ HSV (Shadow Removal)", value=True)
enable_shock = st.sidebar.checkbox("Fast Reset khi đổi sáng (Bật/Tắt đèn)", value=True)


# ==============================================================================
# KHUNG CHÍNH (MAIN DASHBOARD)
# ==============================================================================
st.markdown('<div class="main-header">🛡️ Hệ Thống Giám Sát Thông Minh & Đếm Người Qua Lại (Pure DIP)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Đồ án môn Xử lý ảnh | PTIT HCM | TS. Huỳnh Trung Trụ | Kiến trúc phân tầng Hybrid</div>', unsafe_allow_html=True)

# Các nút điều khiển chính
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.2, 1.2, 3.6])
with ctrl_col1:
    btn_start = st.button("▶️ Bắt đầu / Tiếp tục", type="primary", use_container_width=True)
with ctrl_col2:
    btn_stop = st.button("⏸️ Tạm dừng", use_container_width=True)
with ctrl_col3:
    btn_reset = st.button("🔄 Đặt lại bộ đếm (Reset)", use_container_width=True)

if btn_start:
    st.session_state.is_running = True
if btn_stop:
    st.session_state.is_running = False
if btn_reset:
    st.session_state.reset_trigger = True
    st.session_state.events_log.clear()

# 5 Thẻ KPI Metrics
kpi_in, kpi_out, kpi_inside, kpi_fps, kpi_env = st.columns(5)
metric_in = kpi_in.metric("🚶 Vào (IN)", "0")
metric_out = kpi_out.metric("🚶‍♂️ Ra (OUT)", "0")
metric_inside = kpi_inside.metric("👥 Trong phòng", "0")
metric_fps = kpi_fps.metric("⚡ Tốc độ (FPS)", "0.0")
metric_env = kpi_env.metric("💡 Môi trường", "Chuẩn")

st.markdown("---")


# ==============================================================================
# 🎯 TÍNH NĂNG MỚI: OVERLAY KẺ VẠCH PHÂN CÁCH TRỰC TIẾP TRÊN CAMERA
# ==============================================================================
with st.expander("✏️ CÔNG CỤ KẺ VẠCH PHÂN CÁCH TRỰC TIẾP TRÊN CAMERA (INTERACTIVE OVERLAY)", expanded=(not st.session_state.is_running)):
    st.markdown("""
    <div class="overlay-badge">
        <b>🎯 Hướng dẫn kẻ vạch:</b> Chọn chế độ bên dưới và dùng chuột thao tác trực tiếp trên khung hình camera.
        Vạch phân cách sẽ tự động cập nhật ngay lập tức vào thuật toán đếm và lưu vào cấu hình.
    </div>
    """, unsafe_allow_html=True)

    tool_col1, tool_col2 = st.columns([2.5, 1.5])
    
    with tool_col2:
        draw_mode = st.radio(
            "Chế độ thao tác chuột:",
            ["🖱️ Kéo - Thả chuột (Drag & Drop Line)", "👆 Click lần lượt 2 điểm (A rồi B)"],
            index=0
        )
        
        pt1 = st.session_state.tripwire_pt1
        pt2 = st.session_state.tripwire_pt2
        dx = float(pt2[0] - pt1[0])
        dy = float(pt2[1] - pt1[1])
        line_len = np.hypot(dx, dy)
        angle_deg = np.degrees(np.arctan2(dy, dx))

        st.markdown(f"""
        **Thông số vạch hiện tại:**
        - 🔴 **Điểm A (Bắt đầu):** `({pt1[0]}, {pt1[1]})`
        - 🔵 **Điểm B (Kết thúc):** `({pt2[0]}, {pt2[1]})`
        - 📏 **Chiều dài:** `{line_len:.1f} px`
        - 📐 **Góc nghiêng:** `{angle_deg:.1f}°`
        - 🛡️ **Vùng đệm an toàn:** `±{d_threshold:.0f} px`
        """)

        col_btn_reset, col_btn_save = st.columns(2)
        with col_btn_reset:
            if st.button("🔄 Đặt lại mặc định", use_container_width=True):
                st.session_state.tripwire_pt1 = (80, 160)
                st.session_state.tripwire_pt2 = (280, 160)
                st.session_state.temp_click_pts = []
                calibrator.save_config((st.session_state.tripwire_pt1, st.session_state.tripwire_pt2), d_threshold)
                st.rerun()

        with col_btn_save:
            if st.button("💾 Lưu cấu hình", use_container_width=True):
                calibrator.save_config((st.session_state.tripwire_pt1, st.session_state.tripwire_pt2), d_threshold)
                st.success("✅ Đã lưu vào data/configs/tripwire_config.json")

    with tool_col1:
        # Lấy frame nền xem trước từ camera / video
        preview_raw = get_preview_frame(video_path)
        orig_h, orig_w = preview_raw.shape[:2]

        temp_first_point = st.session_state.temp_click_pts[0] if len(st.session_state.temp_click_pts) == 1 else None
        preview_with_line = render_tripwire_preview(
            preview_raw,
            st.session_state.tripwire_pt1,
            st.session_state.tripwire_pt2,
            d_threshold,
            temp_pt=temp_first_point
        )

        # Chuyển đổi BGR sang RGB cho Pillow & Streamlit
        rgb_preview = cv2.cvtColor(preview_with_line, cv2.COLOR_BGR2RGB)
        pil_preview = Image.fromarray(rgb_preview)

        is_drag = ("Kéo - Thả" in draw_mode)

        # BẬT OVERLAY CANVAS BẰNG STREAMLIT_IMAGE_COORDINATES
        canvas_result = streamlit_image_coordinates(
            pil_preview,
            key="tripwire_camera_overlay",
            click_and_drag=is_drag,
            cursor="crosshair",
            use_column_width="always"
        )

        # Xử lý sự kiện kéo thả chuột
        if canvas_result is not None:
            c_time = canvas_result.get("unix_time", 0)
            if c_time != st.session_state.last_canvas_time:
                st.session_state.last_canvas_time = c_time
                disp_w = float(canvas_result.get("width", orig_w))
                disp_h = float(canvas_result.get("height", orig_h))
                scale_x = orig_w / max(1.0, disp_w)
                scale_y = orig_h / max(1.0, disp_h)

                if is_drag:
                    # Chế độ Kéo - Thả chuột (Drag & Drop)
                    x1_d = int(round(canvas_result["x1"] * scale_x))
                    y1_d = int(round(canvas_result["y1"] * scale_y))
                    x2_d = int(round(canvas_result["x2"] * scale_x))
                    y2_d = int(round(canvas_result["y2"] * scale_y))

                    # Lọc khoảng cách tối thiểu > 10px để tránh click nhầm
                    if np.hypot(x2_d - x1_d, y2_d - y1_d) > 10:
                        x1_d = max(0, min(orig_w - 1, x1_d))
                        y1_d = max(0, min(orig_h - 1, y1_d))
                        x2_d = max(0, min(orig_w - 1, x2_d))
                        y2_d = max(0, min(orig_h - 1, y2_d))

                        st.session_state.tripwire_pt1 = (x1_d, y1_d)
                        st.session_state.tripwire_pt2 = (x2_d, y2_d)
                        calibrator.save_config((st.session_state.tripwire_pt1, st.session_state.tripwire_pt2), d_threshold)
                        st.toast(f"🎉 Đã cập nhật vạch ảo: A({x1_d}, {y1_d}) ➔ B({x2_d}, {y2_d})", icon="✅")
                        st.rerun()
                else:
                    # Chế độ Click lần lượt 2 điểm
                    cx = int(round(canvas_result["x"] * scale_x))
                    cy = int(round(canvas_result["y"] * scale_y))
                    cx = max(0, min(orig_w - 1, cx))
                    cy = max(0, min(orig_h - 1, cy))

                    if len(st.session_state.temp_click_pts) == 0:
                        st.session_state.temp_click_pts.append((cx, cy))
                        st.toast(f"🟢 Đã chọn Điểm A: ({cx}, {cy}). Hãy click tiếp Điểm B!", icon="👉")
                        st.rerun()
                    else:
                        pt_a = st.session_state.temp_click_pts[0]
                        pt_b = (cx, cy)
                        if np.hypot(pt_b[0] - pt_a[0], pt_b[1] - pt_a[1]) > 5:
                            st.session_state.tripwire_pt1 = pt_a
                            st.session_state.tripwire_pt2 = pt_b
                            st.session_state.temp_click_pts = []
                            calibrator.save_config((st.session_state.tripwire_pt1, st.session_state.tripwire_pt2), d_threshold)
                            st.toast(f"🎉 Đã hoàn tất vạch ảo: A{pt_a} ➔ B{pt_b}", icon="✅")
                            st.rerun()

st.markdown("---")


# ==============================================================================
# KHUNG PHÁT LUỒNG VIDEO & MẶT NẠ TIỀN CẢNH
# ==============================================================================
col_video, col_mask = st.columns(2)
with col_video:
    st.markdown("##### 📹 Luồng Giám Sát Thời Gian Thực (Tracking & HUD)")
    video_placeholder = st.empty()
with col_mask:
    st.markdown("##### 🎭 Mặt Nạ Tiền Cảnh Sạch (Clean Foreground Mask - Module 3)")
    mask_placeholder = st.empty()

# Bảng nhật ký sự kiện & Nút xuất CSV
st.markdown("##### 📋 Nhật Ký Lượt Người Cắt Vạch")
log_col, btn_export_col = st.columns([3, 1])
with btn_export_col:
    if st.session_state.events_log:
        df_events = pd.DataFrame(st.session_state.events_log)
        csv_data = df_events.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Xuất Báo Cáo CSV",
            data=csv_data,
            file_name=f"humancheck_events_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

log_placeholder = st.empty()


# ==============================================================================
# VÒNG LẶP XỬ LÝ VIDEO THỜI GIAN THỰC
# ==============================================================================
if st.session_state.is_running and video_path is not None:
    # Khởi tạo 2 engines độc lập
    env_engine = AdaptiveEnvironmentEngine(
        night_threshold=75.0,
        enable_night_mode=enable_night,
        enable_shadow_removal=enable_shadow,
        shock_white_ratio=0.70 if enable_shock else 2.0
    )

    detector = HumanDetectionModule(
        line_coords=(st.session_state.tripwire_pt1, st.session_state.tripwire_pt2),
        d_threshold=d_threshold,
        min_area=min_area,
        min_aspect_ratio=min_ar,
        max_distance=max_dist,
        use_internal_subtractor=False
    )

    cap = cv2.VideoCapture(video_path)

    while cap.isOpened() and st.session_state.is_running:
        ret, frame = cap.read()
        if not ret or frame is None:
            # Lặp lại video nếu kết thúc file
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        if st.session_state.reset_trigger:
            detector.reset()
            env_engine.reset()
            st.session_state.reset_trigger = False

        # 1. Module 3: Thích ứng môi trường
        clean_mask, enhanced_frame, telemetry = env_engine.process(frame)

        # 2. Module 1: Phân đoạn, Tracking, Vạch ảo và Vẽ
        env_status_str = "NIGHT (CLAHE)" if telemetry["is_night_mode"] else "DAY"
        if telemetry["shock_detected"]:
            env_status_str += " | SHOCK RESET!"

        res = detector.process_frame(
            frame=enhanced_frame,
            clean_mask=clean_mask,
            annotate=True,
            extra_status=env_status_str
        )

        # Cập nhật nhật ký sự kiện
        if res["events"]:
            for evt_type, obj_id in res["events"]:
                t_str = time.strftime("%H:%M:%S")
                direction_txt = "Đi VÀO phòng" if evt_type == "IN" else "Đi RA ngoài"
                st.session_state.events_log.insert(0, {
                    "Thời gian": t_str,
                    "Mã đối tượng": f"ID #{obj_id}",
                    "Hành động": direction_txt,
                    "Loại": evt_type
                })
                if len(st.session_state.events_log) > 15:
                    st.session_state.events_log.pop()

        # Hiển thị lên giao diện Streamlit
        metric_in.metric("🚶 Vào (IN)", str(res["count_in"]))
        metric_out.metric("🚶‍♂️ Ra (OUT)", str(res["count_out"]))
        metric_inside.metric("👥 Trong phòng", str(res["inside"]))
        metric_fps.metric("⚡ Tốc độ (FPS)", f"{res['fps']:.1f}")
        metric_env.metric("💡 Môi trường", f"{telemetry['mean_luminance']:.0f} lux ({env_status_str})")

        # Chuyển đổi BGR sang RGB để Streamlit hiển thị đúng màu
        rgb_annotated = cv2.cvtColor(res["annotated_frame"], cv2.COLOR_BGR2RGB)
        video_placeholder.image(rgb_annotated, channels="RGB", use_container_width=True)
        mask_placeholder.image(res["clean_mask"], channels="GRAY", use_container_width=True)

        if st.session_state.events_log:
            log_placeholder.table(st.session_state.events_log)

        # Giữ nhịp hiển thị
        time.sleep(0.01)

    cap.release()
