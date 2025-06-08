@echo off
echo Fixing development environment...

:: Kill any running processes
taskkill /f /im electron.exe 2>nul
taskkill /f /im node.exe 2>nul

:: Clear port 5173 (just in case)
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :5173') DO (
  taskkill /F /PID %%P 2>nul
)

:: Wait a moment for processes to terminate
timeout /t 2 /nobreak >nul

:: Start Vite with cross-env to ensure proper environment variables
start cmd /k "npx cross-env NODE_ENV=development npx vite --port 5174 --strictPort"

:: Wait for Vite to initialize
timeout /t 4 /nobreak >nul

:: Start Electron with cross-env to ensure NODE_ENV is properly set
start cmd /k "npx cross-env NODE_ENV=development VITE_DEV_SERVER_URL=http://localhost:5174 npx electron ."

echo Started development environment with cross-env.
