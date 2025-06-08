@echo off
echo === Starting CVE AI Engine (FastAPI) ===
start cmd /k "uvicorn backend.main:app --reload --port 8000"

echo === Waiting for backend to start ===
timeout /t 10 > nul

echo === Compiling Scanner.java ===
javac -d out -cp "libs/json-20230227.jar" main\java\com\scanner\Scanner.java

echo === Running Scanner ===
java -cp "libs/json-20230227.jar;out" com.scanner.Scanner

pause
