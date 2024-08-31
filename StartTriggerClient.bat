@ECHO OFF

call cd C:\Six2o\Trigger\Websocket

ECHO Activating virtual environment

call newvenv\Scripts\activate.bat

ECHO Virtual environment activated

ECHO Starting trigger client
call python ws_tcp_relay_with_custom_delay.py

PAUSE