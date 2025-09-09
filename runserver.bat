@echo off
REM --------------------------------------
REM Tên script: run_api.bat
REM Mục đích: Kích hoạt venv, chạy uvicorn và ngrok
REM --------------------------------------

SET PORT=8000
SET HOST=0.0.0.0
SET MODULE=main:app

REM 1. Kích hoạt virtual environment
echo Kich hoạt virtual environment...
call .venv\Scripts\activate

REM 2. Chạy Uvicorn
call cd app
echo 🚀 Khởi động Uvicorn tại http://localhost:%PORT% ...
start cmd /k "uvicorn %MODULE% --host %HOST% --port %PORT% --reload"

REM uvicorn app:app --host 0.0.0.0 --port 80 --reload
REM uvicorn app:app --host 127.0.0.1 --port 8000 --reload


REM 3. Đợi Uvicorn khởi động
timeout /t 2 >nul

REM 4. Chạy ngrok từ thư mục D:\SETUP PM\PROGRAM\ngrok
echo 🌐 Đang mở ngrok tunnel...
pushd D:\ngrok
start cmd /k "ngrok http --url=https://drew-weest-trish.ngrok-free.app %PORT%"
popd

REM uvicorn main:app --host 0.0.0.0 --port 8000 --reload
REM ngrok http --url=https://drew-weest-trish.ngrok-free.app 8000