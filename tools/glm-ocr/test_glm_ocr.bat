@echo off
chcp 936 >nul
title GLM-OCR Test Tool

if "%~1"=="" (
    echo Usage: test_glm_ocr.bat [image_path] [prompt]
    echo.
    echo Example:
    echo   test_glm_ocr.bat 1.jpg
    echo   test_glm_ocr.bat 1.jpg "Text Recognition:"
    echo.
    pause
    exit /b 1
)

echo ============================================
echo GLM-OCR Image Recognition
echo ============================================
echo.

set IMAGE_PATH=%~1
set PROMPT=%~2
if "%PROMPT%"=="" set PROMPT=Text Recognition:

echo Image: %IMAGE_PATH%
echo Prompt: %PROMPT%
echo.

REM Convert to WSL path
for /f "delims=" %%i in ('wsl wslpath -u "%IMAGE_PATH%"') do set WSL_PATH=%%i

echo WSL Path: %WSL_PATH%
echo.
echo Recognizing...
echo ============================================
echo.

wsl -d Ubuntu python3 /mnt/c/AI/LLM/test_glm_ocr_image.py "%WSL_PATH%" "%PROMPT%"

echo.
echo ============================================
pause
