import enum


class BowlingMachineResponse(enum.Enum):
    ACCESS_DENIED = "ACCESS_DENIED"
    ACK = "ACK"
    PLEASE_WAIT = "PLEASE_WAIT"
    READY = "READY"
    BALLTRIGGERED = "BALLTRIGGERED"


