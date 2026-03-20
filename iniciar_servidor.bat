@echo off
echo Instalando dependencias necesarias (una sola vez)...
py -m pip install -r requirements.txt
echo ===========================================
echo   Servidor Backend Corriendo en tu PC      
echo ===========================================
echo La aplicacion ahora puede conectarse a este servidor.
echo No cierres esta ventana negra.
echo ===========================================
py -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
