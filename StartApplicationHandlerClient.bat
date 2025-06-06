@ECHO OFF

call cd C:\Six2o\ApplicationHandler\Websocket

ECHO Activating virtual environment

call newvenv\Scripts\activate.bat

ECHO Virtual environment activated

ECHO Starting Application handler client
call python handle_animation_app.py

PAUSE