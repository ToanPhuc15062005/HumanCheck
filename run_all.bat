@echo off
title HumanCheck Surveillance Suite - Full Stack (Backend + Frontend)
chcp 65001 >nul
cls

echo ======================================================================
echo   🚀 HUMANCHECK SURVEILLANCE SUITE - KHỞI CHẠY ĐỒNG THỜI FULL-STACK
echo   Môn học: Xử lý ảnh (DIP) - PTIT HCM ^| TS. Huỳnh Trung Trụ
echo ======================================================================

cd /d "%~dp0"

echo 🔹 [1/2] Đang khởi động FastAPI / Uvicorn Server (Port 8000)...
start "HumanCheck Backend (FastAPI)" cmd /k "python -m uvicorn app.server_uvicorn.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo 🔹 [2/2] Đang khởi động React Frontend Dev Server (Port 5173)...
start "HumanCheck Frontend (Vite/React)" cmd /k "cd frontend && npm run dev"

echo.
echo ======================================================================
echo   ✨ HỆ THỐNG ĐÃ ĐƯỢC MỞ TRONG 2 CỬA SỔ RIÊNG BIỆT:
echo   👉 React Web App (Giao diện chính): http://localhost:5173
echo   👉 FastAPI Backend API:              http://127.0.0.1:8000
echo   👉 Swagger API Docs:                 http://127.0.0.1:8000/docs
echo ======================================================================
echo   Đang tự động mở trình duyệt...
timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo   Để tắt hệ thống, bạn chỉ cần đóng 2 cửa sổ terminal vừa bật lên.
pause
