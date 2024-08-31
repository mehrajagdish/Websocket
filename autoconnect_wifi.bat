@echo off
setlocal

:: Set the SSID
set SSID=iWinner

:check_connection
echo Checking connection status...
netsh wlan show interfaces | findstr /C:"%SSID%" >nul
if %ERRORLEVEL% == 0 (
    echo Connected to "%SSID%".
    timeout /t 60 /nobreak >nul
) else (
    echo Not connected to "%SSID%". Reconnecting...
    netsh wlan connect name="%SSID%"
    timeout /t 10 /nobreak >nul
)
goto check_connection