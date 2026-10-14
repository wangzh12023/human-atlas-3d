@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist node_modules (
  echo 正在安装依赖...
  call npm install
)
if not exist dist\index.html (
  echo 正在构建...
  call npm run build
)
echo 启动预览服务器: http://127.0.0.1:5179
start "" http://127.0.0.1:5179
call npm run preview
