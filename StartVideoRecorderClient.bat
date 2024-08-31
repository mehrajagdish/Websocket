@ECHO OFF

call cd C:\Six2o\Recorder\Websocket

ECHO Activating virtual environment

call newvenv\Scripts\activate.bat

ECHO Virtual environment activated

ECHO Starting video-recorder client
call python PythonVideoRecorderClient.py
ECHO video-recorder client started

PAUSE