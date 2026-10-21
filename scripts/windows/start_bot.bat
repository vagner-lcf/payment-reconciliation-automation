@echo off
setlocal
title Payment Reconciliation Automation

cd /d "%~dp0\..\.."

echo ==================================================
echo          PAYMENT RECONCILIATION AUTOMATION
echo ==================================================
echo.
echo Programa de conciliacao financeira.
echo.
echo IMPORTANTE:
echo Mantenha esta janela aberta enquanto o programa
echo estiver em funcionamento.
echo.
echo Desenvolvido por Vagner Fonseca
echo ==================================================
echo.
echo Para interromper, aguarde a resposta do bot
echo ao comprovante enviado e pressione Ctrl+C.
echo.
echo Registro de atividades:
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_bot.ps1"
