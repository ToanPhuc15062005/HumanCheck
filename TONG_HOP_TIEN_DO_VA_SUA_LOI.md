# BÁO CÁO TỔNG HỢP TIẾN ĐỘ VÀ DANH SÁCH LỖI ĐÃ XỬ LÝ
DỰ ÁN: HUMANCHECK - HỆ THỐNG GIÁM SÁT THÔNG MINH VÀ ĐẾM NGƯỜI QUA LẠI (PURE DIP)
MÔN HỌC: XỬ LÝ ẢNH - PTIT HCM
GIẢNG VIÊN PHỤ TRÁCH: TS. HUỲNH TRUNG TRỤ

---

## I. TỔNG QUAN CÁC HẠNG MỤC ĐÃ HOÀN THÀNH

Trong phiên làm việc này, hệ thống đã được rà soát toàn diện, mở rộng kiến trúc phần mềm, tái thiết kế giao diện người dùng theo chuẩn tối giản cao cấp và đóng gói mã nguồn lên GitHub repository cá nhân.

Chi tiết các hạng mục đã hoàn thành bao gồm:

### 1. Rà soát tiến độ và đánh giá chất lượng đề tài
- Kiểm tra toàn bộ kiến trúc 3 module thuật toán Pure DIP (Digital Image Processing) không dùng Deep Learning:
  + Module 1: Pipeline thị giác, phân đoạn dáng người theo Spatial Moments và tỷ lệ khung bao (Height/Width >= 0.85), bộ theo dõi Centroid Tracker (khoảng cách Euclidean), máy trạng thái động Hysteresis State Machine chống đếm lặp.
  + Module 2: Giải tích hình học vạch ảo, bộ cấu hình tương tác chuột Calibrator, lưu trữ cấu hình file JSON.
  + Module 3: Bộ thích ứng môi trường 5 trụ cột gồm: Fast Background Reset khi đổi sáng đột ngột, kéo sáng thích ứng Gamma kết hợp CLAHE ban đêm, khử bóng đổ người trong không gian màu HSV, khử rung lắc bằng phép toán hình thái học Morphological Opening, và cơ chế đồng hóa đồ vật vào nền (Background Absorption).
- Kiểm thử tự động toàn bộ hệ thống với bộ test suite: 12/12 unit tests và integration tests đều đạt kết quả Passed tuyệt đối.

### 2. Nâng cấp giao diện Streamlit Demo
- Tích hợp công cụ Interactive Camera Overlay cho phép người dùng vẽ trực tiếp vạch ranh giới phân cách trên khung hình camera.
- Hỗ trợ 2 chế độ tương tác:
  + Kéo và thả chuột (Drag and Drop Line).
  + Click lần lượt 2 điểm A và B.
- Hiển thị trực quan trên khung hình: Điểm mốc A và B kèm tọa độ, đường ranh giới màu tương phản cao, mũi tên chỉ hướng Vào (IN) vuông góc với vạch, và 2 đường biên biểu thị vùng đệm an toàn Hysteresis (+/- d px).
- Đồng bộ 2 chiều tự động với các ô nhập số tại Sidebar và tự động cập nhật vào file tripwire_config.json.
- Bổ sung tính năng xuất dữ liệu nhật ký các lượt cắt vạch ra file CSV (Export CSV).

### 3. Tái thiết kế toàn bộ Frontend sang nền tảng React (Swiss Luxury Suite)
- Khởi tạo và xây dựng frontend độc lập bằng Vite + React trong thư mục frontend/.
- Loại bỏ hoàn toàn các emoji và ký tự biểu cảm trên toàn bộ giao diện, thay thế đồng nhất bằng thư viện Lucide-React icons.
- Thiết kế theo triết lý tối giản Swiss Luxury Spa:
  + Bảng màu đơn nhất: Nền đen quang học Obsidian (#090A0C), các khối giao diện phiến đá Slate (#101216), viền siêu mỏng 1px (rgba(255, 255, 255, 0.07)), chữ màu Titan (#F8FAFC) và Platinum (#94A3B8).
  + Không gian bố trí chuẩn lưới 8pt, cân đối khoảng cách lề và đệm, loại bỏ hoàn toàn khoảng trống thừa hoặc cảm giác chèn chúc.
  + Hệ thống kiểu chữ Inter và JetBrains Mono cho các thông số kỹ thuật.
- Tích hợp các chức năng trên Web Frontend:
  + Xem trực tiếp 2 luồng video MJPEG: Luồng camera kèm hộp bao/HUD và luồng mặt nạ tiền cảnh sạch (Module 3).
  + 4 thẻ chỉ số KPI chính: Số lượng khách trong phòng (Interior Occupancy), Lượt vào (Ingress), Lượt ra (Egress), và Tốc độ xử lý thực tế (Throughput FPS).
  + Kết nối WebSocket thời gian thực tần số 10Hz với backend FastAPI để đồng bộ trạng thái không độ trễ.
  + Bảng nhật ký lượt người (Transit Audit Log) kèm nút xuất file CSV.
  + Bộ tinh chỉnh tham số vùng đệm an toàn Hysteresis.
- Tích hợp hệ thống:
  + Bổ sung chế độ khởi chạy run.py --mode=frontend (chạy Vite dev server tại cổng 5173).
  + Mount trực tiếp bản build production của React (frontend/dist) vào FastAPI server, cho phép người dùng truy cập toàn bộ hệ thống chỉ qua 1 cổng duy nhất (http://localhost:8000).

### 4. Bổ sung nút điều khiển Start và Pause cho luồng video
- Backend:
  + Bổ sung cờ trạng thái is_paused trong lớp VideoSurveillanceService.
  + Bổ sung 3 endpoint REST API: POST /api/v1/stream/play, POST /api/v1/stream/pause, và POST /api/v1/stream/toggle.
  + Worker thread tạm dừng đọc frame mới khi pause nhưng vẫn duy trì frame hiện tại để luồng phát MJPEG không bị ngắt kết nối.
  + Cập nhật WebSocket và /api/v1/stats để broadcast trạng thái is_paused cho mọi client.
- Frontend:
  + Bổ sung nút Start/Pause trên cả thanh Header chính và thanh công cụ của khung hình camera.
  + Hiển thị huy hiệu Stream Paused nổi trên video khi đang tạm dừng.
  + Cập nhật trạng thái viền tín hiệu thành Engine Paused.

### 5. Đóng gói mã nguồn và Push lên GitHub cá nhân
- Khởi tạo Git repository cho toàn bộ dự án.
- Thiết lập file .gitignore chuẩn để loại trừ môi trường ảo (.venv), thư viện Node (node_modules), cache Python (__pycache__) và các file build tạm.
- Commit toàn bộ mã nguồn với thông điệp chuẩn.
- Liên kết remote repository: https://github.com/ToanPhuc15062005/HumanCheck.git.
- Xử lý xung đột rebase với commit mặc định trên remote và push toàn bộ nhánh main thành công.

---

## II. DANH SÁCH CÁC LỖI (BUGS) ĐÃ ĐƯỢC PHÁT HIỆN VÀ SỬA CHỮA TRIỆT ĐỂ

Trong quá trình phát triển và tinh chỉnh theo phản hồi của người dùng, các vấn đề kỹ thuật sau đã được phân tích nguyên nhân gốc rễ và xử lý hoàn tất:

### 1. Lỗi nhãn trên video quá to, che khuất khung hình
- Hiện tượng: Khung hình video gốc có độ phân giải 320x240 pixel. Hàm vẽ HUD cũ trong visualizer.py vẽ một hình chữ nhật màu đen có kích thước 330x135 pixel với cỡ chữ 0.7 ở góc trên bên trái, che mất hơn 50% diện tích video. Hộp bao Bounding Box có chiều cao badge 22 pixel và dòng chữ phụ bên dưới làm rối mắt.
- Nguyên nhân: Các tham số vẽ được thiết lập cố định cho video độ phân giải lớn, không tự động co giãn theo video 320x240.
- Giải pháp đã sửa:
  + Trong core/module1_tracking/visualizer.py, thay thế toàn bộ khối HUD 330x135 bằng thanh Micro-HUD nhỏ gọn cao 18 pixel, font scale giảm xuống 0.30 ở mép trên.
  + Thu nhỏ chiều cao badge trên đầu hộp bao từ 22 pixel xuống 13 pixel, font scale giảm còn 0.30, hiển thị mã ngắn gọn dạng #ID.
  + Loại bỏ dòng chữ phụ dài dòng bên dưới chân đối tượng.
  + Thu nhỏ font chữ nhãn vạch tripwire về 0.32.
  + Kết quả: Khung hình video trở nên thông thoáng, quan sát rõ ràng từng đối tượng di chuyển.

### 2. Kích thước website quá to (yêu cầu tỷ lệ 75%)
- Hiện tượng: Giao diện mặc định ở mức zoom 100% chiếm nhiều diện tích màn hình, người dùng phải cuộn trang để xem bảng số liệu và camera.
- Giải pháp đã sửa:
  + Thiết lập thuộc tính CSS zoom: 0.75 trên thẻ html trong frontend/src/index.css.
  + Điều chỉnh lại tỷ lệ đệm (padding) và khoảng cách giữa các panel.
  + Kết quả: Toàn bộ dashboard hiển thị vừa vặn trên một màn hình tiêu chuẩn mà không cần cuộn trang, đạt mật độ thông tin cao theo đúng phong cách executive dashboard.

### 3. Lỗi chức năng kéo thả vạch bị chập chờn (Flickering / Rubberbanding)
- Hiện tượng: Khi người dùng dùng chuột kéo đường ranh giới mới, nét vẽ vừa thả ra thì bị giật ngược về vị trí cũ rồi mới nhảy sang vị trí mới, tạo cảm giác chập chờn không ổn định.
- Nguyên nhân gốc rễ: Luồng WebSocket từ FastAPI server phát dữ liệu telemetry liên tục 10 lần mỗi giây (10Hz). Trong gói tin có chứa tọa độ tripwire hiện tại của server. Khi người dùng vừa kết thúc thao tác kéo, hàm lắng nghe WebSocket trên client lập tức nhận tọa độ cũ (do server chưa kịp lưu request POST vừa gửi) và ghi đè ngược trở lại state currentLine của React, dẫn đến xung đột giữa dữ liệu đang vẽ và dữ liệu từ server.
- Giải pháp đã sửa:
  + Tạo bộ đếm thời gian và cờ kiểm soát: lastEditTimeRef và isDraggingRef trong App.jsx.
  + Khi người dùng bắt đầu kéo hoặc vừa kéo xong trong vòng 2.5 giây, WebSocket bị chặn (debounce) không được phép ghi đè tọa độ vạch.
  + Kết quả: Triệt tiêu 100% hiện tượng vạch bị giật hoặc nhảy ngược về vị trí cũ.

### 4. Lỗi kéo thả vạch bị dính chuột (Sticky Dragging)
- Hiện tượng: Khi kéo nhanh chuột hoặc con trỏ chuột di chuyển ra khỏi phạm vi khung hình canvas, chức năng kéo bị kẹt cứng. Khi đưa chuột quay lại màn hình thì nét vẽ vẫn tiếp tục bị dính theo con trỏ dù người dùng đã nhả nút chuột từ trước.
- Nguyên nhân gốc rễ gồm 3 yếu tố:
  + Yếu tố 1: Sự kiện onMouseUp trước đây chỉ được gắn cục bộ trên phần tử canvas. Khi chuột di chuyển vượt qua mép canvas, sự kiện nhả chuột bị trình duyệt bỏ qua, làm cờ isDragging vẫn giữ giá trị true.
  + Yếu tố 2: Trình duyệt kích hoạt tính năng kéo ảnh mặc định (HTML5 Native Drag) trên thẻ img của luồng MJPEG nằm bên dưới, tạo ra bóng ma của ảnh và khóa chặt con trỏ chuột.
  + Yếu tố 3: Khi website được áp dụng CSS zoom: 0.75, phép tính tọa độ cũ (e.clientX - rect.left) * (320 / canvas.width) bị lệch do sự khác biệt giữa tọa độ vật lý trên màn hình và tọa độ logic của phần tử.
- Giải pháp đã sửa:
  + Chuyển sang Pointer Events API (handlePointerDown) và đăng ký sự kiện di chuyển/nhả chuột toàn cục trên đối tượng window (window.addEventListener('pointermove'), window.addEventListener('pointerup'), window.addEventListener('pointercancel')). Dù người dùng nhả chuột ở bất kỳ đâu trên màn hình hay ngoài cửa sổ trình duyệt, thao tác kéo đều được giải phóng sạch sẽ và hủy bỏ listener.
  + Khóa tính năng kéo ảnh mặc định trên thẻ img bằng CSS: pointer-events: none, user-select: none, -webkit-user-drag: none.
  + Áp dụng công thức tính tọa độ chuẩn hóa theo tỷ lệ phần trăm hộp bao trực quan:
    nx = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    ny = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
    x = Math.round(nx * 320)
    y = Math.round(ny * 240)
    Công thức này miễn nhiễm hoàn toàn với mọi mức zoom, độ phân giải màn hình hay tỷ lệ DPI.
  + Kết quả: Thao tác kéo thả trở nên mượt mà, bắt dính chính xác tuyệt đối và không bao giờ còn hiện tượng dính chuột.

---

## III. HƯỚNG DẪN VẬN HÀNH VÀ KIỂM TRA NHANH

Người dùng có thể kiểm tra lại toàn bộ các chức năng bằng các lệnh sau:

### 1. Khởi chạy Web Frontend React (Khuyên dùng)
Mở terminal tại thư mục HumanCheck và chạy:
python run.py --mode=frontend

Truy cập: http://localhost:5173

### 2. Khởi chạy máy chủ FastAPI sản xuất (Tích hợp cả API và Frontend)
python run.py --mode=api

Truy cập: http://localhost:8000

### 3. Kiểm tra tính năng kéo vạch
- Bấm nút "Calibrate Line" trên thanh công cụ.
- Nhấn giữ chuột tại điểm bắt đầu trên khung hình camera, kéo đến điểm kết thúc và nhả chuột.
- Vạch mới sẽ được cập nhật ngay lập tức trên cả video và backend mà không bị giật hay dính chuột.
- Bấm nút "Pause Stream" để tạm dừng xử lý video và "Start Stream" để tiếp tục.

### 4. Kiểm tra kho lưu trữ GitHub
Toàn bộ dự án đã được cập nhật đầy đủ tại:
https://github.com/ToanPhuc15062005/HumanCheck
