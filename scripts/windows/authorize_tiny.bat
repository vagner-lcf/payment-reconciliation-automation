@echo off
cd /d "%~dp0\..\.."

echo ==========================================
echo         AUTORIZACAO DO TINY
echo ==========================================
echo.
echo Aguarde a abertura do navegador.
echo Faca login no Tiny, se solicitado.
echo Conclua a autorizacao e aguarde a confirmacao nesta janela.
echo.

".venv\Scripts\python.exe" -m src.authorize_tiny

echo.
pause