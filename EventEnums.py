import enum


class Events(enum.Enum):
    REPLAY = "replay"
    THROW_BALL = "throwBall"
    GAME_MODE = "gameMode"
    CURRENT_PLAYER_INFO = "currentPlayerInfo"
    PLAYERS_LIST = "playersList"
    CURRENT_BALL_VELOCITY = "currentBallVelocity"
    CURRENT_BALL_INFO = "currentBallInfo"
    CURRENT_BALL_VIDEO_URL = "currentBallVideoUrl"
    GAME_ENDED = "gameEnded"
    PLAY_VIDEO = "playVideo"
    BOWLING_MACHINE_STATUS = "bowlingMachineStatus"
    SET_BOWLING_MACHINE_PARAMETERS = "setBowlingMachineParameters"
    FEED_BOWLING_MACHINE = "feedBowlingMachine"
    START_PLAYING = "startPlaying"
    STOP_PLAYING = "stopPlaying"
    BAY_SHIFTED = "bayShifted"


class Devices(enum.Enum):
    PLAYER_APP = "playerApp"
    DETECTOR = "detector"
    TRIGGER = "trigger"
    UNITY = "unity"
    RECORDER = "recorder"
    BOWLING_MACHINE = "bowlingMachine"
    BACKEND_SERVER = "backendServer"


class GameMode(enum.Enum):
    FREE_HITTING = "freeHitting"
    TARGET_PRACTICE = "targetPractice"
    SCORING = "scoring"
