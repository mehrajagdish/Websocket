@ECHO OFF
ECHO Activating virtual environment

call newvenv\Scripts\activate.bat

ECHO Virtual environment activated

ECHO Starting websocket server
call python CommonWebsocketServer.py

PAUSE