@echo off
chcp 65001 >nul
title GLM-OCR 快速测试
echo.
echo ============================================
echo    GLM-OCR 快速测试 (1.jpg)
echo ============================================
echo.

wsl -d Ubuntu -e bash -c "cd /mnt/c/AI/LLM && python3 test_glm_ocr_image.py"

echo.
echo ============================================
pause
