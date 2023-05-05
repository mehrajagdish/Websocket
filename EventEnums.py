import enum


class Events(enum.Enum):
    REPLAY = "replay"
    THROW_BALL = "throwBall"
    GAME_MODE = "gameMode"
    CURRENT_PLAYER_INFO = "currentPlayerInfo"
    PLAYERS_LIST = "playersList"
    CURRENT_BALL_VELOCITY = "currentBallVelocity"
    CURRENT_BALL_INFO = "currentBallInfo"


class Devices(enum.Enum):
    PLAYER_APP = "playerApp"
    DETECTOR = "detector"
    TRIGGER = "trigger"
    UNITY = "unity"
    RECORDER = "recorder"


class GameMode(enum.Enum):
    FREE_HITTING = "freeHitting"
    TARGET_PRACTICE = "targetPractice"
    SCORING = "scoring"
