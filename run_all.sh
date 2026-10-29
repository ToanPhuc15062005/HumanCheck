#!/usr/bin/env bash
# ==============================================================================
# HumanCheck: Khởi chạy đồng thời FastAPI Backend & React Frontend (Dev Suite)
# Môn học: Xử lý ảnh (DIP) - PTIT HCM | TS. Huỳnh Trung Trụ
# ==============================================================================

set -e

# Đổi thư mục làm việc về thư mục chứa script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "  🚀 HUMANCHECK SURVEILLANCE SUITE - KHỞI CHẠY HỆ THỐNG TOÀN DIỆN"
echo "======================================================================"

# Chọn python executable
if command -v python &>/dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Lỗi: Không tìm thấy Python trong hệ thống!"
    exit 1
fi

# Kiểm tra npm
if ! command -v npm &>/dev/null; then
    echo "❌ Lỗi: Không tìm thấy npm (Node.js) trong hệ thống!"
    exit 1
fi

echo "🔹 [1/2] Đang khởi chạy FastAPI / Uvicorn Backend tại http://127.0.0.1:8000..."
"$PYTHON_CMD" -m uvicorn app.server_uvicorn.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Hàm dọn dẹp tiến trình khi tắt script (Ctrl+C hoặc Exit)
cleanup() {
    echo ""
    echo "🛑 Đang dừng toàn bộ dịch vụ HumanCheck..."
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    echo "✅ Đã đóng tiến trình an toàn."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Đợi 1.5 giây để backend kịp khởi tạo
sleep 1.5

echo "🔹 [2/2] Đang khởi chạy React Frontend tại http://localhost:5173..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo ""
echo "======================================================================"
echo "  ✨ TẤT CẢ DỊCH VỤ ĐÃ SẴN SÀNG:"
echo "  👉 React Web App (Giao diện chính): http://localhost:5173"
echo "  👉 FastAPI Backend API:              http://127.0.0.1:8000"
echo "  👉 Tài liệu Swagger API Docs:        http://127.0.0.1:8000/docs"
echo "  👉 Luồng Video Giám sát:             http://127.0.0.1:8000/api/v1/stream/video"
echo "======================================================================"
echo "  Nhấn [Ctrl + C] bất kỳ lúc nào để dừng cả 2 dịch vụ cùng lúc."
echo "======================================================================"

# Chờ cho các tiến trình chạy nền
wait
