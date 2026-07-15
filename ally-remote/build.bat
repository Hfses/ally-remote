@echo off
REM ============================================================
REM  Compila o AllyRemote.exe localmente (no proprio Ally/PC).
REM  Requisito: Python 3.11+ instalado com "Add to PATH".
REM ============================================================
cd /d "%~dp0"

pip install -r requirements.txt pyinstaller pillow || goto :erro

python -c "from PIL import Image; Image.open('static/icon-512.png').save('icon.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])" || goto :erro

pyinstaller --onefile --name AllyRemote --icon icon.ico --uac-admin ^
  --add-data "static;static" ^
  --collect-all uvicorn ^
  --hidden-import hid ^
  --collect-all pynput ^
  --collect-all mss ^
  --collect-all PIL ^
  server.py || goto :erro

echo.
echo ============================================================
echo  Pronto! O executavel esta em:  dist\AllyRemote.exe
echo ============================================================
pause
exit /b 0

:erro
echo.
echo  A compilacao FALHOU. Veja a mensagem de erro acima.
pause
exit /b 1
